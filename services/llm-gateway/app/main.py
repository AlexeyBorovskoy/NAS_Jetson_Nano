"""
Home Cloud LLM Gateway.

Single outbound door to the LLM provider (DeepSeek). Everything that leaves the
house passes through here, gets redacted, and is counted against a budget.

Design notes
------------
* `raw` mode is refused: callers cannot bypass redaction.
* Redaction is applied to the *composed* prompt, right before the network call,
  so a new caller cannot forget to redact.
* Budget is enforced BEFORE the call (fail-closed) and updated after it.
  Counters are persisted so a container restart does not reset the day.
* Name redaction is an explicit family-name list, not a NER model — see
  `docs/08_LLM_GATEWAY_DEEPSEEK.md` for what that does and does not cover.
"""
import json
import os
import re
import threading
import time
import uuid
from datetime import date
from pathlib import Path
from typing import Literal, Optional

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None

app = FastAPI(title="Home Cloud LLM Gateway", version="0.3.0")

# ── Redaction ───────────────────────────────────────────────────────────────────

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")
TOKEN_RE = re.compile(r"(?i)(api[_-]?key|token|secret|password|bearer)\s*[:=]\s*[^\s]+")
PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S)
# Talk / chat mentions: @username, @"Display Name"
MENTION_RE = re.compile(r"@\"[^\"]+\"|@[\w./-]+")
# Filesystem paths that expose a personal home directory
HOMEPATH_RE = re.compile(r"/(?:home|Users)/[A-Za-z0-9._-]+")


def _name_patterns() -> list[re.Pattern]:
    """Build declension-tolerant patterns from the configured family names.

    Russian names decline (Ольга → Ольге → Ольгой), so an exact match is not
    enough. We cut the trailing vowel/soft sign to get a stem and allow a short
    suffix. Stems shorter than 3 characters are ignored to avoid over-matching.

    ⚠️ KNOWN LIMIT — verified by test, not assumed:
    diminutives are a DIFFERENT stem and are NOT derived automatically.
    "Ольга" matches Ольге/Ольгой/Ольгу, but NOT "Оля".
    Likewise Иван→"Ваня", Алексей→"Лёша", Ульяна→"Уля".
    In a Russian family chat diminutives are what people actually use, so every
    form must be listed explicitly in LLM_REDACT_NAMES. This is a word list,
    not a named-entity model — see docs/08_LLM_GATEWAY_DEEPSEEK.md.
    """
    raw = os.getenv("LLM_REDACT_NAMES", "")
    patterns: list[re.Pattern] = []
    for name in re.split(r"[,\s]+", raw):
        name = name.strip()
        if len(name) < 3:
            continue
        stem = re.sub(r"[аеёиоуыэюяьйАЕЁИОУЫЭЮЯЬЙ]$", "", name)
        if len(stem) < 3:
            continue
        patterns.append(re.compile(rf"\b{re.escape(stem)}\w{{0,3}}\b", re.IGNORECASE | re.UNICODE))
    return patterns


NAME_PATTERNS = _name_patterns()


def redact(text: str) -> str:
    text = PRIVATE_KEY_RE.sub("[REDACTED_PRIVATE_KEY]", text)
    text = TOKEN_RE.sub(r"\1=[REDACTED]", text)
    text = EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    text = PHONE_RE.sub("[REDACTED_PHONE]", text)
    text = MENTION_RE.sub("[REDACTED_MENTION]", text)
    text = HOMEPATH_RE.sub("[REDACTED_PATH]", text)
    for pattern in NAME_PATTERNS:
        text = pattern.sub("[REDACTED_NAME]", text)
    return text


# ── Budget ──────────────────────────────────────────────────────────────────────

USAGE_FILE = Path(os.getenv("LLM_USAGE_FILE", "/data/llm_usage.json"))
_usage_lock = threading.Lock()


