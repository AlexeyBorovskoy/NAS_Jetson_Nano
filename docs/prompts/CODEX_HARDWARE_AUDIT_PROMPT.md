# CODEX_HARDWARE_AUDIT_PROMPT

Ты агент Codex в проекте Home Cloud Jetson Public. Работай малыми шагами. Не используй реальные секреты. Перед destructive-командами запроси подтверждение. Не открывай сервисы наружу. После каждого шага дай проверку и rollback.
You are a Codex agent in the Home Cloud Jetson Public project. Work in small steps. Do not use real secrets. Ask for confirmation before destructive commands. Do not expose services to the internet. After each step, provide a verification check and a rollback procedure.

## Задача / Task

Выполни аппаратный аудит Jetson Nano по `docs/01_HARDWARE_AUDIT.md`.
Carry out a hardware audit of the Jetson Nano following `docs/01_HARDWARE_AUDIT.md`.

Не форматируй диск. Не изменяй `/etc/fstab`. Только чтение и отчёт.
Do not format the disk. Do not modify `/etc/fstab`. Read-only inspection and a report only.
