# Нагрузочные тесты / Load Tests: NAS_Jetson_Nano

**Version:** 1.0  
**Date:** 2026-06-27

---

## Область охвата и ограничения / Scope and Constraints

🇷🇺 Это только дымовой нагрузочный тест — НЕ тест на выносливость (stress) и НЕ длительный тест (soak).

**Ограничения:**
- Jetson Nano 4GB: ОЗУ общая для CPU/GPU. OOM убьёт сервисы.
- USB SSD (RTL9210B-CG): агрессивный ввод-вывод под нагрузкой может вызвать ошибку -71
- ML-обработка отключена (IMMICH_DISABLE_MACHINE_LEARNING=true)
- Конфигурация теста: максимум 5 VU / 2 минуты

**НЕ ЗАПУСКАТЬ** нагрузочные тесты с > 10 VU на Jetson Nano без мониторинга ОЗУ.

🇬🇧 This is a smoke load test only -- NOT a stress or soak test.

**Constraints:**
- Jetson Nano 4GB: RAM is shared CPU/GPU. OOM will kill services.
- USB SSD (RTL9210B-CG): aggressive I/O under load may trigger error -71
- No ML processing (IMMICH_DISABLE_MACHINE_LEARNING=true)
- Test configuration: max 5 VU / 2 minutes

**DO NOT** run load tests with > 10 VU on Jetson Nano without monitoring RAM.

---

## Тестовый скрипт / Test Script

### nextcloud-smoke.js (k6)

```bash
# Prerequisites
# Install k6: https://k6.io/docs/getting-started/installation/

# Run smoke test
NEXTCLOUD_URL=http://192.168.0.50:8080 k6 run tests/load/nextcloud-smoke.js

# Run against VPS
NEXTCLOUD_URL=http://95.163.176.103:8080 k6 run tests/load/nextcloud-smoke.js
```

---

## Критерии приёмки / Acceptance Criteria

| Метрика / Metric | Цель / Target | Блокирует? / Blocking? |
|---|---|---|
| Virtual Users | 5 | -- |
| Duration | 2 minutes | -- |
| HTTP error rate | < 1% | YES |
| p50 response time | < 500ms | NO (warn) |
| p95 response time | < 2000ms | YES |
| p99 response time | < 5000ms | NO (warn) |

---

## Мониторинг ресурсов во время нагрузочного теста / Resource Monitoring During Load Test

🇷🇺 Открыть второй терминал и вести наблюдение.

🇬🇧 Open a second terminal and monitor:

```bash
# Docker stats (live)
docker stats --no-stream

# Memory pressure
free -h

# CPU load
uptime

# USB SSD state
cat /proc/sys/vm/dirty_ratio
dmesg | grep -E "error|sda" | tail -5
```

🇷🇺 Немедленно остановить тест, если:
- `free -h` показывает доступную ОЗУ < 200 МБ
- любой контейнер перезапустился
- dmesg показывает «error -71» или «I/O error»

🇬🇧 Stop the test immediately if:
- `free -h` shows available RAM < 200MB
- Any container restarts
- dmesg shows "error -71" or "I/O error"

---

## Ожидаемые результаты (Jetson Nano, LAN) / Expected Results (Jetson Nano LAN)

| Сценарий / Scenario | Ожидаемый p95 / Expected p95 | Заметки / Notes |
|---|---|---|
| Nextcloud /status.php (5 VU) | < 200ms | Static endpoint, cached |
| Nextcloud / (5 VU) | < 1000ms | Main page, heavier |
| Immich /api/server/ping (5 VU) | < 500ms | API ping |

---

## Известные ограничения / Known Limitations

🇷🇺

- Jetson Nano — НЕ промышленное железо. Одноплатный ARM-компьютер с 4 ГБ общей ОЗУ.
- Реальная производительность просядет при одновременной фотосинхронизации + запросах к БД + ML (отключён).
- Не экстраполировать эти результаты на сценарии с несколькими пользователями.
- Пропускная способность USB SSD общая для всего ввода-вывода; нагрузочный тест + бэкап = повышенный риск.

🇬🇧

- Jetson Nano is NOT production hardware. Single-board ARM compute with 4GB shared RAM.
- Real-world performance will degrade with concurrent photo sync + DB queries + ML (disabled).
- Do not extrapolate these results to multi-user scenarios.
- USB SSD bandwidth is shared across all I/O; load test + backup = increased risk.
