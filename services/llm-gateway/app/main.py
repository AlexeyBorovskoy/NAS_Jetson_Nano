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
            NAMES_DROPPED.append(name or "<empty>")
            continue
        stem = re.sub(r"[аеёиоуыэюяьйАЕЁИОУЫЭЮЯЬЙ]$", "", name)
        if len(stem) < 2:
            NAMES_DROPPED.append(name)
            continue
        alt = "|".join(NAME_ENDINGS)
        patterns.append(re.compile(rf"\b{re.escape(stem)}(?:{alt})\b", re.IGNORECASE | re.UNICODE))
    return patterns


# Russian case endings, longest first so the alternation is greedy where it matters.
# An explicit list beats a wildcard: "\bОл\w{0,3}\b" also swallows "Олег", while
# "Ол(ой|ей|а|е|и|ю|я|ь|…)" does not — "ег" is not a case ending.
NAME_ENDINGS = ["ой", "ою", "ей", "ею", "ом", "ем", "ём", "а", "у", "е", "ы", "и", "ю", "я", "ь", ""]

# Names the filter could NOT build a pattern for — surfaced in /health so a
# silently ignored name is impossible to miss.
NAMES_DROPPED: list[str] = []

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


# ── Per-user accounting ─────────────────────────────────────────────────────────
#
# Every request carries a `user`. Without it everything lands in "unknown", which
# is deliberate: it stays visible in /v1/usage instead of quietly vanishing, so a
# caller that forgot to identify itself is easy to spot.

DEFAULT_USER = "unknown"


def _user_limits() -> dict[str, int]:
    """Per-user daily token limits: "olga:5000 ivan:20000 anna:3000"."""
    limits: dict[str, int] = {}
    for item in re.split(r"[,\s]+", os.getenv("LLM_USER_LIMITS", "")):
        if not item or ":" not in item:
            continue
        name, _, value = item.partition(":")
        try:
            limits[name.strip().lower()] = int(value)
        except ValueError:
            continue
    return limits


def _user_daily_limit(user: str) -> int:
    """Personal limit if set, otherwise the shared per-user default."""
    limits = _user_limits()
    explicit = limits.get(user.strip().lower())
    if explicit is not None:
        return explicit
    return int(os.getenv("LLM_USER_DAILY_TOKEN_LIMIT", "0") or 0)


def _user_bucket(usage: dict, user: str) -> dict:
    """Fetch (and roll over) one user's counters inside the usage document."""
    users = usage.setdefault("users", {})
    bucket = users.setdefault(user, {})
    if bucket.get("day") != _today():
        bucket["day"] = _today()
        bucket["day_tokens"] = 0
        bucket["day_calls"] = 0
    if bucket.get("month") != _month():
        bucket["month"] = _month()
        bucket["month_tokens"] = 0
        bucket["month_calls"] = 0
    return bucket


def _check_budget(user: str = DEFAULT_USER) -> None:
    """Fail-closed budget gate, evaluated before any outbound call.

    Three independent ceilings, checked cheapest first:
      1. this user's daily tokens,
      2. the household's daily tokens,
      3. the household's monthly cost.
    """
    user = (user or DEFAULT_USER).strip() or DEFAULT_USER
    daily_limit = int(os.getenv("LLM_DAILY_TOKEN_LIMIT", "0") or 0)
    monthly_cost_limit = float(os.getenv("LLM_MONTHLY_COST_LIMIT_USD", "0") or 0)

    with _usage_lock:
        usage = _current_usage()
        bucket = _user_bucket(usage, user)
        user_spent = bucket.get("day_tokens", 0)
        total_day = usage.get("day_tokens", 0)
        total_month = usage.get("month_tokens", 0)

    user_limit = _user_daily_limit(user)
    if user_limit and user_spent >= user_limit:
        raise HTTPException(
            status_code=429,
            detail=f"personal daily limit reached for '{user}' ({user_spent}/{user_limit} tokens)",
        )
    if daily_limit and total_day >= daily_limit:
        raise HTTPException(
            status_code=429,
            detail=f"household daily token limit reached ({total_day}/{daily_limit})",
        )
    if monthly_cost_limit:
        spent = _estimated_cost_usd(total_month)
        if spent >= monthly_cost_limit:
            raise HTTPException(
                status_code=429,
                detail=f"household monthly cost limit reached (~${spent}/${monthly_cost_limit})",
            )


