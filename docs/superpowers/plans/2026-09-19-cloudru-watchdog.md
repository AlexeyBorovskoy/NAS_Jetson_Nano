# D3 — внешний сторож в Cloud.ru: план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** задача в Cloud.ru раз в 10 минут через VPS проверяет, жив ли NAS, и пишет владельцу в Telegram о пропаже и восстановлении.

**Architecture:** на VPS — скрипт `nas-liveness` (forced command отдельного пользователя `naswatch`): проверяет NAS API и Nextcloud через обратный туннель, хранит состояние и решает, тревожить ли. В Cloud.ru — `watchdog_job.py`: ходит на VPS по ssh, пересылает событие в Telegram напрямую, при неудаче — через `nas-liveness notify`; если молчит сам VPS — тревога раз в час.

**Tech Stack:** Python 3.12, только стандартная библиотека; pytest; bash (установщик); Docker (`python:3.12-alpine` + `openssh-client`).

**Spec:** `docs/superpowers/specs/2026-09-19-cloudru-watchdog-design.md`

## Global Constraints

- Язык комментариев, сообщений и документации — **русский**; у документа в `docs/` — EN summary (правило №15).
- Код сторожа лежит в `services/watchdog/`, **не** в `scripts/`: ворота требуют Python 3.6 для `scripts/`, а сторож работает на Python 3.12 (VPS Ubuntu 24.04 — Python 3.12.3, проверено 2026-09-19).
- Только стандартная библиотека Python. Никаких `requests`/`httpx`.
- Секретов в git нет: токен, chat_id, ключи — только пустые ключи в `*.env.example` (правило №1).
- Новых портов на VPS нет; Amnezia, nginx, sshd не перезапускаются (правило №13).
- Порты туннеля на VPS: NAS API — `127.0.0.1:18099/healthcheck`, Nextcloud — `127.0.0.1:18080/status.php` (оба 200, проверено 2026-09-19).
- Тревога — после **2** неудачных проверок подряд; повтор — раз в **24 ч**; «VPS не отвечает» — только если минута запуска **< 10**.
- Время в сообщениях — МСК (UTC+3), формат `ДД.ММ ЧЧ:ММ МСК`.
- Тесты — pytest в `tests/watchdog/`; каталог подключается к воротам `scripts/quality/preflight.sh` (раздел 9) и к CI (`.github/workflows/quality-checks.yml`, job `service-tests`).
- Каждый коммит заканчивается строкой `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`. Хук pre-commit запускает ворота сам; `--no-verify` запрещён.
- Выкат на VPS и в Cloud.ru в этот план **не входит** — только по команде владельца «деплой», по runbook из Task 5.

## Файлы

| Файл | Ответственность |
|---|---|
| `services/watchdog/vps/nas_liveness.py` | VPS: проверки, классификация, решение о тревоге, состояние, подкоманды `check`/`notify` |
| `services/watchdog/vps/install_vps.sh` | VPS: пользователь `naswatch`, установка скрипта, строка `authorized_keys`, `sshd -t` |
| `services/watchdog/job/watchdog_job.py` | Cloud.ru: ssh → разбор → Telegram / запасной путь / правило «VPS молчит» |
| `services/watchdog/job/Dockerfile` | образ задачи |
| `services/watchdog/job/job.env.example` | список переменных задачи, без значений |
| `tests/watchdog/conftest.py` | пути импорта |
| `tests/watchdog/test_nas_liveness.py` | тесты VPS-скрипта |
| `tests/watchdog/test_watchdog_job.py` | тесты задачи |
| `tests/watchdog/test_install_vps.py` | статические проверки установщика |
| `docs/plans/DEPLOY_D3_WATCHDOG_2026-09.md` | runbook: спайк в Cloud.ru + выкат |

---

### Task 1: Ядро решения на VPS — классификация, решение о тревоге, состояние

**Files:**
- Create: `services/watchdog/vps/nas_liveness.py`
- Create: `tests/watchdog/conftest.py`
- Create: `tests/watchdog/test_nas_liveness.py`
- Modify: `scripts/quality/preflight.sh` (строка с `for SVC_TESTS in tests/llm_gateway tests/nas_api; do`)
- Modify: `.github/workflows/quality-checks.yml` (job `service-tests`, после шага `NAS API tests`)

**Interfaces:**
- Produces:
  - `classify(api: int|None, nc: int|None) -> tuple[str|None, str|None]` — `("tunnel", текст)`, `("service", текст)` или `(None, None)`.
  - `decide(state: dict, key: str|None, text: str|None, now: float) -> tuple[str, str, dict]` — событие `"none"|"down"|"repeat"|"recovered"`, текст сообщения, новое состояние.
  - `load_state(path: str) -> dict`, `save_state(state: dict, path: str) -> None`.
  - константы `FAILS_BEFORE_ALERT = 2`, `REPEAT_AFTER = 86400`.

- [ ] **Step 1: conftest с путями импорта**

`tests/watchdog/conftest.py`:
```python
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for sub in ("services/watchdog/vps", "services/watchdog/job"):
    p = os.path.join(ROOT, sub)
    if p not in sys.path:
        sys.path.insert(0, p)
```

- [ ] **Step 2: падающие тесты ядра**

