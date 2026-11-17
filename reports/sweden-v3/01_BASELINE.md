# 01_BASELINE — Фактический baseline VPS Sweden и проекта (G0)

- **Дата (UTC):** `2026-11-17T09:30:18Z`
- **VPS:** `45.140.13.178` (`vpn.privet.dynv6.net`, SSH `aeza-sweden`), Ubuntu 24.04 LTS, `kvm`.
- **Сервисы (`systemctl --failed`: 0):**
  - `sing-box 1.14.4`: `active`, `MainPID=34877`, `0.0.0.0:443` TCP (`vless-reality-in`) + UDP (`hy2-in`), `7` уникальных пользователей в каждом inbound.
  - `nginx`: `active`, `0.0.0.0:8443` и `[::]:8443` (`HTTP 200`).
  - `vpn-monitor`: `active`, `127.0.0.1:8088` (`10/10` OK).
  - `certbot.timer`: `active`, сертификат `vpn.privet.dynv6.net` валиден 88 дней (до `2027-02-14`).
- **Подтверждённые IMP-01/02/03 (не переустанавливаются):**
  - SSH: `PermitRootLogin without-password`, `PasswordAuthentication no`, `KbdInteractiveAuthentication no`, `PubkeyAuthentication yes`.
  - Swap: `/swapfile1G` (`1024M`), `vm.swappiness = 10`.
  - UDP: `net.core.rmem_max = 7500000`, `net.core.wmem_max = 7500000`, `UdpInErrors = 0`, `UdpRcvbufErrors = 0`.
- **Обновления ОС (`apt-get -s upgrade`):** `313` пакетов к обновлению (из них `390` строк security/repo check — отдельный security-only план без смешивания с ротацией).
- **Резервные копии на VPS:** `/root/backup-mod-20261116T130241Z`, `/root/backup-tls-20261116T083718Z`, `/root/backup-ssh-20261116T134205Z`, `/root/backup-imp02-03-20261116`, `/root/vpn-registry`.
