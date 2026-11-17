# 08_MIGRATION_MATRIX — Поэтапный план миграции и отзыва (S5/S6)

- **Серверная активация (S3):** `PASSED` (`2026-11-17T09:40:47Z`, `19` пользователей в `vless-reality-in` и `hy2-in`, `MainPID=34877`, backup `/root/backup-v3-20261117T094047Z/config.json.before`).
- **Волна 1 (Пилот S4):**
  - `olga-android` / `hagircbmsszlx4in` (`olga-android-v3.yaml`): **`LIVE_TESTED`** в `CORP_WIFI_192_168_75`: оба транспорта (`SE-PRIMARY` `396.8ms`, `SE-HY2` `313.6ms`), `RECONNECT 10/10` (`med=1489.2ms`, `max=1771.6ms`), `AUTO_FAILOVER_TESTED` (`SE-PRIMARY -> SE-HY2` за `504.8ms`), `FAIL_CLOSED_LEAK_TEST` (`api.ipify.org rc=35 HTTP=000`, `ya.ru DIRECT HTTP=302`). Домашний Wi-Fi и LTE для v3 — `PENDING_DEVICE`.
  - `alexey-windows` (`alexey-windows-v3.yaml`): `SERVER_ENABLED` (ожидает пилота при отключённом `AmneziaVPN`).
- **Волна 2 (Существующие):** `ivan-windows`, `ivan-android`, `ulyana-android-1`, `ulyana-android-2` → статус `SERVER_ENABLED` (выдача владельцам после Wave 1).
- **Волна 3 (+5 новых):** `new-01`, `new-02`, `new-03`, `new-04`, `new-05` → статус `SERVER_ENABLED` (выдача по мере назначения устройств).
- **Отзыв v1 (S6):** только после `LIVE_TESTED` всех зависимых устройств каждого старого секрета (особенно `hagircbmsszlx4in` с 4 файлами `FAMILY-SE-01..04`).