`tests/watchdog/test_nas_liveness.py`:
```python
"""D3: сторож на VPS. Спецификация — docs/superpowers/specs/2026-09-19-cloudru-watchdog-design.md §4."""
import json
import os

import nas_liveness as nl

T0 = 1_790_000_000.0  # произвольная точка отсчёта


def test_classify_both_silent_is_tunnel():
    key, text = nl.classify(None, None)
    assert key == "tunnel"
    assert "туннель" in text


def test_classify_service_error_names_service_and_code():
    key, text = nl.classify(200, 503)
    assert key == "service"
    assert "Nextcloud" in text and "503" in text
    assert "NAS API" not in text


def test_classify_one_silent_is_service_not_tunnel():
    key, text = nl.classify(None, 200)
    assert key == "service"
    assert "NAS API" in text and "нет ответа" in text


def test_classify_all_ok():
    assert nl.classify(200, 200) == (None, None)


def test_single_failure_is_quiet():
    key, text = nl.classify(None, None)
    event, msg, st = nl.decide({}, key, text, T0)
    assert event == "none" and msg == ""
    assert st["fails"] == 1 and st["down_since"] == T0


def test_second_failure_alerts_with_msk_time():
    key, text = nl.classify(None, None)
    _, _, st = nl.decide({}, key, text, T0)
    event, msg, st = nl.decide(st, key, text, T0 + 600)
    assert event == "down"
    assert "МСК" in msg
    assert st["alerted"] is True and st["last_sent"] == T0 + 600


def test_ongoing_problem_repeats_only_after_a_day():
    key, text = nl.classify(None, None)
    st = {}
    for i in range(2):
        _, _, st = nl.decide(st, key, text, T0 + i * 600)
    event, _, st = nl.decide(st, key, text, T0 + 3600)
    assert event == "none"
    event, msg, st = nl.decide(st, key, text, T0 + 600 + nl.REPEAT_AFTER)
    assert event == "repeat" and "Всё ещё" in msg


def test_problem_kind_change_while_alerted_sends_new_down():
    k1, t1 = nl.classify(200, 503)
    st = {}
    for i in range(2):
        _, _, st = nl.decide(st, k1, t1, T0 + i * 600)
    k2, t2 = nl.classify(None, None)
    event, msg, _ = nl.decide(st, k2, t2, T0 + 1200)
    assert event == "down" and "туннель" in msg


def test_recovery_after_alert_reports_downtime():
    key, text = nl.classify(None, None)
    st = {}
    for i in range(2):
        _, _, st = nl.decide(st, key, text, T0 + i * 600)
    event, msg, st = nl.decide(st, None, None, T0 + 47 * 60)
    assert event == "recovered"
    assert "47 мин" in msg
    assert st == {}


def test_recovery_without_alert_is_quiet():
    key, text = nl.classify(None, None)
    _, _, st = nl.decide({}, key, text, T0)
    event, msg, st = nl.decide(st, None, None, T0 + 600)
    assert event == "none" and st == {}


def test_state_roundtrip_is_atomic(tmp_path):
    path = str(tmp_path / "state.json")
    nl.save_state({"fails": 1}, path)
    assert nl.load_state(path) == {"fails": 1}
    assert os.listdir(tmp_path) == ["state.json"]


def test_broken_state_reads_as_empty(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("{битый", encoding="utf-8")
    assert nl.load_state(str(path)) == {}
    path.write_text(json.dumps([1, 2]), encoding="utf-8")
    assert nl.load_state(str(path)) == {}


def test_missing_state_reads_as_empty(tmp_path):
    assert nl.load_state(str(tmp_path / "нет.json")) == {}
```

- [ ] **Step 3: убедиться, что тесты падают**

Run: `python -m pytest -q tests/watchdog/test_nas_liveness.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'nas_liveness'`

- [ ] **Step 4: реализация ядра**

`services/watchdog/vps/nas_liveness.py`:
```python
#!/usr/bin/env python3
"""D3 — внешний сторож, часть на VPS (forced command пользователя naswatch).

Проверяет через обратный туннель, отвечают ли NAS API и Nextcloud, помнит
состояние и решает, тревожить ли владельца. Отправку делает задача в Cloud.ru;
здесь — только подкоманда notify как запасной путь в Telegram.

Спецификация: docs/superpowers/specs/2026-09-19-cloudru-watchdog-design.md.
Одиночный сбой — не тревога; тревога после двух подряд; повтор — раз в сутки;
о выздоровлении сообщаем всегда (как в nas_jetson_nano-talk-alert.py).
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

STATE_FILE = os.environ.get("NASWATCH_STATE", "/var/lib/naswatch/state.json")
API_URL = os.environ.get("NASWATCH_API_URL", "http://127.0.0.1:18099/healthcheck")
NC_URL = os.environ.get("NASWATCH_NC_URL", "http://127.0.0.1:18080/status.php")
TG_API = os.environ.get("NASWATCH_TG_API", "https://api.telegram.org")
PROBE_TIMEOUT = 10
FAILS_BEFORE_ALERT = 2
REPEAT_AFTER = 24 * 3600
MSK = 3 * 3600


def _msk(ts):
    return time.strftime("%d.%m %H:%M", time.gmtime(ts + MSK)) + " МСК"


# ── классификация ──────────────────────────────────────────────────────────────

def _describe(name, code):
    return "%s — %s" % (name, "нет ответа" if code is None else "HTTP %d" % code)


def classify(api, nc):
    """Молчат оба — отказал весь дом (туннель, питание, интернет, сам Jetson).
    Отвечает хоть кто-то — туннель жив, болеет сервис."""
    if api is None and nc is None:
        return "tunnel", ("🔴 NAS не отвечает — туннель закрыт "
                          "(питание, интернет дома или сам Jetson).")
    bad = [_describe(n, c) for n, c in (("NAS API", api), ("Nextcloud", nc)) if c != 200]
    if bad:
        return "service", "🟠 Туннель жив, но сервисы отвечают с ошибкой: %s." % "; ".join(bad)
    return None, None


# ── решение о тревоге ──────────────────────────────────────────────────────────

def decide(state, key, text, now):
    st = dict(state or {})
    if key is None:
        if st.get("alerted"):
            mins = int((now - st.get("down_since", now)) // 60)
            return "recovered", "✅ NAS снова на связи, простой %d мин." % mins, {}
        return "none", "", {}

    new = {
        "fails": st.get("fails", 0) + 1,
        "down_since": st.get("down_since") or now,
        "key": key,
        "alerted": bool(st.get("alerted")),
        "last_sent": st.get("last_sent", 0),
    }
    if new["fails"] < FAILS_BEFORE_ALERT:
        return "none", "", new
    since = " С %s." % _msk(new["down_since"])
    if not new["alerted"] or st.get("key") != key:
        new.update(alerted=True, last_sent=now)
        return "down", text + since, new
    if now - new["last_sent"] >= REPEAT_AFTER:
        new["last_sent"] = now
        return "repeat", "Всё ещё: " + text + since, new
    return "none", "", new


# ── состояние ──────────────────────────────────────────────────────────────────

def load_state(path=None):
    path = path or STATE_FILE
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_state(state, path=None):
    path = path or STATE_FILE
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False)
    os.replace(tmp, path)
```

