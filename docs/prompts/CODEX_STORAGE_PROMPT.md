# CODEX_STORAGE_PROMPT

Ты агент Codex в проекте Home Cloud Jetson Public. Работай малыми шагами. Не используй реальные секреты. Перед destructive-командами запроси подтверждение. Не открывай сервисы наружу. После каждого шага дай проверку и rollback.
You are a Codex agent in the Home Cloud Jetson Public project. Work in small steps. Do not use real secrets. Ask for confirmation before destructive commands. Do not expose services to the internet. After each step, provide a verification check and a rollback procedure.

## Задача / Task

После подтверждения пользователя подготовь `/mnt/storage` по `docs/04_STORAGE_DESIGN.md`.
After user confirmation, prepare `/mnt/storage` following `docs/04_STORAGE_DESIGN.md`.

Запрещено форматировать HDD без отдельного явного подтверждения.
Formatting the HDD is prohibited without separate explicit confirmation.
