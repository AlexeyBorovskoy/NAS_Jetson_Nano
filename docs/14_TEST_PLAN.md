# 14. Test Plan

## 1. Hardware tests

| Тест / Test | Команда / Command | Критерий / Criterion |
|---|---|---|
| RAM | `free -h` | no swap storm / система не в swap storm |
| Storage preflight | `sudo bash scripts/storage/storage_preflight.sh` | `/mnt/storage` is a separate ext4 mountpoint, not microSD |
| Storage | `df -h /mnt/storage && mountpoint /mnt/storage` | disk accessible and mounted / доступен и смонтирован |
| USB errors | `dmesg` | no I/O/reset loop / нет I/O/reset loop |
| SMART | `smartctl -a` | no critical errors / нет критичных ошибок |
| Stage 0 direct-link | `nmap -sn 192.168.1.0/24` | Jetson visible as separate host |
| Stage 0 SSH | `ssh <user>@<jetson-direct-link-ip>` | SSH login from laptop works |
| Target LAN после переноса | `ping 192.168.0.50` | accessible after connecting to router |

### 1.1. Existing data HDD intake

Если пользователь подключает HDD с уже существующими данными, особенно NTFS-диск
после Windows, сначала выполняется только read-only проверка. Такой диск не
форматируется, не добавляется в `/etc/fstab` и не монтируется сразу в
`/mnt/storage`.

| Тест / Test | Команда / Command | Критерий / Criterion |
|---|---|---|
| Services stopped before storage check | `docker ps` + `docker compose ... stop` | Nextcloud/Immich не пишут в `/mnt/storage` |
| No false `/mnt/storage` mount | `mountpoint /mnt/storage` | понятно, смонтирован ли внешний диск или это каталог на microSD |
| Existing HDD detected | `lsblk -o NAME,TYPE,SIZE,FSTYPE,LABEL,MOUNTPOINT,MODEL,TRAN,RO` | виден ожидаемый USB HDD и раздел |
| No USB enumeration loop | `journalctl -k -n 120 --no-pager \| grep -i -E "error -71|unable to enumerate"` | пусто |
| Read-only mount | `sudo mount -t ntfs-3g -o ro /dev/sdXN /mnt/hdd-check` | диск смонтирован отдельно от `/mnt/storage` |
| Data presence without leaking names | `df -hT /mnt/hdd-check && find /mnt/hdd-check -mindepth 1 -maxdepth 1 | wc -l` | размер корректный, данные видны, имена файлов не публикуются |
| No forced repair | manual check | не использовались `force`, форматирование, repartition, `setup_disk.sh` |
| Compression feasibility | metadata-only extension/category scan | если данные в основном фото/видео/архивы, lossless-архивирование не считается заменой носителя нужного объёма |

## 2. Samba/SFTP

| Тест / Test | Критерий / Criterion |
|---|---|
| Windows открывает шару | Да |
| Linux подключается по SFTP | Да |
| Запись тестового файла | Да |
| Права доступа корректны | Да |

## 3. Nextcloud

1. Вход в web-интерфейс.
2. Создание пользователя.
3. Загрузка файла.
4. Подключение Android-клиента.
5. Проверка Contacts/Calendar.
6. Проверка DAVx5.

## 4. Immich

1. Вход в web-интерфейс.
2. Подключение Android-клиента.
3. Загрузка 20–50 фото.
4. Загрузка 2–3 видео.
5. Проверка `docker stats`.
6. Проверка работы после перезапуска контейнеров.

## 5. LLM Gateway

1. `GET /health`.
2. Тест mock-mode.
3. Тест DeepSeek API без персональных данных.
4. Проверка лимитов.
5. Проверка redaction.

## 6. VPS + Reverse SSH Tunnel

| Тест / Test | Команда / Command | Критерий / Criterion |
|---|---|---|
| Tunnel service active | `systemctl status nas_jetson_nano-tunnel.service` | active (running) |
| Tunnel ports on VPS | `ss -tlnp \| grep -E '18080\|12283\|18090\|10022'` | 4 порта на 127.0.0.1 |
| nginx container | `docker ps --filter name=nas_jetson_nano_nginx` | Up, network_mode host |
| Nextcloud via VPS | `wget -q -O /dev/null -S http://95.163.176.103:8080/` + `/status.php` | root HTTP 302, `/status.php` HTTP 200 |
| Immich via VPS | `wget -q -O /dev/null -S http://95.163.176.103:2283/` | HTTP 200 |
| LLM GW via VPS | `wget -q -O /dev/null -S http://95.163.176.103:8090/health` | HTTP 200 |
| SSH via tunnel | `ssh -p 10022 admin@127.0.0.1` (с VPS) | prompt |
| Tunnel restart | `systemctl restart nas_jetson_nano-tunnel.service` | re-establishes within 30s |
| Reboot autorecovery | `sudo systemctl reboot`, then poll tunnel/storage/HTTP | tunnel returns, `/mnt/storage` is mounted, containers healthy, VPS HTTP 200 |

## 7. Backup/Restore

1. Запустить `sudo bash scripts/storage/storage_preflight.sh`.
2. Создать тестовый backup.
3. Проверить список snapshots.
4. Восстановить в `/tmp/restore-test`.
5. Проверить целостность файлов.
