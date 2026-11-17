# 00_BASELINE — Исходное состояние (G0)

- **Дата (UTC):** `2026-11-17T07:31:51Z`
- **VPS Sweden (`45.140.13.178`, `vpn.privet.dynv6.net`):**
  - `sing-box 1.14.4` (`MainPID=34877`, `vless-reality-in` TCP/443 + `hy2-in` UDP/443, `7` пользователей).
  - `nginx` TCP/8443 (`HTTP 200`), `vpn-monitor` `127.0.0.1:8088` (`10/10` OK), `certbot.timer` (`active`).
  - `IMP-01` (SSH hardening), `IMP-02` (`/swapfile1G`, `vm.swappiness=10`), `IMP-03` (`rmem_max=wmem_max=7500000`) — подтверждены на сервере.
  - IPv6 egress на VPS работает (`HTTP=200`), но AAAA для `vpn.privet.dynv6.net` отсутствует.
- **Локальный клиент Windows (`alexey-windows`):**
  - Установлен `FlClash 0.9.3+2026110401` (`C:\Program Files\FlClash\FlClash.exe`) с ядром Mihomo (`FlClashCore.exe`).
  - Активный конкурирующий VPN: `AmneziaVPN` (`tun2`, egress `89.124.65.229`).
  - Эффективный `C:\Users\Alexey\AppData\Roaming\com.follow\clash\config.yaml` отличается от импортированного профиля `380671665593389056.yaml` (`tun.enable: false`, `unified-delay: false`, `tcp-concurrent: false`, `sniffer.enable: false`).
- **Архив v1 YAML (`C:\Users\Alexey\.ssh\new-vps-se\`):** 10 файлов, все провалидированы `mihomo.exe -t`, сохранены без изменений.
