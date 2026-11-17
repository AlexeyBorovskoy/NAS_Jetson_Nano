# 10_EXECUTIVE_DECISION — Точка согласования S3 (Production Package)

## Конкретный Change Request (ожидает одобрения пользователя)
- **Пакет:** **S3 — Активация 12 индивидуальных учётных данных v3 на VPS Sweden (`45.140.13.178`) при сохранении 7 старых v1.**
- **Затрагиваемый файл:** `/etc/sing-box/config.json` (только массивы `users` в `vless-reality-in` и `hy2-in`: `7 -> 19`).
- **Не затрагиваются:** порты, IP, TLS-ключи, REALITY private/short_id, Nginx `:8443`, SSH, UFW, DNS, `v1` профили.
- **Prechecks:** backup в `/root/backup-v3-<UTC>/`, `sing-box check` (`PASS` в staging).
- **Воздействие:** `systemctl reload sing-box` (`SIGHUP` на том же `MainPID` с кратковременным переподключением активных потоков).
- **Postchecks:** внешние раздельные пробы старых и новых HY2/REALITY → `45.140.13.178`, `vpn-monitor` `10/10` OK.
- **Откат:** восстановление `config.json.before` + `sing-box check` + `systemctl reload sing-box`.
