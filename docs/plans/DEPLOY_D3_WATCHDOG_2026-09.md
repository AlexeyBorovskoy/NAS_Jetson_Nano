# Выкат D3 — внешний сторож / D3 external watchdog rollout (2026-09)

> 🇷🇺 Только по команде владельца «деплой». Каждый шаг — проверка; расхождение — стоп.
> Спецификация: `docs/superpowers/specs/2026-09-19-cloudru-watchdog-design.md`. EN summary — в конце.

## 0. Спайк в Cloud.ru (до выката; ресурсы — тестовые, удаляются)
Проверить из разовой Container Job на образе `python:3.12-alpine`:
```sh
python -c "import urllib.request as u; print(u.urlopen('https://api.telegram.org', timeout=15).status)"
```
| Вопрос | Как понять | Если «нет» |
|---|---|---|
| Образ из публичного реестра тянется | задача стартовала | собрать `services/watchdog/job` на VPS (`docker build`, amd64) → Artifact Registry Cloud.ru |
| Telegram доступен | `200` или `302` в журнале задачи | основной путь — `notify` через VPS; слепое пятно «VPS мёртв + Telegram закрыт» записать в спецификацию |
| Расписание есть | в форме задачи есть cron | стоп, решение владельца |

## 1. Правило №13 — ДО
```bash
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 \
  'docker ps --format "{{.Names}} {{.Status}}" | grep amnezia; docker exec amnezia-awg2 wg show | grep -c "^peer"; ss -tulnH | awk "{print \$5}" | grep -vE "^(127\.|\[::1\]|10\.|172\.)" | sort -u'
```
Записать: StartedAt `amnezia-*`, число пиров, внешние порты (22/443/40568).

## 2. Ключ сторожа (на рабочей станции, вне git)
```bash
ssh-keygen -t ed25519 -N "" -C nas-watchdog -f "$SCRATCH/nas-watchdog"
ssh-keyscan -t ed25519 95.163.176.103 > "$SCRATCH/vps_known_hosts"
```
Приватный ключ — сразу в секреты Cloud.ru и Windows Credential Manager (`nas-watchdog-ssh-key`), с диска удалить.

## 3. VPS
```bash
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'mkdir -p /root/naswatch'
scp -i ~/.ssh/borovskoy_new_ed25519 services/watchdog/vps/{nas_liveness.py,install_vps.sh} root@95.163.176.103:/root/naswatch/
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'sshd -T | grep -iE "^(allowusers|allowgroups|denyusers|authorizedkeysfile) " || echo "ограничений нет"'
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 "bash /root/naswatch/install_vps.sh '$(cat "$SCRATCH/nas-watchdog.pub")'"
# с рабочей станции ключом сторожа:
ssh -i "$SCRATCH/nas-watchdog" naswatch@95.163.176.103 check     # одна строка JSON
ssh -i "$SCRATCH/nas-watchdog" naswatch@95.163.176.103 bash      # {"error": "unknown command"}
ssh -i "$SCRATCH/nas-watchdog" -W 127.0.0.1:22 naswatch@95.163.176.103   # administratively prohibited
```
Если `AllowUsers` задан — **стоп**: добавлять `naswatch` в sshd_config только отдельным решением.
`authorizedkeysfile` в выводе — нестандартный путь до `authorized_keys` (не `.ssh/authorized_keys` по
умолчанию): установщик пишет ключ туда, где sshd реально ищет — **стоп**, проверить путь вручную.

## 4. chat_id владельца
Владелец пишет `/start` боту @bobik_borovskoy_bot. Команда ниже выполняется **на самом Jetson**
(`ssh admin@192.168.0.50`, затем блок целиком): `~/.ssh/id_ed25519` — ключ устройства к VPS, на
рабочей станции его нет. Токен идёт через stdin, не через
командную строку (иначе виден в `ps` на VPS), и не попадает в аргументы curl: URL передаётся через `curl -K -`:
```bash
cd ~/nasa && grep '^TELEGRAM_BOT_TOKEN=' config/.env | cut -d= -f2- | tr -d '"' \
 | ssh -i ~/.ssh/id_ed25519 root@95.163.176.103 'read -r T; printf "url = \"https://api.telegram.org/bot%s/getUpdates\"\n" "$T" | curl -s -K -' \
 | python3 -c 'import json,sys; print({u["message"]["chat"]["id"] for u in json.load(sys.stdin)["result"] if "message" in u})'
```
⚠️ Если семейный Talk-бот (`@бобик`) уже работает с этим токеном через long polling, `getUpdates`
вернёт `409 Conflict` (второй одновременный опрос запрещён Telegram) — команда выше отдаст пустой
результат, а не ошибку. В этом случае `chat_id` брать из журнала самого бота
(`docker logs homecloud_nasa_api`, там уже видны входящие сообщения), а не этой командой.

