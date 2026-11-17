# 08_ROLLBACK — Процедура отката Sweden VPN v2

## 1. Откат на клиенте (Windows / Android `FlClash`)
1. Открыть `FlClash` → **Profiles**.
2. Выбрать исходный профиль v1 (`380671665593389056` / `FAMILY-SE-*-v1.yaml`), не удаляя его заранее.
3. Переподключить VPN и проверить egress IP (`45.140.13.178`).
4. При необходимости на Windows снова включить `AmneziaVPN`.

## 2. Откат в проекте
- Вся разработка v2 изолирована в `tools/sweden_vpn/`, `tests/sweden_vpn/`, `docs/sweden_vpn_v2/`, `releases/sweden-v2/` и `.agent-work/private-releases/sweden-v2/`.
- Исходные v1 YAML в `C:\Users\Alexey\.ssh\new-vps-se\` и сервер `/etc/sing-box/config.json` не изменялись.

## 3. Проверка после отката
- E2E: `curl.exe --socks5-hostname 127.0.0.1:7890 https://api.ipify.org` (или через TUN) → `45.140.13.178`.
- SSH: `ssh -o BatchMode=yes aeza-sweden "systemctl is-active sing-box"`.