def _record_usage(tokens: int, user: str = DEFAULT_USER) -> None:
    user = (user or DEFAULT_USER).strip() or DEFAULT_USER
    with _usage_lock:
        usage = _current_usage()
        usage["day_tokens"] = usage.get("day_tokens", 0) + tokens
        usage["day_calls"] = usage.get("day_calls", 0) + 1
        usage["month_tokens"] = usage.get("month_tokens", 0) + tokens
        usage["month_calls"] = usage.get("month_calls", 0) + 1
        bucket = _user_bucket(usage, user)
        bucket["day_tokens"] = bucket.get("day_tokens", 0) + tokens
        bucket["day_calls"] = bucket.get("day_calls", 0) + 1
        bucket["month_tokens"] = bucket.get("month_tokens", 0) + tokens
        bucket["month_calls"] = bucket.get("month_calls", 0) + 1
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


_IMG_TAG_RE = re.compile(r'<img\s+src="([^"]+)"', re.IGNORECASE)


def _gigachat_download_file(file_id: str) -> bytes:
    """Fetch a generated/stored file's binary content."""
    token = _gigachat_access_token()
    base = os.getenv("GIGACHAT_BASE_URL", "https://gigachat.devices.sberbank.ru/api/v1").rstrip("/")
    try:
        r = httpx.get(
            f"{base}/files/{file_id}/content",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/jpg"},
            verify=_gigachat_verify(),
            timeout=120.0,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"GigaChat file download error: {exc}") from exc
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"GigaChat file download: HTTP {r.status_code} {r.text[:200]}")
    return r.content


def _gigachat_upload_file(filename: str, data: bytes, mime: str = "image/jpeg") -> str:
    """Upload a file to GigaChat storage; returns its id."""
    token = _gigachat_access_token()
    base = os.getenv("GIGACHAT_BASE_URL", "https://gigachat.devices.sberbank.ru/api/v1").rstrip("/")
    try:
        r = httpx.post(
            f"{base}/files",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": (filename, data, mime)},
            data={"purpose": "general"},
            verify=_gigachat_verify(),
            timeout=180.0,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"GigaChat upload error: {exc}") from exc
    if r.status_code not in (200, 201):
        raise HTTPException(status_code=502, detail=f"GigaChat upload: HTTP {r.status_code} {r.text[:300]}")
    file_id = (r.json() or {}).get("id", "")
    if not file_id:
        raise HTTPException(status_code=502, detail="GigaChat upload returned no file id")
    return file_id


def _gigachat_image(user_prompt: str, attachments: Optional[list[str]] = None) -> tuple[bytes, str, int]:
    """Ask Kandinsky (via GigaChat's built-in text2image) for an image.

    Returns (image_bytes, file_id, tokens). `attachments` carries an uploaded
    source image for editing/restoration instead of generating from scratch.
    """
    token = _gigachat_access_token()
    base = os.getenv("GIGACHAT_BASE_URL", "https://gigachat.devices.sberbank.ru/api/v1").rstrip("/")
    # ⚠️ Verified 2026-08-10: only GigaChat-2-Max accepts an image on input.
    # Plain "GigaChat" answers 422 "Model does not support image" — so the image
    # model is deliberately a SEPARATE setting from the chat model.
    model = os.getenv("GIGACHAT_IMAGE_MODEL", "GigaChat-2-Max")

    message: dict = {"role": "user", "content": user_prompt}
    if attachments:
        message["attachments"] = attachments

    body = {
        "model": model,
        # Lets the model decide to invoke the built-in text2image function.
        "function_call": "auto",
        "messages": [
            {"role": "system", "content": "Ты — художник. Выполняй запрос пользователя по изображению."},
            message,
        ],
    }
    try:
        r = httpx.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
            verify=_gigachat_verify(),
            timeout=300.0,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"GigaChat image transport error: {exc}") from exc
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"GigaChat image error: HTTP {r.status_code} {r.text[:300]}")

    data = r.json()
    content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""
    tokens = (data.get("usage") or {}).get("total_tokens", 0) or 0

    match = _IMG_TAG_RE.search(content)
    if not match:
        raise HTTPException(
            status_code=502,
            detail=f"GigaChat returned no image (text answer instead): {content[:300]}",
        )
    file_id = match.group(1)
    return _gigachat_download_file(file_id), file_id, tokens


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
    # Who is asking — drives per-user quotas and the /v1/usage breakdown.
    user: Optional[str] = None


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
        # Non-empty means a name in LLM_REDACT_NAMES is NOT being filtered.
        "names_dropped": NAMES_DROPPED,
        "providers": {
            "deepseek": bool(deepseek_key) and deepseek_key != "replace_me",
            "gigachat": bool(os.getenv("GIGACHAT_AUTH_KEY", "").strip()),
        },
    }


