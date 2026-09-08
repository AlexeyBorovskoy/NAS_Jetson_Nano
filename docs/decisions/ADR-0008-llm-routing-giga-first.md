# ADR-0008: LLM routing — GigaChat first, DeepSeek fallback  
# ADR-0008: Маршрутизация LLM — GigaChat first, DeepSeek fallback

## Status / Статус

🇬🇧 **Accepted** (2026-09-04). Live cutover on Jetson verified 2026-09-08.  
🇷🇺 **Принято** (2026-09-04). Выкат на Jetson проверен 2026-09-08.

## Context / Контекст

🇬🇧 Gateway already supports `deepseek`, `gigachat`, `ollama`, and `cloudru`.  
🇷🇺 Шлюз поддерживает deepseek, gigachat, ollama и cloudru.

🇬🇧 Pre-cutover device default was DeepSeek with `prefer_local=true`.  
🇷🇺 До cutover на устройстве был DeepSeek и `prefer_local=true`.

🇬🇧 Live probe: `GigaChat-2` stable on `https://api.giga.chat/v1`; PERS freemium; **1 concurrent stream**.  
🇷🇺 Live: GigaChat-2 на api.giga.chat; freemium PERS; **1 поток**.

🇬🇧 Workstation with Ollama is out of architecture (ADR-0007).  
🇷🇺 Станция с Ollama вне архитектуры (ADR-0007).

## Decision / Решение

1. 🇬🇧 **Family default:** `LLM_PROVIDER=gigachat`, model `GigaChat-2`, base `https://api.giga.chat/v1`.  
   🇷🇺 **Default семьи:** gigachat / GigaChat-2 / api.giga.chat.
2. 🇬🇧 Talk bot sends `provider` from `TALK_BOT_LLM_PROVIDER` (default `gigachat`).  
   🇷🇺 Talk передаёт `TALK_BOT_LLM_PROVIDER=gigachat`.
3. 🇬🇧 DeepSeek = fallback on Giga 429/5xx (`LLM_GIGA_FALLBACK_DEEPSEEK`).  
   🇷🇺 DeepSeek = fallback при 429/5xx Giga.
4. 🇬🇧 `LLM_PREFER_LOCAL=false` in prod.  
   🇷🇺 `LLM_PREFER_LOCAL=false` в prod.
5. 🇬🇧 Cloud.ru FM = separate `provider=cloudru` (optional).  
   🇷🇺 Cloud.ru FM = `provider=cloudru` (опционально).
6. 🇬🇧 Family photo analysis remains denied (`LLM_ALLOW_IMAGE_ANALYSIS=false`).  
   🇷🇺 Анализ семейных фото запрещён.
7. 🇬🇧 Serialize Giga calls (one in-flight).  
   🇷🇺 Сериализация вызовов Giga (1 in-flight).

## Consequences / Последствия

🇬🇧 Family uses RU freemium; DeepSeek remains spare; balance via `/v1/provider/gigachat/balance`.  
🇷🇺 Семья на freemium РФ; DeepSeek запасной; balance через endpoint.

## Rollback / Откат

```env
LLM_PROVIDER=deepseek
TALK_BOT_LLM_PROVIDER=deepseek
```
