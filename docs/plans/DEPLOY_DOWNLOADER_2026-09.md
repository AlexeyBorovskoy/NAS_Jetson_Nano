# Выкат качалки и Telegram-бота / Downloader and Telegram bot rollout (2026-09)

> 🇷🇺 Только по команде владельца «деплой». Каждый шаг — проверка; расхождение — стоп.
> Спецификация: `docs/superpowers/specs/2026-09-19-home-downloader-design.md`. EN summary — в конце.

**Простой:** NAS API ~15 с (пересборка). Nextcloud, Immich, Samba не трогаются. На VPS — только SSH-сессия SOCKS.

## 1. Правило №13 — ДО
Как в `DEPLOY_STAGE_A_2026-09.md` §1: StartedAt `amnezia-*`, число пиров, внешние порты — записать.

## 2. Код и тесты на устройстве
```bash
cd ~/nasa && git pull --ff-only && git rev-parse --short HEAD
for t in tests/unit/test_aria2_hooks.py tests/unit/test_downloader_infra.py; do python3 "$t" >/dev/null 2>&1 && echo "ok $t" || echo "FAIL $t"; done
```

## 3. Секреты и ключи `.env` (значения не печатать)
- `ARIA2_RPC_SECRET` — сгенерировать (`openssl rand -hex 24`), записать в `config/.env` и в Windows Credential Manager `nas-aria2-rpc-secret`.
- `TELEGRAM_USERS`, `TELEGRAM_FAMILY_CHAT_ID` — из `docs/local/IDENTIFIERS.md`; `TELEGRAM_BOT_ENABLED=true`. Токен уже в `.env`.
- Проверка кавычек: `python3 scripts/quality/check_env_syntax.py config/.env` (правило №8).

## 4. Каталоги
⚠️ **§4 выполняется строго ДО §6:** если `/mnt/storage/downloads/.config` не существует, Docker создаст его от root, и контейнер (UID 1000) не сможет записать сессию.

```bash
sudo -S mkdir -p /mnt/storage/downloads/.incomplete /mnt/storage/downloads/.config /mnt/hdd2tb/Downloads/.incomplete
sudo -S chown -R 1000:1000 /mnt/storage/downloads
ls -ld /mnt/hdd2tb/Downloads   # NTFS: права задаёт ntfs-3g; запись проверяется в §6
```

## 5. SOCKS к VPS
```bash
sudo -S cp systemd/nas_jetson_nano-tg-socks.service /etc/systemd/system/ && sudo -S systemctl daemon-reload
sudo -S systemctl enable --now nas_jetson_nano-tg-socks.service
ss -tlnH | grep 1080                                   # только 172.17.0.1:1080
curl -s -o /dev/null -w "tg via socks: %{http_code}\n" --socks5-hostname 172.17.0.1:1080 https://api.telegram.org/   # 302
```
Если юнит в рестартах (ssh не смог занять `172.17.0.1:1080` — `ExitOnForwardFailure`) — стоп, разбор по `journalctl -u nas_jetson_nano-tg-socks`.

## 6. Контейнер качалки
```bash
docker compose -f docker/compose/docker-compose.downloads.yml --env-file config/.env up -d --build
docker exec homecloud_downloads sh -c 'touch /downloads/hdd/.w && rm /downloads/hdd/.w && echo hdd-writable'
docker stats --no-stream --format "{{.Name}} {{.MemUsage}}" homecloud_downloads
sudo -S cp systemd/nas_jetson_nano-dl-speed-* /etc/systemd/system/ && sudo -S systemctl daemon-reload
sudo -S systemctl enable --now nas_jetson_nano-dl-speed-day.timer nas_jetson_nano-dl-speed-night.timer
```

## 7. Режим приватности (владелец)
@BotFather → `/setprivacy` → @bobik_borovskoy_bot → **Disable**. Затем убрать бота из группы «Боровские» и добавить снова.
Проверка: `getMe` → `can_read_all_group_messages: true`.

## 8. NAS API
```bash
docker compose -f docker/compose/docker-compose.nas_jetson_nano-api.yml --env-file config/.env up -d --build
docker logs --since 2m homecloud_nasa_api 2>&1 | grep -i telegram     # "Telegram bot enabled", без ошибок
```

## 9. Проверка в группе «Боровские»
1. «@бобик привет» → ответ GigaChat. «мам, привет» (без обращения) → тишина.
2. «@бобик скачай <magnet небольшого легального образа Linux>» → «⏬ Принял…» → «⏬ Качаю: … на SSD» → «✅ Готово».
3. «@бобик скачай https://…/файл» (HTTP) → то же. «@бобик закачки» → список и свободное место.
4. Файлы видны с Windows: `\\192.168.0.50\hdd2tb\Downloads`.
5. `docker ps` — 14 контейнеров, здоровы; `free -m` — доступно ≥ 1 ГБ.
   - «бобик, привет» от члена семьи работает; «@бобикXYZ привет» — тишина (граница позывного).
   - «@бобик закачки» показывает последней строкой свободное место на SSD и HDD.

## Известные ограничения

**(а)** Имя хоста, резолвящееся во внутренний адрес через DNS-ребиндинг после проверки, не ловится полностью — `parse_link` проверяет только литерал, а aria2 сам ходит в сеть. Обходится только осознанно.

**(б)** При одновременном завершении двух закачек с одинаковым именем финальное переименование может перезаписать файл, появившийся за время копирования (узкое окно).

**(в)** Оповещения владельцу о долгой недоступности SOCKS в этом срезе нет — проверять `systemctl status nas_jetson_nano-tg-socks`.

## 10. Правило №13 — ПОСЛЕ; откат
| Что | Команда |
|---|---|
| бот | `TELEGRAM_BOT_ENABLED=false` в `.env` → `up -d` API (не `restart`: `.env` перечитывается только при пересоздании) |
| качалка | `docker compose -f docker/compose/docker-compose.downloads.yml down` |
| SOCKS | `sudo systemctl disable --now nas_jetson_nano-tg-socks.service` |
| приватность | @BotFather `/setprivacy` → Enable, перезайти бота в группу |

## EN summary

Owner-triggered rollout. Record the VPN baseline, pull and run the on-device tests, add the aria2 secret and
the Telegram whitelist to the device `.env`, create the download directories, start the SOCKS unit bound to
docker0 and check Telegram through it, build and start the aria2 container and the day/night speed timers.
The owner turns the bot's group privacy off and re-adds it to the family group. Rebuild the NAS API, then test
a question, a magnet link, an HTTP link and the list in the group, and confirm the files appear in the Samba
share. Verify call boundary enforcement (`@bobik` is answered, `@bobikXYZ` is silent) and that the list shows
free space on both SSD and HDD. **Known limitations:** hostnames resolved to internal IPs after DNS rebinding bypass
the link check (aria2 makes its own network request); simultaneous completion of same-name downloads has a narrow
file overwrite window; SOCKS unavailability alerts not in this slice — monitor `systemctl status nas_jetson_nano-tg-socks`.
Compare the VPN state after. Rollback steps are listed per component.
