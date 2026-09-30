# OPS-1 — container watchdog deployment evidence / доказательства развёртывания

Date: 2026-09-30. Device timestamps below are UTC. No production container was
stopped; both probes used an already-local image and were removed after the test.

## Result / Результат

OPS-1 is deployed on the Jetson and meets its acceptance criteria. The systemd
timer is enabled and active, an eligible stopped `homecloud_*` probe recovered
in 123 seconds, the per-container maintenance marker suppressed recovery, and
the watchdog's Telegram request was accepted.

OPS-1 развёрнут на Jetson и соответствует критериям приёмки. systemd-таймер
включён и активен, подходящий остановленный probe `homecloud_*` восстановился
за 123 секунды, контейнерный maintenance-маркер запретил восстановление, а
Telegram-запрос watchdog был принят.

## Traceable observations / Наблюдения

| UTC | Evidence | Classification |
|---|---|---|
| 2026-09-30 14:24–14:27 | `nas_jetson_nano-container-watchdog.timer` reported `enabled` and `active`; successful service invocations were observed | observed |
| 2026-09-30 14:30:39 | With `/etc/nas-watchdog.pause.d/homecloud_watchdog_probe` present, a manual service invocation logged `обслуживание ... — пропускаю`; the probe remained `exited` | observed |
| 2026-09-30 14:30:39–14:32:42 | After removing the marker, the scheduled timer logged `docker start OK`; measured recovery was 123 seconds, below the 3-minute acceptance bound | observed |
| 2026-09-30 14:33:22 | `systemctl list-timers` showed the next invocation at 14:34:39, two minutes after the previous trigger | observed |
| 2026-09-30 14:49:14–14:49:16 | On deployed revision `cea5a1b`, a disposable alert probe was started and the journal logged both `docker start OK` and `алерт доставлен` | observed |
| 2026-09-30 14:49:49 | Both disposable containers and both temporary pause markers were absent; the next timer invocation remained scheduled | observed |

The `алерт доставлен` line means `send_with_retries()` received a successful
Telegram API response. Revision `21d4eb6` fixed the previous false-silence case
where a returned `(False, error)` was ignored; revision `cea5a1b` added an
explicit success journal entry. Secrets and Telegram response bodies were not
logged.

## Verification / Проверка

- Full repository gate: passed.
- Regression tests: 18 passed.
- Service suites: LLM gateway 44 passed; NAS API 210 passed; watchdog 44 passed;
  backup API 24 passed and 1 skipped; STT 17 passed.
- OPS-1 focused tests: 8 passed, including delivery failure and success logging.
- Non-blocking local warnings: ShellCheck and Docker were unavailable; the known
  non-Immich `:latest` image debt remains tracked as DEP-2.

## Operating contract / Эксплуатационный контракт

- Scope: only `homecloud_*` containers with Docker restart policy `always`.
- Stopped/created/dead: `docker start`; running/unhealthy: `docker restart`.
- Manual maintenance: `/etc/nas-watchdog.pause`, a per-container file under
  `/etc/nas-watchdog.pause.d/`, or label `nas.watchdog.maintenance=true`.
- Rollback: `sudo systemctl disable --now nas_jetson_nano-container-watchdog.timer`.
  This stops future runs; it does not remove containers, data, units, or state.
