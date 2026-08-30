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
| Target LAN после переноса / Target LAN after the move | `ping 192.168.0.50` | accessible after connecting to router |

### 1.1. Existing data HDD intake

🇷🇺 Если пользователь подключает HDD с уже существующими данными, особенно NTFS-диск
после Windows, сначала выполняется только read-only проверка. Такой диск не
форматируется, не добавляется в `/etc/fstab` и не монтируется сразу в
`/mnt/storage`.

🇬🇧 If the user attaches an HDD that already holds data — especially an NTFS disk
coming from Windows — only a read-only check is performed first. Such a disk is not
formatted, not added to `/etc/fstab`, and not mounted straight into `/mnt/storage`.

| Тест / Test | Команда / Command | Критерий / Criterion |
|---|---|---|
| Services stopped before storage check | `docker ps` + `docker compose ... stop` | Nextcloud/Immich не пишут в `/mnt/storage` / Nextcloud/Immich are not writing to `/mnt/storage` |
| No false `/mnt/storage` mount | `mountpoint /mnt/storage` | понятно, смонтирован ли внешний диск или это каталог на microSD / it is clear whether an external disk is mounted or this is just a directory on the microSD |
| Existing HDD detected | `lsblk -o NAME,TYPE,SIZE,FSTYPE,LABEL,MOUNTPOINT,MODEL,TRAN,RO` | виден ожидаемый USB HDD и раздел / the expected USB HDD and its partition are visible |
| No USB enumeration loop | `journalctl -k -n 120 --no-pager \| grep -i -E "error -71|unable to enumerate"` | пусто / empty |
| Read-only mount | `sudo mount -t ntfs-3g -o ro /dev/sdXN /mnt/hdd-check` | диск смонтирован отдельно от `/mnt/storage` / the disk is mounted separately from `/mnt/storage` |
| Data presence without leaking names | `df -hT /mnt/hdd-check && find /mnt/hdd-check -mindepth 1 -maxdepth 1 | wc -l` | размер корректный, данные видны, имена файлов не публикуются / the size is correct, the data is visible, file names are not published |
| No forced repair | manual check | не использовались `force`, форматирование, repartition, `setup_disk.sh` / no `force`, no formatting, no repartitioning, no `setup_disk.sh` was used |
| Compression feasibility | metadata-only extension/category scan | если данные в основном фото/видео/архивы, lossless-архивирование не считается заменой носителя нужного объёма / if the data is mostly photos/video/archives, lossless archiving does not count as a substitute for a large enough medium |

## 2. Samba/SFTP

| Тест / Test | Критерий / Criterion |
|---|---|
| Windows открывает шару / Windows opens the share | Да / Yes |
| Linux подключается по SFTP / Linux connects over SFTP | Да / Yes |
| Запись тестового файла / Writing a test file | Да / Yes |
| Права доступа корректны / Access rights are correct | Да / Yes |

## 3. Nextcloud

🇷🇺
1. Вход в web-интерфейс.
2. Создание пользователя.
3. Загрузка файла.
4. Подключение Android-клиента.
5. Проверка Contacts/Calendar.
6. Проверка DAVx5.

🇬🇧
1. Log in to the web interface.
2. Create a user.
3. Upload a file.
4. Connect the Android client.
5. Check Contacts/Calendar.
6. Check DAVx5.

## 4. Immich

🇷🇺
1. Вход в web-интерфейс.
2. Подключение Android-клиента.
3. Загрузка 20–50 фото.
4. Загрузка 2–3 видео.
5. Проверка `docker stats`.
6. Проверка работы после перезапуска контейнеров.

🇬🇧
1. Log in to the web interface.
2. Connect the Android client.
3. Upload 20–50 photos.
4. Upload 2–3 videos.
5. Check `docker stats`.
6. Verify it still works after the containers are restarted.

## 5. LLM Gateway

🇷🇺
1. `GET /health`.
2. Тест mock-mode.
3. Тест DeepSeek API без персональных данных.
4. Проверка лимитов.
5. Проверка redaction.

🇬🇧
1. `GET /health`.
2. Mock-mode test.
3. DeepSeek API test with no personal data.
4. Check the limits.
5. Check redaction.

## 6. VPS + Reverse SSH Tunnel

| Тест / Test | Команда / Command | Критерий / Criterion |
|---|---|---|
| Tunnel service active | `systemctl status nas_jetson_nano-tunnel.service` | active (running) |
| Tunnel ports on VPS | `ss -tlnp \| grep -E '18080\|12283\|18090\|10022'` | 4 порта на 127.0.0.1 |
| nginx container | `docker ps --filter name=nas_jetson_nano_nginx` | Up, network_mode host |
| Nextcloud via VPS | `wget -q -O /dev/null -S http://95.163.176.103:8080/` + `/status.php` | root HTTP 302, `/status.php` HTTP 200 |
| Immich via VPS | `wget -q -O /dev/null -S http://95.163.176.103:2283/` | HTTP 200 |
| LLM GW via VPS | `wget -q -O /dev/null -S http://95.163.176.103:8090/health` | HTTP 200 |
| SSH via tunnel | `ssh -p 10022 admin@127.0.0.1` (с VPS / from the VPS) | prompt |
| Tunnel restart | `systemctl restart nas_jetson_nano-tunnel.service` | re-establishes within 30s |
| Reboot autorecovery | `sudo systemctl reboot`, then poll tunnel/storage/HTTP | tunnel returns, `/mnt/storage` is mounted, containers healthy, VPS HTTP 200 |

## 7. Backup/Restore

🇷🇺
1. Запустить `sudo bash scripts/storage/storage_preflight.sh`.
2. Создать тестовый backup.
3. Проверить список snapshots.
4. Восстановить в `/tmp/restore-test`.
5. Проверить целостность файлов.

🇬🇧
1. Run `sudo bash scripts/storage/storage_preflight.sh`.
2. Create a test backup.
3. Check the snapshot list.
4. Restore into `/tmp/restore-test`.
5. Verify file integrity.
