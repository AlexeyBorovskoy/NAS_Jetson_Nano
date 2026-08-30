# CODEX_NEXTCLOUD_PROMPT

Ты агент Codex в проекте Home Cloud Jetson Public. Работай малыми шагами. Не используй реальные секреты. Перед destructive-командами запроси подтверждение. Не открывай сервисы наружу. После каждого шага дай проверку и rollback.
You are a Codex agent in the Home Cloud Jetson Public project. Work in small steps. Do not use real secrets. Ask for confirmation before destructive commands. Do not expose services to the internet. After each step, provide a verification check and a rollback procedure.

## Задача / Task

Разверни Nextcloud по `docs/06_NEXTCLOUD_DESIGN.md` и `docker/compose/docker-compose.nextcloud.yml`.
Deploy Nextcloud following `docs/06_NEXTCLOUD_DESIGN.md` and `docker/compose/docker-compose.nextcloud.yml`.

Сначала проверь `.env`, storage, доступность портов и Docker.
First check `.env`, storage, port availability, and Docker.
