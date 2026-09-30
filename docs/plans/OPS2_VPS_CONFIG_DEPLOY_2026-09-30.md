# OPS-2 — configured VPS host deployment evidence / доказательства развёртывания

Date: 2026-09-30. Device timestamps are recorded in UTC unless marked MSK.
The configured VPS address and all credentials are intentionally omitted.

## Result / Результат

OPS-2 is complete. Both operational paths now obtain `VPS_HOST` from the
root-owned `/opt/nasa/config/.env` instead of embedding an address in executable
code. The Jetson daily-report systemd path delivered a real Telegram report,
and the Vostro offsite systemd path completed a real restic backup.

OPS-2 завершён. Оба эксплуатационных пути получают `VPS_HOST` из root-only
`/opt/nasa/config/.env`, а не из адреса внутри исполняемого кода. systemd-путь
ежедневного отчёта Jetson доставил реальный отчёт в Telegram, а systemd-путь
offsite на Vostro успешно выполнил реальный restic-бэкап.

## Jetson observations / Наблюдения Jetson

- Deployed repository revision: `bd297d8`.
- Installer: `scripts/monitoring/install_daily_report.sh`; it resolved the live
  legacy layout to `/usr/local/sbin/nasa-{daily-report,send-report-telegram}.sh`
  and `nasa-daily-report-telegram.{service,timer}`.
- Installed source hashes match the repository:
  - sender: `1c089d948214b24caa3b0186f0ff2df07b0eaec132c1f6522cf5f41fec7c6e80`;
  - report: `39f90ecf059fab400689008cbd4537a46c464871bb0e18b0ca0418b2960044d1`.
- Both deployed scripts were checked for the former/current literal VPS IPv4:
  none found; both contain the fail-closed shared-config loader.
- Timer: `enabled` and `active`; next calendar run remained scheduled.
- Direct acceptance run returned `OK, message_id=348`.
- A subsequent systemd service run at 2026-09-30 15:11 UTC returned
  `Result=success`, `ExecMainStatus=0`, and logged `OK, message_id=349`.

## Vostro observations / Наблюдения Vostro

- `/usr/local/sbin/nas-offsite-backup.sh` was replaced with the repository
  version; SHA-256:
  `966ae3ce398f782503c2f4793bd3b2f835d6ca766fed30dce29f290c8d479a80`.
- No literal VPS address was found in the deployed script; its shared-config
  loader and fail-closed validation are present.
- `/opt/nasa/config/.env` exists as `root:root` mode `0600` and contains a
  non-empty `VPS_HOST` entry. Its value is not recorded here.
- `nas-offsite-backup.timer` is `enabled` and `active`.
- A live `nas-offsite-backup.service` run completed at
  2026-09-30 18:21:16 MSK with `Result=success`, `ExecMainStatus=0`. It completed
  the pull, restic backup, retention and prune sequence.

## Verification / Проверка

- `tests/unit/test_vps_host_config.py`: 5 tests passed.
- Full repository gate: passed — regression 18; LLM gateway 44; NAS API 210;
  watchdog 44; backup API 24 passed/1 skipped; STT 17.
- Non-blocking local warnings remain unchanged: ShellCheck and Docker were not
  available, and three non-Immich `:latest` tags remain tracked as DEP-2.

## Rollback / Откат

The previous executables may be restored from the host's normal configuration
backup, but the preferred rollback is to redeploy the prior git revision and
keep `/opt/nasa/config/.env`; returning to an embedded IP would reintroduce
OPS-2. Timers and VPN configuration were not changed beyond reloading the
daily-report unit installed from the repository template.
