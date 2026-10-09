# 10. Безопасность и приватность / Security & Privacy

## DP-2 — подготовка ограничения Docker API, 2026-10-09

🇷🇺 Подготовлен локальный вариант NAS API с UID/GID `10001:10001`, без Linux
capabilities и с `no-new-privileges`. Прямой `docker.sock` в API удалён. Только
отдельный `services/docker-status-proxy` получает сокет: он допускает исключительно
GET `/containers/json` (без query или с `all=1`), возвращает только Id/Names/Status/
Image/State. POST, inspect, logs, images, exec и другие пути не передаются Docker.
При отказе бэкенда возвращается 503, а не пустой успешный список.

Прокси не публикует порт хоста и подключён только к внутренней сети `docker_status`.
API также подключён к прежней сети приложений. Монтирование сокета с `:ro` само по
себе не является запретом Docker POST; запрет реализован проверкой HTTP-маршрута.
Прокси остаётся привилегированным относительно Docker из-за доступа к сокету:
это отдельная граница доверия, а не способ сделать сам сокет безопасным.

**Изменение поведения:** перезапуск контейнеров через NAS API отключается (503),
даже для владельца. Восстановление остаётся задачей существующего хостового watchdog.
Новый вариант не развёрнут; контейнерный smoke-test на ARM64 ещё требуется.

Перед выкатом владелец проверяет права UID 10001 на каталог логов, API JSONL и его
ротации, `telegram-state.json` и `downloads-ledger.json`, а также чтение мониторингового
снимка и каталогов статистики. Не выполнять рекурсивный chown общих каталогов.
Хостовые report/backup-скрипты и root-only конфигурации могут быть недоступны этому
UID: проверить операции отдельно, не давать API sudo или Docker-группу для обхода.
Контейнеры Nextcloud/Immich и их volumes при этой подготовке не изменяются.

Проверки: `python tests/unit/test_docker_status_proxy.py`,
`python -m pytest tests/nas_api -q`, Compose config с примером окружения.
Нужны живые проверки `/v1/containers`, health и UID после разрешённого выката.
Откат — предыдущие Dockerfile/Compose и API-модули; возвращение прямого сокета
возвращает прежние широкие права и требует осознанного решения, не автоматического fallback.

🇬🇧 Local DP-2 preparation runs NAS API as UID/GID 10001 with dropped capabilities,
no-new-privileges and no Docker socket. An unpublished proxy on an internal network
allows only container-list GET, filters output fields and fails with 503. The proxy
itself remains trusted because it holds the socket. API container restart is disabled;
host watchdog recovery remains. ARM64 runtime, mounted-file permissions and host-script
compatibility must be verified before deployment; never restore access via sudo or a
Docker group automatically. Rollback restores the previous privilege boundary explicitly.

## 1. Принципы / Principles

🇷🇺
1. Закрытая домашняя сеть по умолчанию.
2. Внешний доступ только через VPN/SSH tunnel.
3. Минимизация прав контейнеров.
4. Секреты вне Git.
5. Персональные данные не отправляются в LLM.
6. Backup обязателен.

🇬🇧
1. Closed home network by default.
2. External access only via VPN/SSH tunnel.
3. Minimal container privileges.
4. Secrets out of Git.
5. Personal data never sent to external LLMs.
6. Backup is mandatory.

## 2. DeepSeek privacy policy

🇷🇺 DeepSeek в своей политике указывает, что сервисы не предназначены для обработки sensitive personal data. Поэтому проект запрещает отправлять в DeepSeek семейные фото, контакты, календари, личные документы и полные backup-архивы.

🇬🇧 DeepSeek policy states its services are not intended for sensitive personal data. Therefore this project prohibits sending family photos, contacts, calendars, personal documents, or backup archives to DeepSeek.

## 3. Сетевые правила / Network access rules

| Сервис / Service | Доступ / Access |
|---|---|
| SSH | LAN/VPN only |
| Samba | LAN only |
| Nextcloud | LAN/VPN only |
| Immich | LAN/VPN only |
| LLM Gateway | LAN only, preferred localhost/internal |
| БД / Databases | Docker internal only |

## 4. Hardening / Базовая защита

```bash
sudo apt update && sudo apt upgrade -y
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from 192.168.0.0/24 to any port 22 proto tcp
sudo ufw allow from 192.168.0.0/24 to any port 445 proto tcp
sudo ufw enable
```

🇷🇺 Правила firewall адаптируются после выбора VPN и reverse proxy.
🇬🇧 Firewall rules are adapted after choosing VPN and reverse proxy.

## 5. Публичный GitHub / Public GitHub

🇷🇺 Перед публикацией:
🇬🇧 Before publishing:

```bash
./scripts/security/check_no_secrets.sh
git status --short
```

🇷🇺 Запрещено публиковать:
🇬🇧 Never publish:

- `.env` файлы / files
- реальные IP внешних серверов / real IPs of external servers
- персональные домены, если раскрывают личные данные / personal domains revealing personal data
- серийные номера HDD / HDD serial numbers
- API-ключи / API keys
- дампы БД / DB dumps
- фото и backup-манифесты / photos and backup manifests
