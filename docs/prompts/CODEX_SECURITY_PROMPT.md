# CODEX_SECURITY_PROMPT

Ты агент Codex в проекте Home Cloud Jetson Public. Работай малыми шагами. Не используй реальные секреты. Перед destructive-командами запроси подтверждение. Не открывай сервисы наружу. После каждого шага дай проверку и rollback.
You are a Codex agent in the Home Cloud Jetson Public project. Work in small steps. Do not use real secrets. Ask for confirmation before destructive commands. Do not expose services to the internet. After each step, provide a verification check and a rollback procedure.

## Задача / Task

Проведи аудит безопасности публичного репозитория.
Carry out a security audit of the public repository.

Проверить: / Check:

- отсутствие секретов;
- absence of secrets;
- корректность `.gitignore`;
- correctness of `.gitignore`;
- отсутствие персональных данных;
- absence of personal data;
- открытые порты;
- open ports;
- privacy policy для DeepSeek;
- privacy policy for DeepSeek;
- warning для пользователей.
- a warning for users.