- [ ] **Step 5: тесты проходят**

Run: `python -m pytest -q tests/watchdog/test_nas_liveness.py`
Expected: `13 passed`

- [ ] **Step 6: подключить `tests/watchdog` к воротам и CI**

В `scripts/quality/preflight.sh` строку
```bash
    for SVC_TESTS in tests/llm_gateway tests/nas_api; do
```
заменить на
```bash
    for SVC_TESTS in tests/llm_gateway tests/nas_api tests/watchdog; do
```
В `.github/workflows/quality-checks.yml` после шага
```yaml
      - name: NAS API tests
        run: python -m pytest -q tests/nas_api
```
добавить
```yaml

      - name: Watchdog tests (D3)
        run: python -m pytest -q tests/watchdog
```

- [ ] **Step 7: коммит**

```bash
git add services/watchdog/vps/nas_liveness.py tests/watchdog/conftest.py tests/watchdog/test_nas_liveness.py scripts/quality/preflight.sh .github/workflows/quality-checks.yml
git commit -m "feat(D3): watchdog core on VPS — classify, alert decision, atomic state

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```
Expected: ворота в выводе хука — `ВОРОТА ПРОЙДЕНЫ`, в разделе 9 есть строка `tests/watchdog: 13 passed`.

---

### Task 2: VPS — реальные проверки и подкоманды `check` / `notify`

**Files:**
- Modify: `services/watchdog/vps/nas_liveness.py` (дописать в конец)
- Modify: `tests/watchdog/test_nas_liveness.py` (дописать в конец)

**Interfaces:**
- Consumes: `classify`, `decide`, `load_state`, `save_state` из Task 1.
- Produces:
  - `probe(url: str, timeout: float = PROBE_TIMEOUT) -> int|None` — HTTP-код или `None`, если HTTP-ответа нет.
  - `cmd_check(now: float|None = None, probe_fn=probe, path: str|None = None) -> dict` — `{"event", "text", "api", "nextcloud", "checked_at"}`.
  - `send_telegram(token: str, chat_id: str, text: str) -> int` — HTTP-код, `0` при обрыве.
  - `cmd_notify(raw: str, send=send_telegram) -> dict` — `{"ok": bool, "code": int}`.
  - `main(argv: list|None = None) -> int` — команда из `SSH_ORIGINAL_COMMAND`, иначе из `argv`, по умолчанию `check`; печатает одну строку JSON.

- [ ] **Step 1: падающие тесты**

Дописать в `tests/watchdog/test_nas_liveness.py`:
```python
import http.server
import socket
import threading


def _serve(code):
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(code)
            self.end_headers()

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def _closed_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def test_probe_returns_http_code():
    for code in (200, 503):
        srv = _serve(code)
        try:
            assert nl.probe("http://127.0.0.1:%d/" % srv.server_port, timeout=5) == code
        finally:
            srv.shutdown()


def test_probe_closed_port_is_none():
    assert nl.probe("http://127.0.0.1:%d/" % _closed_port(), timeout=5) is None


def test_cmd_check_two_runs_alert_and_persist(tmp_path):
    path = str(tmp_path / "state.json")
    silent = lambda url: None
    first = nl.cmd_check(now=T0, probe_fn=silent, path=path)
    assert first["event"] == "none" and first["api"] is None
    second = nl.cmd_check(now=T0 + 600, probe_fn=silent, path=path)
    assert second["event"] == "down"
    assert second["checked_at"] == int(T0 + 600)
    healthy = nl.cmd_check(now=T0 + 1800, probe_fn=lambda url: 200, path=path)
    assert healthy["event"] == "recovered" and "30 мин" in healthy["text"]


def test_cmd_notify_passes_fields_and_reports_ok():
    seen = {}

    def fake_send(token, chat_id, text):
        seen.update(token=token, chat_id=chat_id, text=text)
        return 200

    raw = json.dumps({"token": "T", "chat_id": "42", "text": "привет"})
    assert nl.cmd_notify(raw, send=fake_send) == {"ok": True, "code": 200}
    assert seen == {"token": "T", "chat_id": "42", "text": "привет"}


def test_cmd_notify_rejects_bad_request_without_sending():
    called = []
    out = nl.cmd_notify("{битый", send=lambda *a: called.append(a) or 200)
    assert out["ok"] is False and called == []


def test_main_uses_ssh_original_command_and_prints_json(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SSH_ORIGINAL_COMMAND", "notify")
    monkeypatch.setattr(nl, "send_telegram", lambda t, c, x: 200)
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO(
        json.dumps({"token": "SECRET-TOKEN", "chat_id": "1", "text": "x"})))
    assert nl.main([]) == 0
    out = capsys.readouterr().out
    assert json.loads(out) == {"ok": True, "code": 200}
    assert "SECRET-TOKEN" not in out


def test_main_rejects_unknown_command(monkeypatch, capsys):
    monkeypatch.setenv("SSH_ORIGINAL_COMMAND", "bash -i")
    assert nl.main([]) == 2
    assert "unknown" in capsys.readouterr().out
```

