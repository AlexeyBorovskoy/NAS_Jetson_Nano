# Выкат качалки и Telegram-бота / Downloader and Telegram bot rollout (2026-09)

> 🇷🇺 Только по команде владельца «деплой». Каждый шаг — проверка; расхождение — стоп.
> Спецификация: `docs/superpowers/specs/2026-09-19-home-downloader-design.md`. EN summary — в конце.

**Простой:** NAS API ~15 с (пересборка). Nextcloud, Immich, Samba не трогаются. На VPS — только SSH-сессия SOCKS.

## 1. Правило №13 — ДО
Как в `DEPLOY_STAGE_A_2026-09.md` §1: StartedAt `amnezia-*`, число пиров, внешние порты — записать.

## 2. Код и тесты на устройстве
```bash
cd ~/nasa
git status --porcelain   # непусто — СТОП: ручные правки на устройстве, git pull их затрёт (см. CLAUDE.md)
PREV=$(git rev-parse HEAD)   # для отката §10
git pull --ff-only && git rev-parse --short HEAD
for t in tests/unit/test_aria2_hooks.py tests/unit/test_downloader_infra.py; do
  echo "== $t =="
  python3 "$t"              # вывод не подавляется: FAIL должен быть виден целиком
done
```

## 3. Секреты и ключи `.env` (значения не печатать)
- `ARIA2_RPC_SECRET` — сгенерировать и дописать одной командой, без промежуточного вывода на экран:
  ```bash
  s=$(openssl rand -hex 24); printf 'ARIA2_RPC_SECRET=%s\n' "$s" >> config/.env; unset s
  ```
  Копия — Windows Credential Manager `nas-aria2-rpc-secret`, заводится **со станции**: значение читается с
  устройства по ssh и подаётся в stdin команды добавления, не в аргументах и не на экране.
- `TELEGRAM_USERS`, `TELEGRAM_FAMILY_CHAT_ID` — из `docs/local/IDENTIFIERS.md`; `TELEGRAM_BOT_ENABLED=true`. Токен
  уже в `.env`. `TELEGRAM_OWNER_LOGIN=admin` — логин владельца (адресные сообщения бота: незнакомцы, чужие
  группы). Логины в `TELEGRAM_USERS` — те же, что в Talk: квота на человека общая между ботами.
- Проверка кавычек: `python3 scripts/quality/check_env_syntax.py config/.env` (правило №8).

## 4. Каталоги
⚠️ **§4 выполняется строго ДО §6:** если `/mnt/storage/downloads/.config` не существует, Docker создаст его от root, и контейнер (UID 1000) не сможет записать сессию.

```bash
mountpoint -q /mnt/hdd2tb || { echo "HDD не смонтирован"; exit 1; }
sudo -S mkdir -p /mnt/storage/downloads/.incomplete /mnt/storage/downloads/.config /mnt/hdd2tb/Downloads/.incomplete
sudo -S chown -R 1000:1000 /mnt/storage/downloads
touch /mnt/hdd2tb/Downloads/.nas-hdd-marker   # И6: entrypoint и страж (_disk_free) проверяют его каждый раз
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
Ключ и пользователь SOCKS — те же переменные (`VPS_SSH_KEY`, `VPS_USER`), что у рабочего туннеля (И7); отдельно проверять нечего, но при смене ключа менять в одном месте `.env`, а не в двух юнитах.

Тот же путь, но изнутри контейнера NAS API (именно так туда ходит бот) — без токена в команде:
```bash
docker exec homecloud_nasa_api python3 -c "
import httpx
r = httpx.get('https://api.telegram.org/', proxy='socks5://172.17.0.1:1080', timeout=10)
print(r.status_code)"
```

## 6. Контейнер качалки
```bash
docker compose -f docker/compose/docker-compose.downloads.yml --env-file config/.env up -d --build
docker exec homecloud_downloads sh -c 'touch /downloads/hdd/.w && rm /downloads/hdd/.w && echo hdd-writable'
docker stats --no-stream --format "{{.Name}} {{.MemUsage}}" homecloud_downloads
sudo -S cp systemd/nas_jetson_nano-dl-speed-* /etc/systemd/system/ && sudo -S systemctl daemon-reload
sudo -S systemctl enable --now nas_jetson_nano-dl-speed-day.timer nas_jetson_nano-dl-speed-night.timer
h=$(date +%H); [ "$h" -ge 8 ] && [ "$h" -lt 23 ] && unit=day || unit=night   # таймер сработает только в своё время
sudo -S systemctl start nas_jetson_nano-dl-speed-$unit.service
journalctl -u nas_jetson_nano-dl-speed-$unit.service -n 5 --no-pager | grep -q '"result":"OK"' \
  && echo "лимит скорости применён ($unit)" || echo "СТОП: aria2_speed.sh не подтвердил OK — смотреть журнал"