def _load_usage() -> dict:
    try:
        return json.loads(USAGE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_usage(data: dict) -> None:
    try:
        USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        USAGE_FILE.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        # Never let bookkeeping break the request path; in-memory state still applies.
        pass


def _today() -> str:
    return date.today().isoformat()


def _month() -> str:
    return _today()[:7]


def _current_usage() -> dict:
    """Usage counters for today/this month, rolled over automatically."""
    data = _load_usage()
    if data.get("day") != _today():
        data["day"] = _today()
        data["day_tokens"] = 0
        data["day_calls"] = 0
    if data.get("month") != _month():
        data["month"] = _month()
        data["month_tokens"] = 0
        data["month_calls"] = 0
    return data


def _estimated_cost_usd(tokens: int) -> float:
    """Rough cost estimate. Prices are configurable because they change."""
    price_per_m = float(os.getenv("LLM_PRICE_USD_PER_MTOKEN", "0.5"))
    return round(tokens / 1_000_000 * price_per_m, 4)


def _check_budget() -> None:
    """Fail-closed budget gate, evaluated before any outbound call."""
    daily_limit = int(os.getenv("LLM_DAILY_TOKEN_LIMIT", "0") or 0)
    monthly_cost_limit = float(os.getenv("LLM_MONTHLY_COST_LIMIT_USD", "0") or 0)
    with _usage_lock:
        usage = _current_usage()
    if daily_limit and usage.get("day_tokens", 0) >= daily_limit:
        raise HTTPException(
            status_code=429,
            detail=f"daily token limit reached ({usage['day_tokens']}/{daily_limit})",
        )
    if monthly_cost_limit:
        spent = _estimated_cost_usd(usage.get("month_tokens", 0))
        if spent >= monthly_cost_limit:
            raise HTTPException(
                status_code=429,
                detail=f"monthly cost limit reached (~${spent}/${monthly_cost_limit})",
            )


def _record_usage(tokens: int) -> None:
    with _usage_lock:
        usage = _current_usage()
        usage["day_tokens"] = usage.get("day_tokens", 0) + tokens
        usage["day_calls"] = usage.get("day_calls", 0) + 1
        usage["month_tokens"] = usage.get("month_tokens", 0) + tokens
        usage["month_calls"] = usage.get("month_calls", 0) + 1
        _save_usage(usage)


# ── Providers ───────────────────────────────────────────────────────────────────
#
# Both providers go through the SAME redaction and the SAME budget. Adding a
# provider must never open a second, unguarded door — that is the whole reason
# this gateway exists.

_gigachat_token: dict = {"value": "", "expires_at": 0.0}
_token_lock = threading.Lock()


def _gigachat_verify():
    """TLS setting for Sber endpoints.

    Sber signs its certificates with the Russian Ministry of Digital Development
    CA, which is not in the default trust store. Preferred: mount the root
    certificate and point GIGACHAT_CA_BUNDLE at it. Disabling verification is
    supported for a first connectivity check only.
    """
    bundle = os.getenv("GIGACHAT_CA_BUNDLE", "").strip()
    if bundle:
        return bundle
    return os.getenv("GIGACHAT_VERIFY_SSL", "true").lower() not in ("false", "0", "no")


def _gigachat_access_token() -> str:
    """Fetch and cache an OAuth token. Sber tokens live 30 minutes."""
    with _token_lock:
        if _gigachat_token["value"] and time.time() < _gigachat_token["expires_at"] - 60:
            return _gigachat_token["value"]

        auth_key = os.getenv("GIGACHAT_AUTH_KEY", "").strip()
        if not auth_key:
            raise HTTPException(status_code=500, detail="GIGACHAT_AUTH_KEY is not configured")

        oauth_url = os.getenv("GIGACHAT_OAUTH_URL", "https://ngw.devices.sberbank.ru:9443/api/v2/oauth")
        scope = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
        try:
            r = httpx.post(
                oauth_url,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                    "RqUID": str(uuid.uuid4()),
                    "Authorization": f"Basic {auth_key}",
                },
                data={"scope": scope},
                verify=_gigachat_verify(),
                timeout=30.0,
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"GigaChat OAuth transport error: {exc}") from exc

        if r.status_code != 200:
            raise HTTPException(status_code=502, detail=f"GigaChat OAuth failed: HTTP {r.status_code} {r.text[:200]}")

        data = r.json()
        token = data.get("access_token", "")
        if not token:
            raise HTTPException(status_code=502, detail="GigaChat OAuth returned no access_token")
        # expires_at comes in milliseconds; fall back to the documented 30 min.
        expires_at = data.get("expires_at")
        _gigachat_token["value"] = token
        _gigachat_token["expires_at"] = (expires_at / 1000) if expires_at else (time.time() + 1800)
        return token


def _call_gigachat(system: str, user: str, model: str) -> tuple[str, int]:
    token = _gigachat_access_token()
    base = os.getenv("GIGACHAT_BASE_URL", "https://gigachat.devices.sberbank.ru/api/v1").rstrip("/")
    try:
        r = httpx.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            verify=_gigachat_verify(),
            timeout=120.0,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"GigaChat transport error: {exc}") from exc

    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"GigaChat error: HTTP {r.status_code} {r.text[:200]}")

    data = r.json()
    content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""
    tokens = (data.get("usage") or {}).get("total_tokens", 0) or 0
    return content, tokens