## 5. Cloud.ru
Container Job: образ (по итогам §0), расписание `*/10 * * * *`, `max instances = 1`, таймаут 60 с,
самая малая конфигурация. Секреты — ключи из `services/watchdog/job/job.env.example`.
Ручной запуск → в журнале `ok event=none api=200 nc=200`.

## 6. Боевая проверка (время выбирает владелец; снаружи NAS ~20 мин не виден, дома работает)
⚠️ Выполнять **из дома (LAN)**: на время проверки пропадает и внешний SSH-доступ на 10022 (сам туннель
и есть то, что мы гасим). `$P` в одинарных кавычках на рабочей станции разворачивается на ней же, а не
на Jetson, где эта переменная не задана — пароль должен читаться на самом Jetson:
```bash
ssh admin@192.168.0.50 'P=$(grep "^NEXTCLOUD_ADMIN_PASSWORD=" ~/nasa/config/.env | cut -d= -f2- | tr -d "\""); echo "$P" | sudo -S systemctl stop nasa-tunnel.service'
# ждать: 2 запуска → «🔴 NAS не отвечает …» в Telegram
ssh admin@192.168.0.50 'P=$(grep "^NEXTCLOUD_ADMIN_PASSWORD=" ~/nasa/config/.env | cut -d= -f2- | tr -d "\""); echo "$P" | sudo -S systemctl start nasa-tunnel.service'
# следующий запуск → «✅ NAS снова на связи, простой N мин»
```

## Известные ограничения
(а) Ручной `check` во время реальной аварии «съедает» тревогу: состояние на VPS помечается
отправленным, и настоящая задача в Cloud.ru её больше не пошлёт. Для отладки — отдельный файл
состояния, под root на VPS: `NASWATCH_STATE=/tmp/naswatch-debug.json /usr/local/bin/nas-liveness check`.
(б) Если не сработали оба пути доставки (Telegram напрямую и `notify` через VPS), событие теряется
до повтора через 24 ч, а «recovered» — насовсем (следующая проверка увидит только «снова всё хорошо»
без факта простоя). Задача в этом случае завершается с кодом 1 — видно в журнале Cloud.ru.

## 7. Правило №13 — ПОСЛЕ; откат
Сверить с §1. Откат: удалить задачу в Cloud.ru; на VPS `userdel -r naswatch && rm /usr/local/bin/nas-liveness`.

Смена ключа сторожа: повторный запуск install_vps.sh с новым ключом старый НЕ удаляет — строку старого ключа убрать из /var/lib/naswatch/.ssh/authorized_keys вручную. Смена токена @bobik — в двух местах: config/.env Jetson и секреты Cloud.ru.

## EN summary
Spike in Cloud.ru first (image pull, Telegram reachability, schedules). Record the VPN baseline, create a
dedicated ed25519 key, install `nas-liveness` for a no-sudo `naswatch` user with a single-command key, and
verify that no shell or forwarding is allowed. Get the owner's chat_id via `/start`, create the Cloud.ru job
every 10 minutes with max one instance, then prove it by stopping the Jetson tunnel for 20 minutes. Compare
the VPN state after. Rollback: delete the job, remove the user and the script. Rotating the watchdog key does not remove the old one; delete its line by hand. A new bot token must be set both in the Jetson .env and in the Cloud.ru secrets.

Known limits: a manual `check` during a real outage marks the alert as already sent, silencing the real one; and if both delivery paths fail, the event is lost until the next day's repeat (a "recovered" is lost for good) and the job exits with code 1.
