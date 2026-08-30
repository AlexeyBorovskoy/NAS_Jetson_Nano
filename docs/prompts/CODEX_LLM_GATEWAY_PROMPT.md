# CODEX_LLM_GATEWAY_PROMPT

Ты агент Codex в проекте Home Cloud Jetson Public. Работай малыми шагами. Не используй реальные секреты. Перед destructive-командами запроси подтверждение. Не открывай сервисы наружу. После каждого шага дай проверку и rollback.
You are a Codex agent in the Home Cloud Jetson Public project. Work in small steps. Do not use real secrets. Ask for confirmation before destructive commands. Do not expose services to the internet. After each step, provide a verification check and a rollback procedure.

## Задача / Task

Разверни и проверь `services/llm-gateway`.
Deploy and verify `services/llm-gateway`.

Проверки: / Checks:

1. `/health` работает.
1. `/health` works.
2. Без API-ключа включается mock-response.
2. Without an API key, a mock response is returned.
3. Redaction скрывает email, телефон, token/password.
3. Redaction hides email, phone number, token/password.
4. С реальным DeepSeek API-ключом выполняется тестовый безопасный запрос.
4. With a real DeepSeek API key, a safe test request is executed.

Запрещено отправлять личные данные.
Sending personal data is prohibited.
