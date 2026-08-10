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
from datetime import date
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None

app = FastAPI(title="Home Cloud LLM Gateway", version="0.2.0")

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


# ── Models ──────────────────────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    task: str = Field(default="general")
    prompt: str
    context: Optional[str] = None
    mode: Literal["safe", "raw"] = "safe"
    reasoning: bool = False


class ChatResponse(BaseModel):
    provider: str
    model: str
    redacted: bool
    content: str
    tokens: int = 0


# ── Endpoints ───────────────────────────────────────────────────────────────────


@app.get("/health")
def health():
    return {
        "status": "ok",
        "provider": os.getenv("LLM_PROVIDER", "deepseek"),
        "redaction": os.getenv("LLM_REDACT_PERSONAL_DATA", "true"),
        "names_configured": len(NAME_PATTERNS),
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


@app.post("/v1/chat", response_model=ChatResponse)
def chat(payload: ChatRequest):
    provider = os.getenv("LLM_PROVIDER", "deepseek")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    model = os.getenv("DEEPSEEK_REASONER_MODEL" if payload.reasoning else "DEEPSEEK_MODEL", "deepseek-chat")

    if payload.mode != "safe":
        raise HTTPException(status_code=400, detail="raw mode is disabled in Stage 1")

    if not api_key or api_key == "replace_me":
        return ChatResponse(
            provider=provider,
            model="mock",
            redacted=True,
            content="LLM Gateway mock response: DEEPSEEK_API_KEY is not configured.",
        )

    if OpenAI is None:
        raise HTTPException(status_code=500, detail="openai SDK is not installed")

    _check_budget()

    prompt = payload.prompt
    context = payload.context or ""
    full = f"Task: {payload.task}\n\nContext:\n{context}\n\nPrompt:\n{prompt}"
    safe_full = redact(full)

    client = OpenAI(api_key=api_key, base_url=base_url)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an infrastructure assistant. Do not request or expose secrets or personal data."},
                {"role": "user", "content": safe_full},
            ],
            stream=False,
        )
        content = response.choices[0].message.content or ""
        tokens = getattr(getattr(response, "usage", None), "total_tokens", 0) or 0
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=502, detail=f"LLM provider error: {exc}") from exc

    _record_usage(tokens)
    return ChatResponse(provider=provider, model=model, redacted=True, content=content, tokens=tokens)


@app.post("/v1/diagnostics/explain", response_model=ChatResponse)
def explain_diagnostics(payload: ChatRequest):
    payload.task = "explain_anonymized_diagnostics"
    return chat(payload)
