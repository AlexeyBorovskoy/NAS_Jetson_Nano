# 06_SERVER_REGRESSION_GATE — Pre/Post Checks и Go/No-Go для S3

1. **Pre-checks:**
   - Резервная копия `/etc/sing-box/config.json` в `/root/backup-v3-<UTC>/config.json.before` (`chmod 600`).
   - Проверка уникальности всех `19` UUID и `19` паролей.
   - `sing-box check -c /etc/sing-box/config.json` перед `reload`/`restart`.
2. **Post-checks:**
   - `systemctl is-active sing-box` + `ss -tulpen | grep :443` (TCP и UDP).
   - `vpn-monitor` `127.0.0.1:8088` (`10/10` OK).
   - Внешние раздельные пробы: старый HY2, старый REALITY, новый HY2 (`v3`), новый REALITY (`v3`) → egress `45.140.13.178`.
3. **Rollback:** `cp -a /root/backup-v3-<UTC>/config.json.before /etc/sing-box/config.json && sing-box check -c /etc/sing-box/config.json && systemctl reload sing-box` (или `restart`).
