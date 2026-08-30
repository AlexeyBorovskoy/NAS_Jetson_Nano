# Неизвестное / Unknowns

**Дата / Date:** 2026-08-30. Всё, что не удалось доказать в рамках read-only периметра — вынесено сюда, а не заменено предположением / Everything that could not be proven within the read-only perimeter — listed here, not replaced with a guess.

| ID | Unknown | Почему важно / Why it matters | Как проверить / How to verify | Риск / Risk |
|---|---|---|---|---|
| U-01 | Точный размер `/var/lib/docker` | Оценка реального дискового следа Docker-образов/volume | `sudo du -xhd1 /var/lib/docker` (требует root) | LOW — SSD свободен на 94%, не срочно |
| U-02 | Полный обход `/mnt/hdd2tb` по подкаталогам | `du` не завершился за 90с на NTFS-3g/FUSE, 1.4 ТБ данных; известен только `$RECYCLE.BIN`=27ГБ | Фоновый прогон много минут, вне read-only снимка | LOW — свободно 462ГБ (24%) |
| U-03 | `PasswordAuthentication`/`PermitRootLogin` — фактическое значение (не закомментированный default) | Единственный вход на устройство из дома — критичный периметр | `sshd -T \| grep -iE 'passwordauthentication\|permitrootlogin'` — безопасно, read-only, не root | MEDIUM — единственный путь к устройству |
| U-04 | Задан ли `NAS_JETSON_NANO_API_JWT_SECRET` явно в `.env` устройства | Если нет — секрет меняется при каждом рестарте контейнера | Нельзя проверить без чтения `.env` (запрещено правилами задачи) — владелец может подтвердить сам | LOW |
| U-05 | Свежесть restic-репозитория offsite на Vostro (Фаза 1) | Единственная offsite-копия БД | `ssh alexey@192.168.75.153` — недоступен вне корпоративной LAN Vostro, требует машину внутри сети | MEDIUM — не переверено с 24.08 независимо в этой сессии |
| U-06 | Установлен ли Ubuntu ESM (Extended Security Maintenance) на устройстве | Определяет, реально ли ОС без патчей безопасности с 04/2023 | `pro status` (не root-разрушительно, но не входило в разрешённый набор команд) | HIGH — прямо влияет на оценку TD-11 |
| U-07 | Точное имя переменной Telegram-бот-токена | Не найдено регэкспом по `.env.example` | Уточнить у владельца или другим паттерном grep | LOW — не критично, значение всё равно не выводилось бы |
| U-08 | `BACKUP_RETENTION_DAILY/WEEKLY/MONTHLY` — конкретные числа | Влияет на реальную глубину истории бэкапов | Прочитать значения (не секрет) — не входило в собранный набор этой части | LOW |
| U-09 | Используется ли ещё `docker-compose.stage1.yml` где-либо (скрипты/CI/README) | Устаревший файл, риск случайного запуска | `grep -rn "stage1" --include="*.sh" --include="*.md" --include="*.yml"` по всему репо | LOW |
| U-10 | CORS-конфигурация `llm-gateway` и `backup-api` | Проверен только `nas_jetson_nano-api`; не известно, так же ли широк CORS у двух других сервисов | Прочитать `main.py` этих двух сервисов | LOW-MEDIUM |
| U-11 | Реальный видеозвонок Nextcloud Talk снаружи LAN | Гипотеза о непроходимости NAT без coturn основана на статике (отсутствие образа), не на живом тесте | Тестовый звонок снаружи LAN с согласия участников | — (влияет на приоритет TD-03) |
| U-12 | Docker `json-file` logging driver — лимиты `max-size`/`max-file` в `daemon.json` | Отдельный от `/var/log/nasa-monitor` риск заполнения диска логами контейнеров | `cat /etc/docker/daemon.json` (без root, обычно доступен) | LOW-MEDIUM, не проверялось |
| U-13 | Точная версия cuDNN (не только csv-манифест) | Для полноты `DEPENDENCIES.md`, не критично — GPU-стек не используется проектом | `dpkg -l \| grep libcudnn` | LOW — GPU простаивает, не влияет на решения |
| U-14 | Модель GPU (число CUDA-ядер) live-командой, не по спецификации платы | Справочное значение сейчас взято из общеизвестной спецификации, не измерено | `deviceQuery` из CUDA samples (безопасно, не требует root) | LOW — GPU не используется, не влияет на решения |

## Комментарий по методу / Method note

🇷🇺 Ни один из пунктов выше не заменён предположением в других файлах аудита — там, где факт не был установлен, соответствующий раздел (`RISKS.md`, `SECURITY.md`, `DEPENDENCIES.md`) прямо ссылается на этот файл вместо того, чтобы утверждать что-то неподтверждённое.

🇬🇧 None of the items above were replaced with a guess in the other audit files — wherever a fact could not be established, the relevant section (`RISKS.md`, `SECURITY.md`, `DEPENDENCIES.md`) points here explicitly instead of asserting something unverified.