- [ ] **Step 2: убедиться, что падают**

Run: `python -m pytest -q tests/watchdog/test_nas_liveness.py`
Expected: FAIL — `AttributeError: module 'nas_liveness' has no attribute 'probe'`

- [ ] **Step 3: реализация**

Дописать в конец `services/watchdog/vps/nas_liveness.py`:
```python
# ── проверки и команды ─────────────────────────────────────────────────────────

def probe(url, timeout=PROBE_TIMEOUT):
    """HTTP-код или None. None — HTTP-ответа нет вовсе: порт закрыт, туннель
    принял соединение и оборвал, таймаут. Любой код (и 4xx) — сервис ответил."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception:
        return None


def cmd_check(now=None, probe_fn=probe, path=None):
    now = time.time() if now is None else now
    api, nc = probe_fn(API_URL), probe_fn(NC_URL)
    key, text = classify(api, nc)
    event, message, new = decide(load_state(path), key, text, now)
    save_state(new, path)
    return {"event": event, "text": message, "api": api, "nextcloud": nc,
            "checked_at": int(now)}


def send_telegram(token, chat_id, text):
    req = urllib.request.Request(
        "%s/bot%s/sendMessage" % (TG_API, token),
        data=json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception:
        return 0


def cmd_notify(raw, send=send_telegram):
    """Запасной путь: токен и текст приходят через stdin, на VPS не хранятся."""
    try:
        req = json.loads(raw)
        token, chat_id, text = req["token"], req["chat_id"], req["text"]
    except (ValueError, KeyError, TypeError):
        return {"ok": False, "code": 0, "error": "bad request"}
    code = send(token, chat_id, text)
    return {"ok": code == 200, "code": code}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    raw = os.environ.get("SSH_ORIGINAL_COMMAND") or " ".join(argv) or "check"
    cmd = raw.split()[0]
    if cmd == "check":
        out, rc = cmd_check(), 0
    elif cmd == "notify":
        out, rc = cmd_notify(sys.stdin.read()), 0
    else:
        out, rc = {"error": "unknown command"}, 2
    print(json.dumps(out, ensure_ascii=False))
    return rc


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: тесты проходят**

Run: `python -m pytest -q tests/watchdog/test_nas_liveness.py`
Expected: `20 passed`

- [ ] **Step 5: коммит**

```bash
git add services/watchdog/vps/nas_liveness.py tests/watchdog/test_nas_liveness.py
git commit -m "feat(D3): VPS probes through the tunnel, check/notify commands

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: Задача в Cloud.ru — `watchdog_job.py`, Dockerfile, шаблон переменных

**Files:**
- Create: `services/watchdog/job/watchdog_job.py`
- Create: `services/watchdog/job/Dockerfile`
- Create: `services/watchdog/job/job.env.example`
- Create: `tests/watchdog/test_watchdog_job.py`

**Interfaces:**
- Consumes (по ssh, не импортом): вывод `nas-liveness check` — одна строка JSON `{"event": "none|down|repeat|recovered", "text": str, ...}`; `nas-liveness notify` читает stdin `{"token","chat_id","text"}` и печатает `{"ok": bool, "code": int}`.
- Produces:
  - `VPS_DOWN_TEXT: str`
  - `run_once(env: dict, now: datetime.datetime, ssh, send) -> tuple[str, bool]` — строка для журнала (без токена и текста) и признак успеха. `ssh(command: str, stdin_text: str|None = None) -> tuple[int, str]`; `send(token, chat_id, text) -> int`.
  - `prepare_ssh(env: dict, workdir: str) -> list[str]` — базовая команда ssh.
  - `main() -> int`.

- [ ] **Step 1: падающие тесты**

