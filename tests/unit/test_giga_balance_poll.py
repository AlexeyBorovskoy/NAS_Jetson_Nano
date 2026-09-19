#!/usr/bin/env python3
"""E2: ежедневный опрос баланса GigaChat пишет файл для алерта — и только годный.

ЗАЧЕМ. Алерт (test_giga_balance_alert.py) судит по свежести файла. Если опрос
перезапишет файл ответом 502 или обрывком JSON, алерт примет сбой за «квоты в
порядке» либо за битые данные вместо «опрос сломан». Поэтому: при ошибке файл не
трогается (он стареет → алерт через 50 ч), запись атомарная.

curl подменяется заглушкой в PATH. Запуск: python3 tests/unit/test_giga_balance_poll.py
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "..", "scripts", "sber", "check_gigachat_balance.sh")
GOOD = '{"provider":"gigachat","balance":{"balance":[{"usage":"GigaChat","value":5}]}}'

STUB = """#!/usr/bin/env bash
# заглушка curl: пишет тело в файл после -o, печатает код для -w
out=""
while [ $# -gt 0 ]; do
  case "$1" in -o) out="$2"; shift;; esac; shift
done
printf '%s' "$STUB_BODY" > "$out"
printf '%s' "$STUB_CODE"
"""


def run(tmp, code, body):
    env = dict(os.environ)
    env["PATH"] = os.path.join(tmp, "bin") + os.pathsep + env.get("PATH", "")
    env["STUB_CODE"], env["STUB_BODY"] = code, body
    env["GIGA_BALANCE_FILE"] = os.path.join(tmp, "state", "balance.json")
    bash = shutil.which("bash") or "bash"
    p = subprocess.run([bash, SCRIPT], env=env, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, universal_newlines=True)
    return p.returncode, env["GIGA_BALANCE_FILE"]


def main():
    tmp = tempfile.mkdtemp()
    os.makedirs(os.path.join(tmp, "bin"))
    stub = os.path.join(tmp, "bin", "curl")
    with io.open(stub, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(STUB)
    os.chmod(stub, 0o755)
    failures = 0

    def case(name, cond, got):
        nonlocal failures
        print(("  [ok]   %s" if cond else "  [FAIL] %s\n         получено: %r") %
              ((name,) if cond else (name, got)))
        failures += 0 if cond else 1

    print("E2: опрос баланса пишет файл для алерта")
    rc, path = run(tmp, "200", GOOD)
    ok = rc == 0 and os.path.exists(path)
    got = io.open(path, encoding="utf-8").read() if os.path.exists(path) else None
    case("200 — файл записан, содержимое — ответ шлюза",
         ok and json.loads(got)["balance"]["balance"][0]["value"] == 5, (rc, got))

    rc, _ = run(tmp, "502", '{"detail":"upstream"}')
    after = io.open(path, encoding="utf-8").read()
    case("502 — код ошибки, прежний файл не тронут", rc != 0 and after == got, (rc, after))

    rc, _ = run(tmp, "200", '{"balance":')
    after = io.open(path, encoding="utf-8").read()
    case("200 с обрывком JSON — ошибка, файл не тронут", rc != 0 and after == got, (rc, after))

    leftovers = [n for n in os.listdir(os.path.dirname(path)) if n != "balance.json"]
    case("временных файлов не остаётся", not leftovers, leftovers)

    print("\nпадений: %d" % failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
