#!/usr/bin/env python3
"""Юниты systemd совместимы с systemd 237 (Ubuntu 18.04 на Jetson) — ворота REL-1.

ИСТОРИЯ ДЕФЕКТА. Юнит `nas_jetson_nano-boot-alert.service` (алерт D2, «сообщение
владельцу после аварийной загрузки») был написан как `Type=oneshot` вместе с
`Restart=on-failure`. Jetson живёт на systemd 237, а он такую комбинацию отвергает:
юнит получал `Loaded: error (Invalid argument)` и не запускался ни разу. Выкаченный
2026-09-20, он молчал все три аппаратных сброса Jetson (29.09, 06.10, 11.10) — то
есть инструмент, существовавший ровно ради этих событий, не сработал ни на одном из
них. Дефект найден 12.10 при разборе загрузок (`docs/plans/CHECKPOINT_2026-10-12.ru.md`,
раздел 2) и исправлен в git: `Type=simple`, `StartLimit*` → `[Unit]` (задача REL-1 в
`docs/plans/DEVELOPMENT_PLAN_2026-10_OWNER_GOALS.ru.md`). systemd разрешил oneshot
вместе с `Restart=` только с v244 — на системе 237 эта связка не поднимется никогда.
Проверок на это не было ни одной — потому дефект и дожил до боевой машины.

ЧТО ПРОВЕРЯЕТСЯ — два правила совместимости с systemd 237:

  1. `[Service]` `Type=oneshot` вместе с `Restart=` со значением, отличным от `no`
     (пустое значение = сброс к умолчанию, тоже допустимо). systemd 237 не грузит
     такой юнит: `Loaded: error (Invalid argument)`.
  2. Ключи `StartLimitBurst` / `StartLimitIntervalSec` / `StartLimitInterval` в
     секции `[Service]`. С systemd 230 их место — в `[Unit]`; в `[Service]` systemd
     237 их не понимает, пишет `Unknown lvalue` и ИГНОРИРУЕТ — ограничение числа
     попыток не действует, а юнит выглядит настроенным.

Проверяются все `systemd/**/*.service` проекта (только чтение — юниты не меняются).
Запуск (без pytest, идёт и на Jetson с Python 3.6, и в воротах `preflight.sh`):
    python3 tests/unit/test_systemd237_units.py
"""
import io
import re
import sys
import tempfile
import unittest
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", line_buffering=True)
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8",
                                  errors="replace", line_buffering=True)

ROOT = Path(__file__).resolve().parents[2]
UNITS_DIR = ROOT / "systemd"

SECTION_RE = re.compile(r"^\[([A-Za-z][A-Za-z0-9_.-]*)\]$")
ASSIGNMENT_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_.-]*)\s*=(.*)$")

# Правило 2: до systemd 230 эти ключи жили в [Service], с 230 — в [Unit].
START_LIMIT_KEYS = ("StartLimitBurst", "StartLimitIntervalSec", "StartLimitInterval")


def iter_assignments(text):
    """Разбор юнита: (номер строки, секция, ключ, значение).

    Пустые строки и комментарии (`#` и `;` в начале строки) пропускаются — это не
    украшение: в самом юните-носителе дефекта слова `Type=oneshot`,
    `Restart=on-failure` и `[Unit]` встречаются ВНУТРИ комментариев, и разбор без
    этой отсечки ругался бы на исправленный юнит.
    """
    section = None
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith(";"):
            continue
        header = SECTION_RE.match(line)
        if header:
            section = header.group(1)
            continue
        assignment = ASSIGNMENT_RE.match(line)
        if assignment is not None and section is not None:
            yield number, section, assignment.group(1), assignment.group(2).strip()


def check_unit(text):
    """Нарушения совместимости с systemd 237 в тексте юнита — списком строк.

    Каждая строка называет номер строки файла и номер правила, чтобы по сообщению
    можно было сразу править юнит, а не искать причину заново.
    """
    violations = []
    service = {}  # ключ -> (номер строки, значение); как в systemd, побеждает последнее
    for number, section, key, value in iter_assignments(text):
        if section != "Service":
            continue
        if key in START_LIMIT_KEYS:
            violations.append(
                "строка %d: %s=%s в [Service] — с systemd 230 место этого ключа в [Unit], "
                "в [Service] systemd 237 его игнорирует (правило 2)" % (number, key, value))
        service[key] = (number, value)

    unit_type = service.get("Type", (None, ""))[1]
    restart = service.get("Restart", (None, ""))
    # Пустая строка тоже не нарушение: `Restart=` без значения systemd трактует
    # как сброс к умолчанию, а умолчание — `no`.
    if unit_type == "oneshot" and restart[1] not in ("", "no"):
        violations.append(
            "строка %d: [Service] Type=oneshot с Restart=%s — systemd 237 не загрузит юнит "
            "(Loaded: error (Invalid argument)); повторы оставлять в самом скрипте "
            "(правило 1)" % (restart[0], restart[1]))
    return violations


def project_unit_files():
    """Все юниты *.service проекта в устойчивом порядке (drop-in *.conf не входят)."""
    return sorted(UNITS_DIR.rglob("*.service"), key=str)


def check_unit_files(paths):
    """Нарушения по списку файлов: '<путь относительно корня>: <нарушение>'."""
    failures = []
    for path in paths:
        try:
            label = path.relative_to(ROOT).as_posix()
        except ValueError:
            label = path.as_posix()
        with path.open(encoding="utf-8") as handle:
            text = handle.read()
        for violation in check_unit(text):
            failures.append("%s: %s" % (label, violation))
    return failures