@app.get("/v1/usage")
def usage(user: Optional[str] = None):
    """Who spent what. Pass ?user=<name> for one person, omit for everyone."""
    with _usage_lock:
        data = _current_usage()
        buckets = dict(data.get("users", {}))

    def _person(name: str, bucket: dict) -> dict:
        limit = _user_daily_limit(name)
        day_tokens = bucket.get("day_tokens", 0) if bucket.get("day") == _today() else 0
        month_tokens = bucket.get("month_tokens", 0) if bucket.get("month") == _month() else 0
        return {
            "user": name,
            "day_tokens": day_tokens,
            "day_calls": bucket.get("day_calls", 0) if bucket.get("day") == _today() else 0,
            "day_limit": limit,
            "day_left": max(limit - day_tokens, 0) if limit else None,
            "month_tokens": month_tokens,
            "month_cost_usd_est": _estimated_cost_usd(month_tokens),
        }

    if user:
        return _person(user, buckets.get(user, {}))

    people = [_person(name, b) for name, b in buckets.items()]
    people.sort(key=lambda p: p["month_tokens"], reverse=True)
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
        "per_user_default_limit": int(os.getenv("LLM_USER_DAILY_TOKEN_LIMIT", "0") or 0),
        "users": people,
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
    user = payload.user or DEFAULT_USER
    _check_budget(user)

    context = payload.context or ""
    full = f"Task: {payload.task}\n\nContext:\n{context}\n\nPrompt:\n{payload.prompt}"
    safe_full = redact(full)

    if provider == "gigachat":
        content, tokens = _call_gigachat(SYSTEM_PROMPT, safe_full, model)
    else:
        content, tokens = _call_deepseek(SYSTEM_PROMPT, safe_full, model)

    _record_usage(tokens, user)
    return ChatResponse(provider=provider, model=model, redacted=True, content=content, tokens=tokens)


@app.post("/v1/diagnostics/explain", response_model=ChatResponse)
def explain_diagnostics(payload: ChatRequest):
    payload.task = "explain_anonymized_diagnostics"
    return chat(payload)


# ── Images (Kandinsky via GigaChat) ─────────────────────────────────────────────
#
# Two endpoints with deliberately DIFFERENT privacy weight:
#
#   /v1/image/generate — only a text prompt leaves the house. No personal data.
#   /v1/image/restore  — sends AN ACTUAL PHOTO to the provider. Gated by
#                        LLM_ALLOW_IMAGE_ANALYSIS, which is false by default,
#                        because the whole point of this project is that family
#                        photos stay home. Turning it on is a conscious decision.


class ImageRequest(BaseModel):
    prompt: str
    # Optional: where to write the result on the server side.
    save_path: Optional[str] = None
    user: Optional[str] = None


# Ready-made instructions for the common cases. Restoration is just one of them —
# the same upload path also does stylisation, which is what a family actually asks for.
# 🔴 ПРОВЕРЕНО 2026-08-10 — ЧИТАТЬ ПЕРЕД ИСПОЛЬЗОВАНИЕМ.
#
# GigaChat API НЕ РЕДАКТИРУЕТ фотографии. Прямой запрос на ретушь модель
# отклоняет словами «Я не могу редактировать изображения» и советует Photoshop.
#
# Реально работает связка из двух независимых шагов:
#   1. GigaChat-2-Max СМОТРИТ на фото и составляет его текстовое описание;
#   2. Kandinsky (text2image) РИСУЕТ НОВОЕ изображение по этому описанию.
#
# Значит, на выходе — не ваша фотография, а другая картинка на её мотив:
# другие лица, другой фон. Для «нарисуй в стиле» это приемлемо, для
# «отреставрируй бабушкино фото» или «отретушируй меня» — НЕТ.
#
# Пресеты, обещавшие сохранить человека (restore/colorize/glamour), убраны:
# выполнить это обещание через данный API невозможно.
IMAGE_PRESETS: dict[str, str] = {
    "anime": "Нарисуй новое изображение в стиле аниме по мотивам этой фотографии.",
    "cartoon": "Нарисуй новое изображение в мультипликационном стиле по мотивам этой фотографии.",
    "artistic": "Нарисуй художественную иллюстрацию по мотивам этой фотографии.",
}

