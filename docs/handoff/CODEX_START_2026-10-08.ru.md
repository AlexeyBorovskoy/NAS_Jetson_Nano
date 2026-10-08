# Старт Codex в NAS_Jetson_Nano — передача от 2026-10-08

Английская версия: [CODEX_START_2026-10-08.md](CODEX_START_2026-10-08.md). Документ заменяет устаревший
`docs/prompts/CODEX_BOOTSTRAP_PROMPT.md` (30.08) для текущего старта. Секретов здесь нет — только пути.

## 1. Прочитать до первого действия (по порядку)

1. `AGENTS.md` — общие правила агентов (версия из рабочей копии, с §9 «Артефакты» и §10 «Чистота»).
2. [`docs/plans/CHECKPOINT_2026-10-08.ru.md`](../plans/CHECKPOINT_2026-10-08.ru.md) — где проект сейчас.
3. `CLAUDE.md` — операционное состояние, таблица компонентов, «Грабли» и «Жёсткие правила» №1–18.
   Написан для Claude, но это **канон знаний проекта** и для Codex: там записаны найденные дефекты и запреты.
4. `docs/32_QUALITY_GATE.md` — ворота качества; `docs/AGENT_REPOSITORY_HYGIENE.md` — чистота (в индексе).
5. При делегировании механики — `docs/handoff/DEEPSEEK_WORKER.md` (исполнитель DeepSeek, `ds-worker`).

Справочно, только чтение: память Claude по проекту лежит вне репозитория —
`C:\Users\Alexey\.claude\projects\e--Linux-mint-virtual-VM-shared-NAS-Jetson-Nano\memory\` (`MEMORY.md` — индекс).

## 2. Жёсткие правила, которые нельзя нарушить ни разу

- **Язык с владельцем — русский.**
- **VPN на VPS (правило №13):** контейнеры `amnezia-*` не трогать и не перезапускать; до и после любой
  работы на VPS — контейнеры не перезапускались, наружу только 22/443/40568 udp, число пиров не уменьшилось.
- **Любая команда на VPS — под ограничением памяти** (владелец, 08.10):
  `ssh … root@VPS 'systemd-run --quiet --scope -p MemoryMax=256M -p MemorySwapMax=0 bash -s' < script.sh`.
  Журналы — потоком и с `--since`, никогда в переменную оболочки: 04.10 так задушили VPN.
- **Выкат — только по слову владельца «деплой».** Монитор VPS/VPN (задача 8) ещё и требует отдельного
  явного разрешения на read-only чтение счётчиков VPN.
- Секреты не печатать и не коммитить; называть файл и строку, не значение. Перед пушем —
  `bash scripts/security/check_no_secrets.sh`.
- Разрушительное (`rm -rf`, форматирование, `DROP`, удаление чужих файлов и worktree) — только с
  подтверждения владельца. `/mnt/hdd2tb` (NTFS, 1.4 ТБ архива) не форматировать и не обходить параллельно.
- Живой Jetson работает на **старой раскладке**: репозиторий `~/nasa`, контейнеры `homecloud_*`, юниты
  `nasa-*`; `git pull` на устройстве — только по инструкции деплоя.
- Документация — парами `X.md` (EN) + `X.ru.md` (RU); новый документ без пары не готов (правило №15).

## 3. Окружение рабочей станции

| Что | Где / как |
|---|---|
| Репозиторий | `E:\Linux mint\virtual_VM\shared\NAS_Jetson_Nano`, ветка `main`; remotes `origin` (GitHub) и `gitverse` (`NAS_HOME`) |
| Python для тестов | `.venv\Scripts\python.exe`; в Git Bash — `export PATH="/e/Linux mint/virtual_VM/shared/NAS_Jetson_Nano/.venv/Scripts:$PATH"` (форма `E:/` ломает PATH) |
| Ворота | `bash scripts/quality/preflight.sh --quick`; хук `.githooks/pre-commit` включён (`core.hooksPath`) |
| Публикация | `git push origin main`; GitVerse — `bash scripts/sber/gitverse_mirror_push.sh` (пушит `main` и `master`) |
| GitHub CLI | `C:\tools\gh\bin\gh.exe`, вход `AlexeyBorovskoy` через keyring. Токен почти администраторский — никому не передавать |
| DeepSeek | `ds-worker new/run/status/review`, конфиг `ds_worker.toml`, история `ds_board/` (вне git) |
| Доска проектов | `python E:\agent_coordination\coord.py list --agent nas --open`; метка проекта — `nas` |
| Артефакты | только внутри проекта: `.agent-work/{worktrees,archives,tmp}/`, `artifacts/` (AGENTS.md §9) |

## 4. Доступы (пути, без значений)

| Куда | Как |
|---|---|
| VPS `95.163.176.103` | `ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103` или алиас `vps-nas` |
| VPS, если адрес заблокирован | `-o HostKeyAlias=95.163.176.103 root@193.8.215.130` или `vps-nas-alt` (блок переключается между адресами) |
| Jetson из дома | `ssh admin@192.168.0.50` (правило №17) |
| Jetson снаружи | алиас `jetson-via-vps` / `jetson-via-vps-alt` (обратный туннель на VPS `:10022`) |
| sudo на Jetson | пароль — `NEXTCLOUD_ADMIN_PASSWORD` в `~/nasa/config/.env` **на устройстве**; не печатать |

Алиасы описаны в `~/.ssh/config` станции и в `docs/plans/VOSTRO_BASTION_HOME_ACCESS.md`.

## 5. Первые команды и ожидаемый результат

```bash
git status --short            # 9 файлов работы по чистоте в индексе (см. точку §4) — не терять
git config --get core.bare    # false; true = повторился дефект хука, вернуть: git config core.bare false
git log --oneline -3          # последние коммиты интеграции
git worktree list             # ветка deepseek/nas-vpnmon-deploy-prep-20261007 и старые deepseek/* — не удалять без проверки
python E:\agent_coordination\coord.py list --agent nas --open
```

## 6. Очередь работ

1. **Чистота репозитория:** интегрирована коммитом `d180977`. Синтетические тесты
   очищают `GIT_*`; обычный запуск (18 тестов), изолированный настоящий Git-хук
   и хук основного репозитория прошли без обхода.
2. **Подготовка монитора:** ветка `deepseek/nas-vpnmon-deploy-prep-20261007` интегрирована.
   Сохранены hygiene-памятка и правило памяти VPS; инструкции SSH используют ограничение
   памяти. Это интеграция документации, не деплой.
3. Монитор VPS/VPN, задача 8 — **ждёт владельца**, сам не начинать.
4. Клиентские сбои VPN — профиль установлен; нужна попытка телефона через Deco с наблюдением на VPS.
5. Аудит, стадии 19–21 — `docs/audit/2026-10-02_code_audit/PLAN.ru.md`.

## 7. Промпт для первого запуска Codex

```text
Ты Codex в проекте NAS_Jetson_Nano. Отвечай владельцу по-русски. Сначала прочитай
docs/handoff/CODEX_START_2026-10-08.ru.md и всё из его раздела 1, затем выполни команды
раздела 5 и доложи состояние: что в индексе main, чем отличается ветка
deepseek/nas-vpnmon-deploy-prep-20261007, есть ли открытые запросы на доске для nas.
Перед изменениями проверь текущую очередь; деплой требует отдельного разрешения.
На VPS — только под systemd-run с MemoryMax=256M и MemorySwapMax=0; Amnezia не трогать.
```