`tests/watchdog/test_watchdog_job.py`:
```python
"""D3: задача сторожа в Cloud.ru. Спецификация §2, §4, §5."""
import datetime
import json
import os

import watchdog_job as wj

ENV = {"TELEGRAM_BOT_TOKEN": "SECRET-TOKEN", "OWNER_CHAT_ID": "42",
       "VPS_HOST": "vps.example", "SSH_PRIVATE_KEY": "KEY", "SSH_KNOWN_HOSTS": "KH"}
UTC = datetime.timezone.utc


def at(minute):
    return datetime.datetime(2026, 9, 19, 3, minute, tzinfo=UTC)


class FakeSsh:
    def __init__(self, check_rc=0, check_out="", notify_out='{"ok": true, "code": 200}'):
        self.check_rc, self.check_out, self.notify_out = check_rc, check_out, notify_out
        self.calls = []

    def __call__(self, command, stdin_text=None):
        self.calls.append((command, stdin_text))
        if command == "check":
            return self.check_rc, self.check_out
        return 0, self.notify_out


class FakeSend:
    def __init__(self, code=200):
        self.code, self.sent = code, []

    def __call__(self, token, chat_id, text):
        self.sent.append((token, chat_id, text))
        return self.code


def check_json(event, text=""):
    return json.dumps({"event": event, "text": text, "api": 200, "nextcloud": 200}) + "\n"


def test_quiet_when_nothing_happened():
    send = FakeSend()
    log, ok = wj.run_once(ENV, at(5), FakeSsh(check_out=check_json("none")), send)
    assert ok and send.sent == []


def test_event_goes_to_owner_directly():
    send = FakeSend()
    ssh = FakeSsh(check_out=check_json("down", "🔴 NAS не отвечает"))
    log, ok = wj.run_once(ENV, at(25), ssh, send)
    assert ok
    assert send.sent == [("SECRET-TOKEN", "42", "🔴 NAS не отвечает")]
    assert [c for c, _ in ssh.calls] == ["check"]


def test_telegram_unreachable_falls_back_to_vps_relay():
    send = FakeSend(code=0)
    ssh = FakeSsh(check_out=check_json("recovered", "✅ снова на связи"))
    log, ok = wj.run_once(ENV, at(25), ssh, send)
    assert ok
    command, payload = ssh.calls[1]
    assert command == "notify"
    assert json.loads(payload) == {"token": "SECRET-TOKEN", "chat_id": "42",
                                   "text": "✅ снова на связи"}


def test_both_paths_failed_is_reported_as_failure():
    ssh = FakeSsh(check_out=check_json("down", "x"), notify_out='{"ok": false, "code": 0}')
    log, ok = wj.run_once(ENV, at(25), ssh, FakeSend(code=0))
    assert not ok


def test_vps_down_alerts_in_first_ten_minutes_of_hour():
    send = FakeSend()
    log, ok = wj.run_once(ENV, at(3), FakeSsh(check_rc=255), send)
    assert send.sent == [("SECRET-TOKEN", "42", wj.VPS_DOWN_TEXT)]


def test_vps_down_quiet_rest_of_hour():
    send = FakeSend()
    log, ok = wj.run_once(ENV, at(10), FakeSsh(check_rc=255), send)
    assert send.sent == [] and ok


def test_garbage_from_vps_counts_as_vps_down():
    send = FakeSend()
    wj.run_once(ENV, at(0), FakeSsh(check_out="not json"), send)
    assert send.sent[0][2] == wj.VPS_DOWN_TEXT


def test_log_line_never_contains_token_or_text():
    ssh = FakeSsh(check_out=check_json("down", "секретный текст"))
    log, _ = wj.run_once(ENV, at(25), ssh, FakeSend(code=0))
    assert "SECRET-TOKEN" not in log and "секретный" not in log


def test_prepare_ssh_writes_key_and_pins_host(tmp_path):
    cmd = wj.prepare_ssh(ENV, str(tmp_path))
    key = tmp_path / "id"
    assert key.read_text() == "KEY\n"
    assert (tmp_path / "known_hosts").read_text() == "KH\n"
    assert "StrictHostKeyChecking=yes" in cmd and "BatchMode=yes" in cmd
    assert cmd[-1] == "naswatch@vps.example"
    if os.name == "posix":
        assert (key.stat().st_mode & 0o777) == 0o600


def test_dockerfile_runs_unprivileged():
    here = os.path.dirname(os.path.abspath(__file__))
    df = os.path.join(here, "..", "..", "services", "watchdog", "job", "Dockerfile")
    text = open(df, encoding="utf-8").read()
    assert "openssh-client" in text
    assert "USER 10001" in text
```

- [ ] **Step 2: убедиться, что падают**

Run: `python -m pytest -q tests/watchdog/test_watchdog_job.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'watchdog_job'`

- [ ] **Step 3: реализация**