# ── синтетические юниты ────────────────────────────────────────────────────────
# Именно эта связка стояла в nas_jetson_nano-boot-alert.service с 2026-09-20
# по 2026-10-12 и не давала алерту D2 загрузиться.
SYNTHETIC_ONESHOT_WITH_RESTART = """\
[Unit]
Description=Синтетика: oneshot + Restart — дефект REL-1
[Service]
Type=oneshot
ExecStart=/bin/true
Restart=on-failure
"""

SYNTHETIC_STARTLIMIT_IN_SERVICE = """\
[Unit]
Description=Синтетика: StartLimit* не в той секции
[Service]
Type=oneshot
ExecStart=/bin/true
StartLimitBurst=5
StartLimitIntervalSec=600
"""

SYNTHETIC_GOOD_LONG_RUNNING = """\
[Unit]
Description=Синтетика: долгоживущий юнит с повтором
StartLimitIntervalSec=600
StartLimitBurst=5

[Service]
Type=simple
ExecStart=/bin/sleep infinity
Restart=on-failure
RestartSec=60
"""

# Заодно проверка отсечки комментариев: обе «плохие» строки закомментированы.
SYNTHETIC_GOOD_ONESHOT_WITH_COMMENTS = """\
[Unit]
; точка с запятой — тоже комментарий
Description=Синтетика: oneshot, повтор выключен

[Service]
Type=oneshot
ExecStart=/bin/true
# Restart=on-failure — закомментировано и нарушением считаться не должно
; StartLimitBurst=5 — и эта строка тоже
Restart=no
"""


class Systemd237RuleTests(unittest.TestCase):
    """Синтетика: правила ловят дефект и не трогают правильные юниты."""

    def test_oneshot_with_restart_is_flagged(self):
        """(b) oneshot + Restart=on-failure — нарушение правила 1."""
        violations = check_unit(SYNTHETIC_ONESHOT_WITH_RESTART)
        self.assertTrue(violations, "oneshot+Restart не пойман — дефект REL-1 вернулся бы")
        self.assertTrue(any("правило 1" in v for v in violations), violations)
        self.assertTrue(any("on-failure" in v for v in violations), violations)
        # Указана строка самого Restart= (строка 6), а не Type= — иначе правка вслепую.
        self.assertTrue(any("строка 6" in v for v in violations), violations)

    def test_startlimit_in_service_is_flagged(self):
        """(c) StartLimit* в [Service] — по нарушению на каждый ключ, правило 2."""
        violations = check_unit(SYNTHETIC_STARTLIMIT_IN_SERVICE)
        self.assertEqual(len(violations), 2, violations)
        self.assertTrue(all("правило 2" in v for v in violations), violations)
        self.assertTrue(all("StartLimit" in v for v in violations), violations)

    def test_good_units_are_clean(self):
        """(d) Верные юниты нарушений не дают."""
        cases = (("simple + Restart=on-failure", SYNTHETIC_GOOD_LONG_RUNNING),
                 ("oneshot + Restart=no, комментарии", SYNTHETIC_GOOD_ONESHOT_WITH_COMMENTS))
        for name, text in cases:
            with self.subTest(name=name):
                self.assertEqual(check_unit(text), [])

    def test_comments_and_blank_lines_are_skipped(self):
        """Комментарии с '#' и ';' и пустые строки не считаются настройками."""
        text = ("[Unit]\n\n# Type=oneshot\n; Restart=on-failure\n[Service]\n"
                "Type=simple\n\n# [Service] StartLimitBurst=5\nRestart=always\n")
        self.assertEqual(check_unit(text), [])

    def test_violation_message_names_file_and_rule(self):
        """(a) Сообщение о нарушении называет файл и правило."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nas_jetson_nano-broken.service"
            with path.open("w", encoding="utf-8") as handle:
                handle.write(SYNTHETIC_ONESHOT_WITH_RESTART)
            failures = check_unit_files([path])
        self.assertEqual(len(failures), 1, failures)
        self.assertIn("nas_jetson_nano-broken.service", failures[0])
        self.assertIn("правило 1", failures[0])


class ProjectUnitGateTests(unittest.TestCase):
    """Все юниты проекта проходят ворота."""

    def test_units_are_found(self):
        """Ворота не должны молча проходить на пустом списке файлов."""
        names = [path.name for path in project_unit_files()]
        self.assertGreater(len(names), 0, "в systemd/ не найдено ни одного *.service")
        # Носитель дефекта REL-1: если он пропал из-под проверки — ворота проверяют не то.
        self.assertIn("nas_jetson_nano-boot-alert.service", names)

    def test_all_project_units_pass(self):
        """(a) Ни один systemd/*.service не нарушает правил 1 и 2."""
        failures = check_unit_files(project_unit_files())
        self.assertEqual(failures, [], "нарушения совместимости с systemd 237:\n"
                         + "\n".join(failures))

    def test_boot_alert_unit_regression(self):
        """Прямая регрессия REL-1: алерт D2 снова не окажется oneshot с Restart."""
        path = UNITS_DIR / "nas_jetson_nano-boot-alert.service"
        self.assertTrue(path.is_file())
        with path.open(encoding="utf-8") as handle:
            violations = check_unit(handle.read())
        self.assertEqual(violations, [], violations)


if __name__ == "__main__":
    unittest.main()
