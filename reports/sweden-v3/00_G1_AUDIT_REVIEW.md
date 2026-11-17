# 00_G1_AUDIT_REVIEW — Разбор фактов и границ доказательности G1 Android

- **Источник:** `artifacts/G1_Android_Report_ANDROID_G1_20261117T090742Z.zip`, Git `011f37f`.
- **Устройство и приложение:** Android 16 (`25100RA69G`), `com.follow.clash` `FlClash 0.9.3` (`2026112401`), активный профиль `olga-android-v2.yaml` рядом с v1 `FAMILY-SE-Olga-Android.yaml`. (Также установлены `com.fclash.app` и `org.amnezia.vpn`).

## Что доказано (`VERIFIED` / `MEASURED`)
- Выбор группы в UI: `PROXY → AUTO → SE-PRIMARY` (`Fallback`).
- Оба транспорта (`SE-PRIMARY` REALITY TCP/443 и `SE-HY2` UDP/443) отработали в мобильной сети МТС LTE (`468ms` / `375ms`) и в корпоративном Wi-Fi (`417.9ms` / `399.8ms`) через `adb_forwarded_socks5` (`com.follow.clash:7890`) с egress `45.140.13.178`.
- Переход LTE → корп. Wi-Fi прошёл без разрыва, `ya.ru` DIRECT → `HTTP 302` (`147.9ms`).
- **Разбор задержки `:8443` (`2436.3ms` в G1):** дополнительная декомпозиция `curl.exe -w` показала, что при холодном DNS на Windows (`2.609s`) `dns=2.609s`, а `tcp+tls+ttfb=0.438s`; через телефон с тёплым кэшем `PHONE_8443: dns=0.000s, tcp=0.016s, tls=0.437s, ttfb=0.484s`. Причина задержки — DNS-ожидание, а не Nginx на VPS.

## Пробелы и ограничения G1
- `startup_to_success_ms` не измерен (`NO_START_EVENT`, все пробы — `WARM_PROBE`).
- `AUTO_FAILOVER_TESTED = PENDING_FAILOVER_TEST`, `FAIL_CLOSED_LEAK_TEST = PENDING_LEAK_TEST`, домашний Wi-Fi = `PENDING_DEVICE`.
- Все пробы шли через `adb_forwarded_socks5`, а не напрямую через пользовательские Android-приложения поверх `VpnService` (`bypassable=true`).
- В ZIP-архиве отсутствовали текстовые логи `session_lte_probes.txt` / `session_wifi_probes.txt` (они остались только в терминальном транскрипте предыдущей сессии).
- Ускорение Windows-стенда (`-34.9%`) на Android не переносится.
