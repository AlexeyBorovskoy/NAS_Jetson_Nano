# ADR-0008: Маршрутизация LLM — GigaChat first, DeepSeek fallback

## Статус / Status

🇷🇺 **Принято** (2026-09-04). / 🇬🇧 **Accepted** (2026-09-04).

## Контекст / Context

- Шлюз уже поддерживает `deepseek`, `gigachat`, `ollama`.
- На Jetson (2026-09-04): `gigachat=true`, default `deepseek`, `LLM_PREFER_LOCAL=true`, model legacy `GigaChat`, base URL devices.sberbank.
- Live probe: `GigaChat-2` стабилен на `https://api.giga.chat/v1`; freemium PERS почти полный; 1 concurrent stream для физлиц.
- Станция с Ollama выведена из архитектуры (ADR-0007).

## Решение / Decision

1. **Default family path:** `LLM_PROVIDER=gigachat`, model `GigaChat-2`, base `https://api.giga.chat/v1`.
2. **Talk-бот** передаёт `provider` из `TALK_BOT_LLM_PROVIDER` (default `gigachat`).
3. **DeepSeek** — fallback при 429/5xx Giga и явный override `provider=deepseek`.
4. **`LLM_PREFER_LOCAL=false`** в prod; ollama остаётся в коде для dev only.
5. **Cloud.ru FM** — отдельный provider позже (волна 3), через тот же redaction door.
6. **Image analysis** семейных фото — запрет (`LLM_ALLOW_IMAGE_ANALYSIS=false`).
7. **Очередь:** не более 1 in-flight запроса к Giga (лимит PERS).

## Последствия / Consequences

- Семья использует freemium РФ-модель; DeepSeek остаётся spare.
- Нужен cutover env на устройстве + правки `.env.example` / Talk.
- Balance monitoring через upstream `/balance`.

## Откат / Rollback

`LLM_PROVIDER=deepseek`, `TALK_BOT_LLM_PROVIDER=` empty or deepseek, restore legacy base URL if needed.