`services/watchdog/job/watchdog_job.py`:
```python
#!/usr/bin/env python3
"""D3 — внешний сторож, часть в Cloud.ru (Container Job раз в 10 мин).

Идёт по ssh на VPS (ключ с единственной командой nas-liveness), получает
событие и пересылает его владельцу в Telegram. Если Telegram из Cloud.ru
недоступен — просит VPS отправить (nas-liveness notify). Если молчит сам VPS,
состояние хранить негде: тревога только в запуске с минутой 00–09 — раз в час
(решение владельца 2026-09-19).

В журнал — только событие и коды; токен и текст сообщений не печатаются.
Спецификация: docs/superpowers/specs/2026-09-19-cloudru-watchdog-design.md.
"""
import datetime
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

VPS_DOWN_TEXT = ("🔴 VPS не отвечает: у семьи нет внешнего доступа к NAS и VPN. "
                 "Повтор — раз в час, пока не ответит.")
ALERT_EVENTS = ("down", "repeat", "recovered")
TG_API = "https://api.telegram.org"


def send_telegram(token, chat_id, text):
    # Копия nas_liveness.send_telegram: образы разные, общего модуля нет намеренно.
    req = urllib.request.Request(
        "%s/bot%s/sendMessage" % (TG_API, token),
        data=json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception:
        return 0


def _last_json(out):
    try:
        data = json.loads(out.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None
    return data if isinstance(data, dict) else None


def run_once(env, now, ssh, send):
    token, chat_id = env["TELEGRAM_BOT_TOKEN"], env["OWNER_CHAT_ID"]
    rc, out = ssh("check")
    result = _last_json(out) if rc == 0 else None
    if result is None or "event" not in result:
        if now.minute < 10:
            code = send(token, chat_id, VPS_DOWN_TEXT)
            return "vps_down alerted tg=%d" % code, code == 200
        return "vps_down quiet (не первый запуск часа)", True

    event = result["event"]
    if event not in ALERT_EVENTS:
        return "ok event=%s api=%s nc=%s" % (event, result.get("api"), result.get("nextcloud")), True

    code = send(token, chat_id, result["text"])
    if code == 200:
        return "sent event=%s tg=200" % event, True
    payload = json.dumps({"token": token, "chat_id": chat_id, "text": result["text"]})
    _, out2 = ssh("notify", payload)
    relayed = (_last_json(out2) or {}).get("ok") is True
    return "event=%s tg=%d relay=%s" % (event, code, "ok" if relayed else "fail"), relayed


def prepare_ssh(env, workdir):
    key = os.path.join(workdir, "id")
    known = os.path.join(workdir, "known_hosts")
    fd = os.open(key, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write(env["SSH_PRIVATE_KEY"].strip() + "\n")
    with open(known, "w") as fh:
        fh.write(env["SSH_KNOWN_HOSTS"].strip() + "\n")
    return ["ssh", "-i", key, "-o", "UserKnownHostsFile=" + known,
            "-o", "StrictHostKeyChecking=yes", "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=15",
            "%s@%s" % (env.get("VPS_USER", "naswatch"), env["VPS_HOST"])]


def make_ssh(base):
    def run(command, stdin_text=None):
        try:
            p = subprocess.run(base + [command], input=stdin_text,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               universal_newlines=True, timeout=40)
            return p.returncode, p.stdout
        except (subprocess.TimeoutExpired, OSError):
            return 255, ""
    return run


def main():
    env = dict(os.environ)
    with tempfile.TemporaryDirectory() as workdir:
        ssh = make_ssh(prepare_ssh(env, workdir))
        log, ok = run_once(env, datetime.datetime.now(datetime.timezone.utc), ssh, send_telegram)
    print(log)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
```

`services/watchdog/job/Dockerfile`:
```dockerfile
# D3: задача внешнего сторожа для Cloud.ru Container Jobs (amd64).
FROM python:3.12-alpine
RUN apk add --no-cache openssh-client && adduser -D -u 10001 watch
COPY watchdog_job.py /app/watchdog_job.py
USER 10001
CMD ["python", "/app/watchdog_job.py"]
```

`services/watchdog/job/job.env.example`:
```bash
# D3: переменные задачи сторожа. Значения — ТОЛЬКО в секретах Cloud.ru, не в git.
TELEGRAM_BOT_TOKEN=     # токен @bobik_borovskoy_bot; при смене — менять и в .env Jetson
OWNER_CHAT_ID=          # chat_id владельца (после /start в боте)
VPS_HOST=95.163.176.103
VPS_USER=naswatch
SSH_PRIVATE_KEY=        # приватный ключ сторожа (ed25519), целиком
SSH_KNOWN_HOSTS=        # строка known_hosts VPS: ssh-keyscan -t ed25519 95.163.176.103
```

- [ ] **Step 4: тесты проходят**

Run: `python -m pytest -q tests/watchdog`
Expected: `30 passed`

- [ ] **Step 5: коммит**