```

## 7. Режим приватности (владелец)
@BotFather → `/setprivacy` → @bobik_borovskoy_bot → **Disable**. Затем убрать бота из группы «Боровские» и добавить снова.

Jetson напрямую до Telegram не доходит — проверки идут через VPS, токен через stdin (не в argv, не в файле на
диске), URL — через `curl -K -`, как в `DEPLOY_D3_WATCHDOG_2026-09.md` §4:
```bash
cd ~/nasa && grep '^TELEGRAM_BOT_TOKEN=' config/.env | cut -d= -f2- | tr -d '"' \
 | ssh -i ~/.ssh/id_ed25519 root@95.163.176.103 'read -r T; printf "url = \"https://api.telegram.org/bot%s/getMe\"\n" "$T" | curl -s -K -'
```
→ `can_read_all_group_messages: true`.

**Сброс хвоста накопленных апдейтов — до §8** (до того, как бот начнёт опрашивать): иначе бот ответит на
`/start` и все «@бобик …» за то время, что был выключен.
```bash
cd ~/nasa && grep '^TELEGRAM_BOT_TOKEN=' config/.env | cut -d= -f2- | tr -d '"' \
 | ssh -i ~/.ssh/id_ed25519 root@95.163.176.103 'read -r T; printf "url = \"https://api.telegram.org/bot%s/getUpdates?offset=-1\"\n" "$T" | curl -s -K -'
```

## 8. NAS API
```bash
docker compose -f docker/compose/docker-compose.nas_jetson_nano-api.yml --env-file config/.env up -d --build
timeout 60 sh -c 'until docker logs homecloud_nasa_api 2>&1 | grep -q "telegram connected"; do sleep 2; done' \
  && echo "бот подключился" || echo "СТОП: не дождались \"telegram connected\" за 60 с — смотреть журнал"
