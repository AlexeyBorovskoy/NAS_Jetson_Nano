# 05_CLIENT_MATRIX & MIGRATION_REGISTER — Реестр устройств Sweden VPN v2

- **Manifest:** [manifest.json](file:///e:/Linux%20mint/virtual_VM/shared/NAS_Jetson_Nano/releases/sweden-v2/manifest.json)
- **Приватные профили (вне Git):** `.agent-work/private-releases/sweden-v2/<device_id>/<device_id>-v2.yaml`

| Device ID | Владелец | ОС / Клиент | Пилот | Статус v1 | Статус v2 |
|---|---|---|---|---|---|
| `alexey-windows` | Alexey | Windows / `FlClash 0.9.3+2026110401` | Да (G1) | Active (rollback) | `generated` (ожидает отключения `AmneziaVPN` для живого теста) |
| `hagircbmsszlx4in` (`olga-android-v2`) | Test / Olga | Android 16 (`25100RA69G`) / `FlClash 0.9.3` | Да (G1) | Active (`FAMILY-SE-Olga-Android.yaml` сохранён) | `live-tested` в `android_mts_lte` (`AUTO->SE-PRIMARY` `0.468s`, `SE-HY2` `0.375s`) и `corp_wifi` (`192.168.75.86`: `AUTO->SE-PRIMARY` `462.5–507.9ms`, `SE-PRIMARY` `417.9ms`, `SE-HY2` `399.8ms`) → `45.140.13.178`; домашний Wi-Fi — `PENDING_DEVICE` |
| `ivan-windows` | Ivan | Windows / `FlClash` | Нет (G2) | Active (rollback) | `generated` / `PENDING_DEVICE` |
| `ivan-android` | Ivan | Android / `FlClash` | Нет (G2) | Active (rollback) | `generated` / `PENDING_DEVICE` |
| `olga-android` | Olga | Android / `FlClash` | Нет (G2) | Active (rollback) | `generated` / `PENDING_DEVICE` |
| `ulyana-android-1` | Ulyana | Android / `FlClash` | Нет (G2) | Active (rollback) | `generated` / `PENDING_DEVICE` |
| `ulyana-android-2` | Ulyana | Android / `FlClash` | Нет (G2) | Active (rollback) | `generated` / `PENDING_DEVICE` |