```bash
git add services/watchdog/job tests/watchdog/test_watchdog_job.py
git commit -m "feat(D3): Cloud.ru watchdog job — relay fallback, hourly VPS-down rule, no secrets in logs

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: Установщик на VPS

**Files:**
- Create: `services/watchdog/vps/install_vps.sh`
- Create: `tests/watchdog/test_install_vps.py`

**Interfaces:**
- Consumes: `services/watchdog/vps/nas_liveness.py` (копируется в `/usr/local/bin/nas-liveness`); состояние по умолчанию `/var/lib/naswatch/state.json` (Task 1).
- Produces: пользователь `naswatch` (home `/var/lib/naswatch`), строка `restrict,command="/usr/local/bin/nas-liveness" <ключ>` в `/var/lib/naswatch/.ssh/authorized_keys`.

- [ ] **Step 1: падающий тест**

`tests/watchdog/test_install_vps.py`:
```python
"""D3: установщик на VPS — статические гарантии (правило №13, спецификация §5).

Установщик выполняется только на VPS по «деплой», поэтому здесь проверяется
текст: ключ с единственной командой, sshd не перезапускается, sshd -t есть,
Amnezia/nginx/docker не упоминаются.
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "..", "services", "watchdog", "vps", "install_vps.sh")


def src():
    return open(SCRIPT, encoding="utf-8").read()


def test_key_is_restricted_to_one_command():
    assert 'restrict,command=\\"/usr/local/bin/nas-liveness\\"' in src()


def test_sshd_config_checked_and_never_restarted():
    s = src()
    assert "sshd -t" in s
    assert not re.search(r"systemctl\s+(restart|reload|stop)\s+ssh", s)


def test_does_not_touch_vpn_or_proxy_or_docker():
    s = src().lower()
    for word in ("amnezia", "nginx", "docker", "ufw", "iptables"):
        assert word not in s, word


def test_only_ed25519_keys_accepted():
    assert "ssh-ed25519" in src()


def test_password_is_not_locked_style():
    # «!» в shadow OpenSSH считает заблокированным аккаунтом и может отказать во входе по ключу.
    assert "usermod -p '*' naswatch" in src()


def test_idempotent_authorized_keys():
    assert "grep -qxF" in src()
```

- [ ] **Step 2: убедиться, что падает**

Run: `python -m pytest -q tests/watchdog/test_install_vps.py`
Expected: FAIL — `FileNotFoundError`

- [ ] **Step 3: реализация**

`services/watchdog/vps/install_vps.sh`:
```bash
#!/usr/bin/env bash
# D3: установка части сторожа на VPS. Только по команде «деплой», runbook —
# docs/plans/DEPLOY_D3_WATCHDOG_2026-09.md.
#   sudo bash install_vps.sh "ssh-ed25519 AAAA... nas-watchdog"
# Что делает: пользователь naswatch (без sudo), /usr/local/bin/nas-liveness,
# ключ сторожа с единственной командой. sshd не перезапускается: authorized_keys
# читается при каждом входе. Новых портов нет.
set -euo pipefail

PUB="${1:?нужен публичный ключ сторожа одной строкой: ssh-ed25519 ...}"
case "$PUB" in
  ssh-ed25519\ *) ;;
  *) echo "ожидается ключ ssh-ed25519" >&2; exit 2 ;;
esac
HERE="$(dirname "$(readlink -f "$0")")"

if ! id naswatch >/dev/null 2>&1; then
  useradd --system --create-home --home-dir /var/lib/naswatch --shell /bin/sh naswatch
fi
usermod -p '*' naswatch

install -m 0755 -o root -g root "$HERE/nas_liveness.py" /usr/local/bin/nas-liveness
install -d -m 0700 -o naswatch -g naswatch /var/lib/naswatch/.ssh

AK=/var/lib/naswatch/.ssh/authorized_keys
LINE="restrict,command=\"/usr/local/bin/nas-liveness\" $PUB"
touch "$AK"
grep -qxF "$LINE" "$AK" || printf '%s\n' "$LINE" >> "$AK"
chown naswatch:naswatch "$AK"
chmod 600 "$AK"

sshd -t
echo "проверка от имени naswatch:"
sudo -u naswatch /usr/local/bin/nas-liveness check
```

- [ ] **Step 4: тесты проходят**

Run: `python -m pytest -q tests/watchdog && bash -n services/watchdog/vps/install_vps.sh`
Expected: `36 passed`, `bash -n` без вывода.

- [ ] **Step 5: коммит**

```bash
git add services/watchdog/vps/install_vps.sh tests/watchdog/test_install_vps.py
git commit -m "feat(D3): VPS installer — naswatch user, single-command key, sshd -t only

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: Runbook выката и журнал плана

**Files:**
- Create: `docs/plans/DEPLOY_D3_WATCHDOG_2026-09.md`
- Modify: `docs/plans/DEVELOPMENT_PLAN_2026-09_SBER_ERA.md` (§1 журнал — строка после `| 2026-09-19 | **C11** имя API-контейнера | ✅ (A4) | \`a12c5bd\` |`)

**Interfaces:**
- Consumes: все файлы Task 1–4; команды и пути — ровно как в них.

- [ ] **Step 1: runbook**

`docs/plans/DEPLOY_D3_WATCHDOG_2026-09.md`:
````markdown
# Выкат D3 — внешний сторож / D3 external watchdog rollout (2026-09)

> 🇷🇺 Только по команде владельца «деплой». Каждый шаг — проверка; расхождение — стоп.
> Спецификация: `docs/superpowers/specs/2026-09-19-cloudru-watchdog-design.md`. EN summary — в конце.

## 0. Спайк в Cloud.ru (до выката; ресурсы — тестовые, удаляются)
Проверить из разовой Container Job на образе `python:3.12-alpine`:
```sh
python -c "import urllib.request as u; print(u.urlopen('https://api.telegram.org', timeout=15).status)"
```
| Вопрос | Как понять | Если «нет» |
|---|---|---|
| Образ из публичного реестра тянется | задача стартовала | собрать `services/watchdog/job` на VPS (`docker build`, amd64) → Artifact Registry Cloud.ru |
| Telegram доступен | `200` или `302` в журнале задачи | основной путь — `notify` через VPS; слепое пятно «VPS мёртв + Telegram закрыт» записать в спецификацию |
| Расписание есть | в форме задачи есть cron | стоп, решение владельца |

## 1. Правило №13 — ДО
```bash
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 \
  'docker ps --format "{{.Names}} {{.Status}}" | grep amnezia; docker exec amnezia-awg2 wg show | grep -c "^peer"; ss -tulnH | awk "{print \$5}" | grep -vE "^(127\.|\[::1\]|10\.|172\.)" | sort -u'
```
Записать: StartedAt `amnezia-*`, число пиров, внешние порты (22/443/40568).

## 2. Ключ сторожа (на рабочей станции, вне git)
```bash
ssh-keygen -t ed25519 -N "" -C nas-watchdog -f "$SCRATCH/nas-watchdog"
ssh-keyscan -t ed25519 95.163.176.103 > "$SCRATCH/vps_known_hosts"
```
Приватный ключ — сразу в секреты Cloud.ru и Windows Credential Manager (`nas-watchdog-ssh-key`), с диска удалить.

## 3. VPS
```bash
scp services/watchdog/vps/{nas_liveness.py,install_vps.sh} root@95.163.176.103:/root/naswatch/
ssh root@95.163.176.103 'sshd -T | grep -iE "^(allowusers|allowgroups|denyusers) " || echo "ограничений нет"'
ssh root@95.163.176.103 "bash /root/naswatch/install_vps.sh '$(cat "$SCRATCH/nas-watchdog.pub")'"
# с рабочей станции ключом сторожа:
ssh -i "$SCRATCH/nas-watchdog" naswatch@95.163.176.103 check     # одна строка JSON
ssh -i "$SCRATCH/nas-watchdog" naswatch@95.163.176.103 bash      # {"error": "unknown command"}
ssh -i "$SCRATCH/nas-watchdog" -N -L 9999:127.0.0.1:22 naswatch@95.163.176.103   # отказ проброса
```
Если `AllowUsers` задан — **стоп**: добавлять `naswatch` в sshd_config только отдельным решением.

> ⚠️ Исправлено в runbook (ac5ccf3): токен не должен попадать в argv curl — см. DEPLOY_D3_WATCHDOG_2026-09.md §4.

## 4. chat_id владельца
Владелец пишет `/start` боту @bobik_borovskoy_bot. На Jetson; токен идёт через stdin, не через
командную строку (иначе виден в `ps` на VPS), и не печатается:
```bash
cd ~/nasa && grep '^TELEGRAM_BOT_TOKEN=' config/.env | cut -d= -f2- | tr -d '"' \
 | ssh -i ~/.ssh/id_ed25519 root@95.163.176.103 'read -r T; curl -s "https://api.telegram.org/bot$T/getUpdates"' \
 | python3 -c 'import json,sys; print({u["message"]["chat"]["id"] for u in json.load(sys.stdin)["result"] if "message" in u})'
```

## 5. Cloud.ru
Container Job: образ (по итогам §0), расписание `*/10 * * * *`, `max instances = 1`, таймаут 60 с,
самая малая конфигурация. Секреты — ключи из `services/watchdog/job/job.env.example`.
Ручной запуск → в журнале `ok event=none api=200 nc=200`.

## 6. Боевая проверка (время выбирает владельец; снаружи NAS ~20 мин не виден, дома работает)
```bash
ssh admin@192.168.0.50 'echo "$P" | sudo -S systemctl stop nasa-tunnel.service'   # P — из .env устройства
# ждать: 2 запуска → «🔴 NAS не отвечает …» в Telegram
ssh admin@192.168.0.50 'echo "$P" | sudo -S systemctl start nasa-tunnel.service'
# следующий запуск → «✅ NAS снова на связи, простой N мин»
```

## 7. Правило №13 — ПОСЛЕ; откат
Сверить с §1. Откат: удалить задачу в Cloud.ru; на VPS `userdel -r naswatch && rm /usr/local/bin/nas-liveness`.

## EN summary
Spike in Cloud.ru first (image pull, Telegram reachability, schedules). Record the VPN baseline, create a
dedicated ed25519 key, install `nas-liveness` for a no-sudo `naswatch` user with a single-command key, and
verify that no shell or forwarding is allowed. Get the owner's chat_id via `/start`, create the Cloud.ru job
every 10 minutes with max one instance, then prove it by stopping the Jetson tunnel for 20 minutes. Compare
the VPN state after. Rollback: delete the job, remove the user and the script.
````

- [ ] **Step 2: строка в журнал плана**

В `docs/plans/DEVELOPMENT_PLAN_2026-09_SBER_ERA.md` после строки
```
| 2026-09-19 | **C11** имя API-контейнера | ✅ (A4) | `a12c5bd` |
```
вставить
```
| 2026-09-19 | **E2** алерт квоты GigaChat (порог по моделям, устаревший опрос) | ✅ git; выкат по «деплой» | `6bd36bf` |
| 2026-09-19 | **D3** внешний сторож Cloud.ru: VPS-скрипт, задача, установщик, 36 тестов | ✅ git; спайк + выкат — `DEPLOY_D3_WATCHDOG_2026-09.md` | спецификация `126e06b` |
```

- [ ] **Step 3: коммит**

```bash
git add docs/plans/DEPLOY_D3_WATCHDOG_2026-09.md docs/plans/DEVELOPMENT_PLAN_2026-09_SBER_ERA.md
git commit -m "docs(D3): watchdog rollout runbook (spike, VPS, Cloud.ru, live test); plan log

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Self-review (выполнено автором плана)

- Спецификация §2–§5, §7 → Task 1–4; §6 (спайк) и §8 (выкат) → Task 5 (runbook). Замечание: если оба пути отправки упали, VPS уже отметил тревогу отправленной — событие потеряно до повтора через сутки; задача завершается с кодом 1 и это видно в журнале Cloud.ru. Принято как известное ограничение.
- Имена сверены: `classify`/`decide`/`load_state`/`save_state`/`probe`/`cmd_check`/`cmd_notify`/`send_telegram`/`main` (VPS); `run_once`/`prepare_ssh`/`make_ssh`/`VPS_DOWN_TEXT` (job).
- Счёт тестов: Task 1 — 13, Task 2 — +7 = 20, Task 3 — +10 = 30, Task 4 — +6 = 36.
