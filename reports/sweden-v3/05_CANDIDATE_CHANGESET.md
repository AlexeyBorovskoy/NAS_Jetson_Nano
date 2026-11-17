# 05_CANDIDATE_CHANGESET — Серверный changeset S3 (НЕ ПРИМЕНЁН)

## 1. Область изменений (`/etc/sing-box/config.json`)
- **Изменяются исключительно** массивы `users` в двух существующих inbound:
  - `vless-reality-in` (`7` старых v1 + `12` новых v3 = `19` пользователей, все UUID уникальны).
  - `hy2-in` (`7` старых v1 + `12` новых v3 = `19` пользователей, все пароли уникальны).
- **Не изменяются:** IP (`45.140.13.178`), порты (`443/tcp`, `443/udp`), `reality.private_key`, `reality.short_id`, `tls.certificate_path`, `hy2.masquerade`, UFW, SSH, DNS.

## 2. Diff-схема (без секретов)
```diff
 "inbounds": [
   {
     "tag": "vless-reality-in",
     "users": [
       ... 7 existing v1 users (UNCHANGED) ...,
+      {"name": "alexey-windows-v3", "uuid": "<CSPRNG_UUID_V3>", "flow": "xtls-rprx-vision"},
+      ... (+6 rotated existing + 5 new-01..new-05 = 12 entries)
     ]
   },
   {
     "tag": "hy2-in",
     "users": [
       ... 7 existing v1 users (UNCHANGED) ...,
+      {"name": "alexey-windows-v3", "password": "<CSPRNG_HY2_V3>"},
+      ... (+6 rotated existing + 5 new-01..new-05 = 12 entries)
     ]
   }
 ]
```

## 3. Проверка в staging
- `python tools\sweden_vpn\check_server_staging.py` → `STAGING_VLESS_TOTAL= 19`, `STAGING_HY2_TOTAL= 19`, `SING_BOX_STAGING_CHECK=PASS`.
- **Перезапуск:** для загрузки новых `users` потребуется `systemctl reload sing-box` (`ExecReload=/bin/kill -HUP $MAINPID`, проверено in-place с кратковременным переподключением активных потоков) или `systemctl restart sing-box`.
