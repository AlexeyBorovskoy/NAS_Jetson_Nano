# Участие в проекте / Contributing

## Русская версия

Вклад приветствуется, но проект связан с домашней инфраструктурой и персональными данными, поэтому изменения должны быть маленькими, проверяемыми и безопасными.

### Правила

1. Не коммитить секреты.
2. Не добавлять персональные данные в примеры, тесты, логи и документацию.
3. Предпочитать маленькие pull request.
4. Добавлять документацию к каждому операционному скрипту.
5. Сохранять Stage 1 безопасным: по умолчанию не открывать сервисы в публичный интернет.
6. Не добавлять локальную LLM на Jetson Nano в Stage 1.
7. Для рискованных изменений описывать rollback.

### Храповик метрик

`scripts/quality/code_metrics.py --check docs/audit/2026-10-02_code_audit/baseline.json`
в `preflight.sh` (раздел 10) и в CI не даёт структурному рефакторингу откатиться
незамеченным: число модулей уровня `fail` не растёт, уже нездоровый модуль не
ухудшает сложность/вложенность/перехваты, новая функция обязана быть ≤ CC 10 и
≤ 40 строк. После улучшения обнови baseline **отдельным коммитом**:
`python scripts/quality/code_metrics.py --update docs/audit/2026-10-02_code_audit/baseline.json`.
Осознанное исключение — `NAS_METRICS_ALLOW="файл=причина"` в окружении, причина
обязана попасть и в сообщение коммита, а не остаться только в терминале.
Предохранители: новая команда бота — новая функция (не ветка в `_dispatch`);
«где лежит `.env`» — только через `scripts/lib/layout.sh` / `nas_layout.py`,
новую копию этой логики не писать.

### Хорошие первые задачи

- Улучшить hardware audit script.
- Добавить заметки для Raspberry Pi 4/5.
- Добавить скриншоты безопасной тестовой установки.
- Добавить инструкцию по Xiaomi/HyperOS background sync.
- Добавить CI-проверку Docker Compose и shell-скриптов.
- Синхронизировать устаревшие архитектурные документы с текущим деревом.

## English Version

Contributions are welcome, but this project is related to home infrastructure and personal data, so changes should be small, reviewable, and safe.

### Rules

1. Do not commit secrets.
2. Do not include personal data in examples, tests, logs, or documentation.
3. Prefer small pull requests.
4. Add documentation for every operational script.
5. Keep Stage 1 safe: no public port exposure by default.
6. Do not add local LLM inference on Jetson Nano in Stage 1.
7. For risky changes, document rollback.

### Metrics ratchet

`scripts/quality/code_metrics.py --check docs/audit/2026-10-02_code_audit/baseline.json`
in `preflight.sh` (section 10) and in CI stops a structural refactor from
drifting back unnoticed: the count of `fail`-level modules must not grow, an
already-unhealthy module must not get worse on complexity/nesting/catches,
and a brand-new function must be ≤ CC 10 and ≤ 40 lines. After a real
improvement, update the baseline in its **own commit**:
`python scripts/quality/code_metrics.py --update docs/audit/2026-10-02_code_audit/baseline.json`.
A deliberate exception is `NAS_METRICS_ALLOW="file=reason"` in the
environment, with the reason also in the commit message, not left only in a
terminal. Guardrails: a new bot command is a new function (not another
branch in `_dispatch`); "where does `.env` live" has one answer —
`scripts/lib/layout.sh` / `nas_layout.py` — do not write a second copy of it.

### Good First Issues

- Improve the hardware audit script.
- Add Raspberry Pi 4/5 notes.
- Add screenshots from a safe test installation.
- Add a Xiaomi/HyperOS background sync guide.
- Add CI validation for Docker Compose and shell scripts.
- Synchronize outdated architecture documents with the current tree.
