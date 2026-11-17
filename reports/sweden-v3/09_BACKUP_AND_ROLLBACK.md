# 09_BACKUP_AND_ROLLBACK — Резервное копирование и откат

- **VPS бэкапы:** `/root/backup-mod-20261116T130241Z`, `/root/backup-tls-20261116T083718Z`, `/root/backup-ssh-20261116T134205Z`, `/root/backup-imp02-03-20261116`, а перед S3 создаётся `/root/backup-v3-<UTC>/config.json.before`.
- **Изолированная проверка восстановления:** `check_server_staging.py` проверяет целевой JSON через `sing-box check` до касания боевого файла.
- **Откат S3:**
  ```bash
  cp -a /root/backup-v3-<UTC>/config.json.before /etc/sing-box/config.json
  sing-box check -c /etc/sing-box/config.json
  systemctl reload sing-box
  ```
- **Откат клиентов:** переключение обратно на v1/v2 профиль в `FlClash` (старые профили не удаляются).