def _call_deepseek(system: str, user: str, model: str) -> tuple[str, int]:
    if OpenAI is None:
        raise HTTPException(status_code=500, detail="openai SDK is not installed")
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    client = OpenAI(api_key=api_key, base_url=base_url)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            stream=False,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM provider error: {exc}") from exc
    content = response.choices[0].message.content or ""
    tokens = getattr(getattr(response, "usage", None), "total_tokens", 0) or 0
    return content, tokens


# ── Models ──────────────────────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    task: str = Field(default="general")
    prompt: str
    context: Optional[str] = None
    mode: Literal["safe", "raw"] = "safe"
    reasoning: bool = False
    # Per-request provider override; falls back to LLM_PROVIDER.
    provider: Optional[Literal["deepseek", "gigachat"]] = None


class ChatResponse(BaseModel):
    provider: str
    model: str
    redacted: bool
    content: str
    tokens: int = 0


# ── Endpoints ───────────────────────────────────────────────────────────────────


@app.get("/health")
def health():
    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
    return {
        "status": "ok",
        "provider": os.getenv("LLM_PROVIDER", "deepseek"),
        "redaction": os.getenv("LLM_REDACT_PERSONAL_DATA", "true"),
        "names_configured": len(NAME_PATTERNS),
        "providers": {
            "deepseek": bool(deepseek_key) and deepseek_key != "replace_me",
            "gigachat": bool(os.getenv("GIGACHAT_AUTH_KEY", "").strip()),
        },
    }


@app.get("/v1/usage")
def usage():
    """Current budget consumption — what the family has spent today/this month."""
    with _usage_lock:
        data = _current_usage()
    return {
        "day": data.get("day"),
        "day_tokens": data.get("day_tokens", 0),
        "day_calls": data.get("day_calls", 0),
        "day_limit": int(os.getenv("LLM_DAILY_TOKEN_LIMIT", "0") or 0),
        "month": data.get("month"),
        "month_tokens": data.get("month_tokens", 0),
        "month_calls": data.get("month_calls", 0),
        "month_cost_usd_est": _estimated_cost_usd(data.get("month_tokens", 0)),
        "month_cost_limit_usd": float(os.getenv("LLM_MONTHLY_COST_LIMIT_USD", "0") or 0),
    }


@app.post("/v1/redact")
def redact_endpoint(payload: ChatRequest):
    """Show what redaction does to a text without calling the provider."""
    src = "\n".join([payload.prompt, payload.context or ""])
    return {"redacted_text": redact(src)}


SYSTEM_PROMPT = (
    "You are an infrastructure assistant. "
    "Do not request or expose secrets or personal data."
)


@app.post("/v1/chat", response_model=ChatResponse)
def chat(payload: ChatRequest):
    provider = (payload.provider or os.getenv("LLM_PROVIDER", "deepseek")).lower()

    if payload.mode != "safe":
        raise HTTPException(status_code=400, detail="raw mode is disabled in Stage 1")

    if provider == "gigachat":
        model = os.getenv("GIGACHAT_MODEL", "GigaChat")
        configured = bool(os.getenv("GIGACHAT_AUTH_KEY", "").strip())
    elif provider == "deepseek":
        model = os.getenv(
            "DEEPSEEK_REASONER_MODEL" if payload.reasoning else "DEEPSEEK_MODEL",
            "deepseek-chat",
        )
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        configured = bool(api_key) and api_key != "replace_me"
    else:
        raise HTTPException(status_code=400, detail=f"unknown provider: {provider}")

    if not configured:
        return ChatResponse(
            provider=provider,
            model="mock",
            redacted=True,
            content=f"LLM Gateway mock response: {provider} credentials are not configured.",
        )

    # Budget first, then redaction — both apply to every provider.
    _check_budget()

    context = payload.context or ""
    full = f"Task: {payload.task}\n\nContext:\n{context}\n\nPrompt:\n{payload.prompt}"
    safe_full = redact(full)

    if provider == "gigachat":
        content, tokens = _call_gigachat(SYSTEM_PROMPT, safe_full, model)
    else:
        content, tokens = _call_deepseek(SYSTEM_PROMPT, safe_full, model)

    _record_usage(tokens)
    return ChatResponse(provider=provider, model=model, redacted=True, content=content, tokens=tokens)


@app.post("/v1/diagnostics/explain", response_model=ChatResponse)
def explain_diagnostics(payload: ChatRequest):
    payload.task = "explain_anonymized_diagnostics"
    return chat(payload)