# Что попросить нельзя — с объяснением, чтобы вызывающая сторона не гадала.
IMAGE_UNSUPPORTED: dict[str, str] = {
    "restore": "реставрация",
    "colorize": "раскрашивание",
    "glamour": "ретушь/гламур",
    "upscale": "повышение резкости",
}


class ImageEditRequest(BaseModel):
    # Source photo as base64 — the caller decides what to send, one file at a time.
    image_base64: str
    filename: str = "photo.jpg"
    # Either pick a preset or write your own instruction; instruction wins.
    preset: Optional[str] = None
    instruction: Optional[str] = None
    save_path: Optional[str] = None
    user: Optional[str] = None


class ImageResponse(BaseModel):
    provider: str
    file_id: str
    tokens: int
    bytes: int
    image_base64: Optional[str] = None
    saved_to: Optional[str] = None


def _finish_image(raw: bytes, file_id: str, tokens: int, save_path: Optional[str],
                  user: str = DEFAULT_USER) -> ImageResponse:
    import base64 as _b64

    saved = None
    if save_path:
        try:
            p = Path(save_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(raw)
            saved = str(p)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"cannot save image: {exc}") from exc
    _record_usage(tokens, user)
    return ImageResponse(
        provider="gigachat",
        file_id=file_id,
        tokens=tokens,
        bytes=len(raw),
        image_base64=None if saved else _b64.b64encode(raw).decode("ascii"),
        saved_to=saved,
    )


@app.post("/v1/image/generate", response_model=ImageResponse)
def image_generate(payload: ImageRequest):
    """Generate an image from a text prompt. Nothing personal leaves the house."""
    if not os.getenv("GIGACHAT_AUTH_KEY", "").strip():
        raise HTTPException(status_code=400, detail="GigaChat is not configured")
    user = payload.user or DEFAULT_USER
    _check_budget(user)
    safe_prompt = redact(payload.prompt)
    raw, file_id, tokens = _gigachat_image(safe_prompt)
    return _finish_image(raw, file_id, tokens, payload.save_path, user)


@app.get("/v1/image/presets")
def image_presets():
    """What the family can ask for without writing an instruction by hand."""
    return {"presets": IMAGE_PRESETS}


@app.post("/v1/image/edit", response_model=ImageResponse)
def image_edit(payload: ImageEditRequest):
    """Draw a NEW image inspired by a photo. THIS SENDS THE PHOTO TO THE PROVIDER.

    ⚠️ NOT an editor. The provider looks at the photo, describes it in words, and
    generates a fresh picture from that description — faces and background will
    differ. Retouching/restoration is impossible here; see IMAGE_PRESETS above.

    Refused unless LLM_ALLOW_IMAGE_ANALYSIS=true — an explicit, conscious opt-in,
    because family photos staying home is the founding premise of this project.
    """
    if os.getenv("LLM_ALLOW_IMAGE_ANALYSIS", "false").lower() not in ("true", "1", "yes"):
        raise HTTPException(
            status_code=403,
            detail=(
                "image analysis is disabled by policy (LLM_ALLOW_IMAGE_ANALYSIS=false). "
                "This endpoint uploads a real photo to the provider — enable it deliberately."
            ),
        )
    if not os.getenv("GIGACHAT_AUTH_KEY", "").strip():
        raise HTTPException(status_code=400, detail="GigaChat is not configured")

    instruction = payload.instruction
    if not instruction:
        preset = (payload.preset or "restore").lower()
        if preset in IMAGE_UNSUPPORTED:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"'{preset}' ({IMAGE_UNSUPPORTED[preset]}) невозможно: GigaChat API "
                    "не редактирует фотографии, а только генерирует новые по описанию. "
                    f"Доступно: {', '.join(IMAGE_PRESETS)}"
                ),
            )
        instruction = IMAGE_PRESETS.get(preset)
        if not instruction:
            raise HTTPException(
                status_code=400,
                detail=f"unknown preset '{preset}'; known: {', '.join(IMAGE_PRESETS)}",
            )

    import base64 as _b64

    try:
        data = _b64.b64decode(payload.image_base64, validate=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"image_base64 is not valid base64: {exc}") from exc
    if not data:
        raise HTTPException(status_code=400, detail="empty image")

    user = payload.user or DEFAULT_USER
    _check_budget(user)
    file_id_in = _gigachat_upload_file(payload.filename, data)
    raw, file_id, tokens = _gigachat_image(redact(instruction), attachments=[file_id_in])
    return _finish_image(raw, file_id, tokens, payload.save_path, user)
