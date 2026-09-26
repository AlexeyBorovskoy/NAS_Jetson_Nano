# ADR-0012: DeepSeek worker — cheap executor under a Claude lead
# ADR-0012: исполнитель DeepSeek — дешёвый исполнитель под ведущим Claude

## Status / Статус

🇬🇧 **Accepted** (2026-09-26) — owner's policy of 2026-09-25, adopted in full; core added as a
submodule, trial cycle passed.
🇷🇺 **Принято** (2026-09-26) — регламент владельца от 25.09.2026 принят целиком; ядро добавлено
сабмодулем, пробный цикл пройден.

## Context / Контекст

🇬🇧 Agent work in this project runs on Claude, and the owner's weekly Claude limit was hitting
85–95 %. Most of the volume is mechanical: search, inventories, config comparison, docs, tests.
Project `work` (Belgorod) built a portable worker, `ds-worker`: a headless Claude Code CLI pointed
at DeepSeek's Anthropic-compatible API, with task cards, cost classes, a result contract and a
lead-only review. Its two trial tasks cost ≈ $0.08. The owner ordered it handed to this project
on 2026-09-26 (board `m0207`, `m0208`).

🇷🇺 Агентская работа в проекте идёт на Claude, и недельный лимит владельца упирался в 85–95 %.
Основной объём — механика: поиск, инвентарь, сравнение конфигов, документация, тесты. Проект `work`
(Белгород) собрал переносимый исполнитель `ds-worker`: Claude Code CLI без интерфейса, направленный
на Anthropic-совместимый API DeepSeek, с карточками задач, классами стоимости, контрактом результата
и приёмкой только ведущим. Две его пробные задачи стоили ≈ $0.08. Владелец велел передать его сюда
26.09 (доска `m0207`, `m0208`).

🇬🇧 Constraints specific to this project: the repository is **public**; the main checkout sits next
to `.env`, `docs/local/` (family data), `DNS/` (dynv6 token) and `.claude/` (allowlists holding real
secrets); the live system (Jetson, VPS, VPN of ~25 users) must never be touched by an unattended agent.

🇷🇺 Ограничения этого проекта: репозиторий **публичный**; рядом с основной копией лежат `.env`,
`docs/local/` (данные семьи), `DNS/` (токен dynv6) и `.claude/` (в allowlist копятся настоящие
секреты); живую систему (Jetson, VPS, VPN на ~25 человек) агент без присмотра трогать не должен.

## Decision / Решение

🇬🇧
1. **Roles.** Claude leads and dispatches; CHEAP tasks go to the DeepSeek worker as a `ds-worker`
   card, not to a Claude subagent; judgement work goes to Claude subagents; the owner decides
   anything irreversible. Written into `CLAUDE.md` as hard rule №16.
2. **CRITICAL for this project, never delegated:** tunnels, the VPS, Amnezia/WireGuard/xray, external
   access, data on the NAS disks, the live Jetson. The worker has no ssh, curl or web by construction.
3. **Code in the project as a git submodule** `tools/deepseek-worker`, pinned at `0311914`. The
   upstream is private; the public repo carries only the URL and hash. CI does not need it.
4. **Data boundary:** only git-tracked files reach the DeepSeek API. The worker runs in a worktree
   outside the main checkout (`E:/nas-ds-<task>`); `security.deny_read` blocks the whole main
   checkout, `E:/agent_coordination`, `~/.claude`, `~/.config`, `~/.ssh` and secret masks.
5. **Key:** the owner's file, billing shared with the Belgorod bot; passed only through the child
   process environment. Large batches are agreed with the owner.
6. **Acceptance:** only the lead's `review --accept` sets DONE, after verifying the claims against
   code or by a command. Two failed reworks → Claude takes the task.

🇷🇺
1. **Роли.** Claude — ведущий и диспетчер; CHEAP-задачи идут исполнителю DeepSeek карточкой
   `ds-worker`, а не субагенту Claude; работа с суждением — субагентам Claude; необратимое решает
   владелец. Закреплено в `CLAUDE.md` жёстким правилом №16.
2. **CRITICAL для проекта, не делегируется никогда:** туннели, VPS, Amnezia/WireGuard/xray, доступ
   снаружи, данные на дисках NAS, живой Jetson. У исполнителя нет ssh, curl и веба по построению.
3. **Код в проекте — сабмодулем** `tools/deepseek-worker`, закреплён на `0311914`. Источник приватный;
   публичный репозиторий несёт только адрес и хеш. CI он не нужен.
4. **Граница данных:** в API DeepSeek попадают только файлы, отслеживаемые git. Исполнитель работает
   в worktree вне основной копии (`E:/nas-ds-<task>`); `security.deny_read` запрещает основную копию
   целиком, `E:/agent_coordination`, `~/.claude`, `~/.config`, `~/.ssh` и маски секретов.
5. **Ключ:** файл владельца, счёт общий с ботом Белгорода; передаётся только в окружение дочернего
   процесса. Крупные серии задач согласуются с владельцем.
6. **Приёмка:** DONE ставит только `review --accept` ведущего после проверки утверждений по коду или
   командой. Две неудачные доработки — задачу забирает Claude.

## Consequences / Последствия

🇬🇧 **Plus:** mechanical work moves off the Claude limit at ~1–2 % of the cost; every result has a
contract (`RESULT.json`) and an explicit review. **Minus:** a second supplier and a shared bill;
`needs_edit: true` tasks can run code, which bypasses `deny_read` and sees the key — they are used
only deliberately; a private submodule in a public repo means a fresh clone without the owner's
account has a dangling pointer (harmless: nothing in the NAS runtime depends on it).
**Trial 2026-09-26:** `systemd/` inventory, ≈ $0.048 over two passes; contract violation caught
automatically; reading the main checkout outside the worktree was refused.

🇷🇺 **Плюс:** механика уходит из лимита Claude за ~1–2 % цены; у каждого результата есть контракт
(`RESULT.json`) и явная приёмка. **Минус:** второй поставщик и общий счёт; задачи с
`needs_edit: true` могут запускать код, обходящий `deny_read` и видящий ключ, — их дают только
осознанно; приватный сабмодуль в публичном репозитории означает, что у клона без учётки владельца
висит пустая ссылка (безвредно: работа NAS от неё не зависит).
**Пробный цикл 2026-09-26:** инвентарь `systemd/`, ≈ $0.048 за два прохода; нарушение контракта
поймано автоматически; чтение основной копии вне worktree получило отказ.

## References / Ссылки

- `docs/handoff/DEEPSEEK_WORKER.md` — full rules and project decisions / полный регламент и решения проекта
- `tools/deepseek-worker/docs/PROTOCOL.md` — protocol §1–20 / протокол
- `ds_worker.toml` — project config / конфиг проекта
- `docs/20_AGENT_OPERATING_MODEL.md` §10 — place in the agent model / место в модели агентов
- `CLAUDE.md` — hard rule №16 / жёсткое правило №16