docker logs --since 2m homecloud_nasa_api 2>&1 | grep -i telegram     # без ошибок
docker stats --no-stream --format "{{.Name}} {{.MemUsage}}" homecloud_nasa_api   # предел 128 МБ (mem_limit)
```

## 9. Проверка в группе «Боровские»
1. «@бобик привет» → ответ GigaChat. «мам, привет» (без обращения) → тишина.
2. «@бобик скачай <magnet небольшого легального образа Linux>» → «⏬ Принял…» → «⏬ Качаю: … на SSD» → «✅ Готово».
3. «@бобик скачай https://…/файл» (HTTP) → то же. «@бобик закачки» → список и свободное место.
4. Файлы видны с Windows: `\\192.168.0.50\hdd2tb\Downloads`.
5. `docker ps` — 14 контейнеров, здоровы; `free -m` — доступно ≥ 1 ГБ.
   - «бобик, привет» от члена семьи работает; «@бобикXYZ привет» — тишина (граница позывного).
   - «@бобик закачки» показывает последней строкой свободное место на SSD и HDD.
6. Память разговора: «бобик, что приготовить на ужин?» → ответ → «бобик, а без мяса?» (ответ учитывает
   предыдущий вопрос) → «бобик, забудь» → «🐕 Забыл, начнём сначала.»

## Известные ограничения

**(а)** Имя хоста, резолвящееся во внутренний адрес через DNS-ребиндинг после проверки, не ловится полностью — `parse_link` проверяет только литерал, а aria2 сам ходит в сеть. Обходится только осознанно.

**(б)** При одновременном завершении двух закачек с одинаковым именем финальное переименование может перезаписать файл, появившийся за время копирования (узкое окно).

**(в)** Оповещения владельцу о долгой недоступности SOCKS в этом срезе нет — проверять `systemctl status nas_jetson_nano-tg-socks`.

**(г)** `parse_link` проверяет только исходную ссылку; сам aria2 следует HTTP-редиректам и ходит к трекерам и
web-seed'ам, перечисленным внутри `.torrent`, — это не полный SSRF-фильтр.

**(д)** SOCKS слушает `172.17.0.1` (docker0) не только для контейнеров этого хоста: из-за weak host model Linux
адрес доступен любому в LAN, кто проложит маршрут через Jetson как шлюз.

**(е)** После перемонтирования `/mnt/hdd2tb` (отвал/восстановление диска) контейнеры `homecloud_downloads` и
`homecloud_nasa_api` могут держать мёртвую точку монтирования — пересоздавать оба:
`docker compose -f docker/compose/docker-compose.downloads.yml --env-file config/.env up -d --force-recreate` и
то же для `docker-compose.nas_jetson_nano-api.yml`.

**(ё)** Магнит, добавленный напрямую через AriaNg (не через бота), после получения метаданных остаётся на
паузе — маршрутизация на SSD/HDD в этом случае не срабатывает; снимать паузу вручную в AriaNg.

## 10. Правило №13 — ПОСЛЕ; откат
Правило №13 — ПОСЛЕ: как в §1, сравнить с записанным ДО (`amnezia-*` не перезапускались, число пиров WireGuard
не уменьшилось, наружу по-прежнему только 22/443/40568).

| Что | Команда |
|---|---|
| код API целиком | `git checkout $PREV -- services/nas_jetson_nano-api docker/compose/docker-compose.nas_jetson_nano-api.yml` (`$PREV` — записан в §2), затем `docker compose -f docker/compose/docker-compose.nas_jetson_nano-api.yml --env-file config/.env up -d --build` |
| только бот | `TELEGRAM_BOT_ENABLED=false` в `.env` → `docker compose -f docker/compose/docker-compose.nas_jetson_nano-api.yml --env-file config/.env up -d` (не `restart`: `.env` перечитывается только при пересоздании) |
| качалка | `docker compose -f docker/compose/docker-compose.downloads.yml --env-file config/.env down`; `sudo systemctl disable --now nas_jetson_nano-dl-speed-day.timer nas_jetson_nano-dl-speed-night.timer` |
| SOCKS | `sudo systemctl disable --now nas_jetson_nano-tg-socks.service` |
| приватность | @BotFather `/setprivacy` → Enable, перезайти бота в группу |

После любого отката — **повторить §1 и сравнить** с записанным ДО; расхождение — стоп и разбор, не повтор отката.

## EN summary

Owner-triggered rollout. Record the VPN baseline and the current HEAD (`$PREV`, for rollback), check for
uncommitted on-device edits before pulling, run the on-device tests with output never suppressed, add the aria2
secret (written without ever echoing it) and the Telegram whitelist plus `TELEGRAM_OWNER_LOGIN` to the device
`.env`, confirm the HDD is actually mounted and create the download directories including the
`.nas-hdd-marker` file the entrypoint and the guard both check for, start the SOCKS unit bound to docker0 and
check Telegram through it both directly and from inside the NAS API container. Build and start the aria2
container, the day/night speed timers, and immediately start the timer matching the current time of day,
confirming its `"result":"OK"`. The owner turns the bot's group privacy off and re-adds it to the family group;
`getMe` and the `getUpdates?offset=-1` tail reset both run through the VPS with the token piped over stdin, never
in argv. Rebuild the NAS API and wait for the `"telegram connected"` log line (not just "enabled") before
testing a question, a magnet link, an HTTP link and the list in the group, and confirm the files appear in the
Samba share and the container stays under its 128 MB limit. Verify call boundary enforcement (`@bobik` is
answered, `@bobikXYZ` is silent) and that the list shows free space on both SSD and HDD. Also verify per-chat
conversation memory: a follow-up question uses the previous one as context, and «бобик, забудь» clears it with
a confirmation reply. **Known limitations:**
hostnames resolved to internal IPs after DNS rebinding bypass the link check, and aria2 itself follows redirects
and contacts trackers/web-seeds named inside a `.torrent` (not a full SSRF filter); simultaneous completion of
same-name downloads has a narrow file overwrite window; SOCKS unavailability alerts not in this slice — monitor
`systemctl status nas_jetson_nano-tg-socks`; the SOCKS proxy on 172.17.0.1 is reachable from anywhere in the LAN
that can route through the Jetson, not just from containers on the host; after the HDD is remounted both the
downloads and the NAS API containers may hold a stale mount and need `--force-recreate`; a magnet added directly
through AriaNg stays paused after metadata since only the bot routes it — resume it manually. Compare the VPN
state after. Rollback restores `$PREV` for the API code, or narrower steps per component, then repeats §1 and
compares against the baseline.
