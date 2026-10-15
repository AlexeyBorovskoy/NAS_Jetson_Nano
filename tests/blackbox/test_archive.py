"""OBS-1 «чёрный ящик», задача 9: недельный архив на HDD (blackbox/archive.py).

Покрытие — таблица «Случаи для тестов» задачи 9 плана
`docs/superpowers/plans/2026-10-13-obs1-blackbox.ru.md` (каждая строка — минимум
один тест); спецификация — раздел 5.3 («Недельный архив на HDD»)
`docs/superpowers/specs/2026-10-13-blackbox-forensics-design.ru.md`.
В разделе «Фокус ревью» плана задача 9 не значится (там задачи 3, 4, 5, 7, 11),
поэтому тестов с обязательным именем «фокуса» у неё нет — это не пропуск.

TDD: пакета `services/blackbox` ещё нет, поэтому файл обязан падать на импорте
(`ModuleNotFoundError: No module named 'blackbox'`) при сборе тестов, а не на
утверждениях.

Ни одного настоящего процесса: каждая внешняя команда идёт через параметр `run`
(подставной `subprocess.run`), каталоги SSD/HDD — `tmp_path`, в `/mnt` ничего не
пишется. Работает одинаково на Windows и Linux.

Договорённости, которых план не проговаривает дословно и которые фиксируют тесты:
- `week` — строка ISO-недели «ГГГГ-Wнн», `today` — строка дня «ГГГГ-ММ-ДД»
  (как `day_for_ts`); `weeks_due` возвращает недели по возрастанию;
- `archive_week` → dict с ключом «status» («shipped»/«deferred»/«failed») и
  «reason» — непустая строка причины при deferred/failed;
- «горячее» — `<ssd_root>/hot/<день>/`, сборка — `<ssd_root>/staging/`; на HDD
  архив ложится в `<hdd_archive_root>/<год>/blackbox-<неделя>.tar.xz`, рядом —
  `<то же>.sha256`; каталог года (2026/) создаёт сам архиватор: установщик
  заранее его знать не может;
- `ship(path, sha, hdd_dir, run)`: `hdd_dir` — целевой каталог (год недели);
  копия идёт «timeout 1800 cp» во временное имя, затем `os.rename` (Python)
  и «timeout 600 sha256sum» со сверкой; временного файла на HDD не остаётся.
"""
import hashlib
import os
import tarfile

from blackbox.archive import (
    archive_week,
    build_archive,
    hdd_alive,
    hdd_busy,
    prune_hdd,
    ship,
    weeks_due,
)
from blackbox.config import Config
from blackbox.store import Catalog

TODAY = "2026-10-13"  # день из таблицы случаев: вторник

# Дни «горячего» в тестах — 2026-10-01…2026-10-13, как в строке 1 таблицы.
# W40 (28.09–04.10) заканчивается на 10-04 и потому старше 7 суток;
# W41 (05–11.10) и W42 (12–18.10) — ещё не к отправке.
W40_PRESENT_DAYS = ["2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04"]
LATER_DAYS = ["2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08",
              "2026-10-09", "2026-10-10", "2026-10-11",
              "2026-10-12", "2026-10-13"]
DAYS = W40_PRESENT_DAYS + LATER_DAYS
W40_DAYS = ["2026-09-28", "2026-09-29", "2026-09-30"] + W40_PRESENT_DAYS


# ── подставной subprocess.run ────────────────────────────────────────────────


class _FakeCompleted(object):
    """Ответ как у subprocess.CompletedProcess."""

    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _FakeRun(object):
    """Подставной subprocess.run: помнит команды, выполняет только безобидное.

    Команда узнаётся по словам, поэтому «timeout 1800 cp …» и «cp …»
    обрабатываются одинаково. Копирование `cp` выполняется средствами Python,
    `sha256sum` считается hashlib — ничего настоящего не запускается.

    active_units — юниты, на которые systemctl is-active отвечает «active»;
    restic — правда ли, что виден процесс restic (pgrep отвечает кодом 0);
    stat_ok — отвечает ли HDD на «timeout 5 stat -f» (код 0);
    sha256_override — подмена ответа sha256sum (имитация битой копии на HDD).
    """

    def __init__(self, active_units=(), restic=False, stat_ok=True,
                 sha256_override=None):
        self.active_units = tuple(active_units)
        self.restic = restic
        self.stat_ok = stat_ok
        self.sha256_override = sha256_override
        self.calls = []

    @staticmethod
    def _index(parts, name):
        for i, part in enumerate(parts):
            if part == name or part.endswith("/" + name) or part.endswith("\\" + name):
                return i
        return -1

    def _argv_after(self, parts, name):
        """Аргументы после слова-команды, служебные ключи (-f и подобные) — прочь."""
        rest = parts[self._index(parts, name) + 1:]
        return [part for part in rest if not part.startswith("-")]

    def __call__(self, args, **kwargs):
        if isinstance(args, str):
            args = args.split()
        parts = [str(a) for a in args]
        self.calls.append(parts)
        if self._index(parts, "sha256sum") >= 0:
            return self._sha256sum(parts)
        if self._index(parts, "cp") >= 0:
            return self._cp(parts)
        if self._index(parts, "sync") >= 0:
            return _FakeCompleted(0)
        if self._index(parts, "mkdir") >= 0:
            # каталог года архиватор вправе создавать командой, а не Python'ом
            for path in self._argv_after(parts, "mkdir"):
                if not os.path.isdir(path):
                    os.makedirs(path)
            return _FakeCompleted(0)
        if self._index(parts, "stat") >= 0 and "-f" in parts:
            if self.stat_ok:
                return _FakeCompleted(0, "  File: \"hdd\"\n")
            return _FakeCompleted(1, "", "stat: cannot read file system information")
        if self._index(parts, "systemctl") >= 0 and "is-active" in parts:
            return self._systemctl(parts)
        if "restic" in " ".join(parts):
            if self.restic:
                return _FakeCompleted(0, "4242\n")
            return _FakeCompleted(1)
        return _FakeCompleted(0)

    def _cp(self, parts):
        argv = self._argv_after(parts, "cp")
        if len(argv) < 2:
            return _FakeCompleted(1, "", "cp: missing operand")
        src, dst = argv[0], argv[1]
        with open(src, "rb") as fh:
            data = fh.read()
        with open(dst, "wb") as fh:
            fh.write(data)
        return _FakeCompleted(0)

    def _sha256sum(self, parts):
        argv = self._argv_after(parts, "sha256sum")
        if not argv:
            return _FakeCompleted(1, "", "sha256sum: missing operand")
        path = argv[-1]
        if self.sha256_override is not None:
            digest = self.sha256_override
        else:
            with open(path, "rb") as fh:
                digest = hashlib.sha256(fh.read()).hexdigest()
        return _FakeCompleted(0, "%s  %s\n" % (digest, path))

    def _systemctl(self, parts):
        i = parts.index("is-active")
        units = [p for p in parts[i + 1:] if not p.startswith("-")]
        if not units:
            return _FakeCompleted(3, "unknown\n")
        states = ["active" if unit in self.active_units else "inactive"
                  for unit in units]
        rc = 0 if all(state == "active" for state in states) else 3
        return _FakeCompleted(rc, "\n".join(states) + "\n")


# ── общая подготовка временных каталогов ─────────────────────────────────────


def _config(tmp_path):
    """Config с временными корнями вместо /mnt (остальное — по умолчанию)."""
    return Config(
        ssd_root=str(tmp_path / "ssd"),
        fallback_root=str(tmp_path / "fallback"),
        hdd_archive_root=str(tmp_path / "hdd" / "backups" / "blackbox"),
        hdd_mount=str(tmp_path / "hdd"),
    )


def _prepare(tmp_path):
    """Каталоги, которые создаёт установщик (задача 13): корни SSD/HDD и staging.

    Каталог года на HDD (2026/) намеренно не создаётся — его обязан создать
    сам архиватор: новый год заранее не создаётся никем.
    """
    cfg = _config(tmp_path)
    os.makedirs(cfg.hdd_archive_root)
    os.makedirs(os.path.join(cfg.ssd_root, "staging"))
    return cfg


def _make_days(hot_root, days):
    """Дни «горячего»: каталог дня с файлами metrics.db и procs.db."""
    for day in days:
        day_dir = os.path.join(hot_root, day)
        os.makedirs(day_dir)
        for name in ("metrics.db", "procs.db"):
            with open(os.path.join(day_dir, name), "wb") as fh:
                fh.write(day.encode("ascii"))


def _archive_case(tmp_path):
    """Строки 2–5 таблицы: временные SSD/HDD, каталог и дни 01–13.10 в «горячем»."""
    cfg = _prepare(tmp_path)
    catalog = Catalog(str(tmp_path / "catalog.db"))
    hot = os.path.join(cfg.ssd_root, "hot")
    _make_days(hot, DAYS)
    return cfg, catalog, hot


def _files_under(root):
    """Все файлы (не каталоги) под корнем — для проверки «на HDD ничего»."""
    found = []
    for base, _dirs, names in os.walk(str(root)):
        for name in names:
            found.append(os.path.join(base, name))
    return sorted(found)


def _days_present(hot, days):
    return [day for day in days if os.path.exists(os.path.join(hot, day))]


# ── weeks_due ────────────────────────────────────────────────────────────────


def test_weeks_due_returns_weeks_older_than_min_age(tmp_path):
    """Строка таблицы 1: дни 2026-10-01…10-13, today=2026-10-13 → ["2026-W40"].

    W40 = 28.09–04.10: её последний день (04.10) старше 7 суток.
    W41 = 05–11.10: последний день 11.10 — всего 2 суток, не к отправке.
    W42 (12–18.10) — тем более. Недели идут по возрастанию.
    """
    hot_root = tmp_path / "hot"
    _make_days(str(hot_root), DAYS)

    assert weeks_due(str(hot_root), TODAY) == ["2026-W40"]

    # С меньшим сроком уходит и W41: последний её день 11.10 — двое суток;
    # W42 не уходит и здесь — у неё дни 12–13.10 ещё свежие, а 18.10 не настал.
    assert weeks_due(str(hot_root), TODAY, min_age_days=1) == ["2026-W40", "2026-W41"]


# ── hdd_busy / hdd_alive ─────────────────────────────────────────────────────


def test_hdd_busy_returns_active_unit_name(tmp_path):
    """Интерфейс: имя активного юнита из cfg.hdd_busy_units, а спокойное
    состояние — None; спрошены именно юниты из конфига."""
    cfg = _config(tmp_path)
    busy = _FakeRun(active_units=("nas_jetson_nano-immich-hdd-copy.service",))
    assert hdd_busy(cfg, busy) == "nas_jetson_nano-immich-hdd-copy.service"

    calm = _FakeRun()
    assert hdd_busy(cfg, calm) is None
    questioned = " ".join(" ".join(call) for call in calm.calls)
    for unit in cfg.hdd_busy_units:
        assert unit in questioned


def test_hdd_busy_reports_restic_process(tmp_path):
    """Спецификация 5.3(2): архиватор откладывает и когда идёт процесс restic."""
    cfg = _config(tmp_path)
    assert hdd_busy(cfg, _FakeRun(restic=True)) == "restic"


def test_hdd_alive_false_when_stat_fails(tmp_path):
    """Интерфейс: hdd_alive зовёт «timeout … stat -f <hdd_mount>»;
    код 0 — жив, иной код — мёртв."""
    cfg = _config(tmp_path)
    assert hdd_alive(cfg, _FakeRun(stat_ok=True)) is True

    dead = _FakeRun(stat_ok=False)
    assert hdd_alive(cfg, dead) is False
    stat_calls = [call for call in dead.calls if "stat" in call and "-f" in call]
    assert stat_calls
    assert cfg.hdd_mount in stat_calls[0]
    assert any(part.endswith("timeout") for part in stat_calls[0])


# ── build_archive / ship ─────────────────────────────────────────────────────


def test_build_archive_writes_xz_of_week_days_with_sha256(tmp_path):
    """Интерфейс: build_archive(hot_root, week, staging) → (path, sha256);
    в архив входят дни недели и только они, sha256 — хэш готового файла."""
    hot_root = tmp_path / "hot"
    staging = tmp_path / "staging"
    os.makedirs(str(staging))
    _make_days(str(hot_root), ["2026-10-01", "2026-10-02", "2026-10-05"])

    path, sha = build_archive(str(hot_root), "2026-W40", str(staging))

    assert os.path.basename(path) == "blackbox-2026-W40.tar.xz"
    assert os.path.exists(path)
    with open(path, "rb") as fh:
        assert sha == hashlib.sha256(fh.read()).hexdigest()

    with tarfile.open(path, "r:xz") as tar:
        names = tar.getnames()
    assert any(name.endswith("2026-10-01/metrics.db") for name in names)
    assert any(name.endswith("2026-10-02/metrics.db") for name in names)
    assert not any("2026-10-05" in name for name in names)  # W41 — не в W40


def test_ship_copies_verifies_and_renames(tmp_path):
    """Интерфейс: ship(path, sha, hdd_dir, run) — «timeout 1800 cp» во временное
    имя, sync, os.rename под именем архива, «sha256sum» и сверка → True;
    временного файла на HDD не остаётся."""
    staging = tmp_path / "staging"
    os.makedirs(str(staging))
    src = staging / "blackbox-2026-W40.tar.xz"
    payload = b"szhatyj-arhiv\n" * 64
    src.write_bytes(payload)
    sha = hashlib.sha256(payload).hexdigest()

    hdd_dir = tmp_path / "hdd" / "2026"
    os.makedirs(str(hdd_dir))
    run = _FakeRun()

    assert ship(str(src), sha, str(hdd_dir), run) is True

    final = hdd_dir / "blackbox-2026-W40.tar.xz"
    assert final.exists()
    assert final.read_bytes() == payload
    names = sorted(p.name for p in hdd_dir.iterdir())
    assert [n for n in names if n.endswith(".tar.xz")] == ["blackbox-2026-W40.tar.xz"]
    assert any("cp" in call for call in run.calls)
    assert any("sync" in call for call in run.calls)
    assert any("sha256sum" in call for call in run.calls)


def test_ship_returns_false_when_sha256_differs(tmp_path):
    """Интерфейс: сверка sha256 обязательна — ответ HDD не совпал → False."""
    staging = tmp_path / "staging"
    os.makedirs(str(staging))
    src = staging / "blackbox-2026-W40.tar.xz"
    src.write_bytes(b"arhiv")
    sha = hashlib.sha256(b"arhiv").hexdigest()

    hdd_dir = tmp_path / "hdd" / "2026"
    os.makedirs(str(hdd_dir))
    run = _FakeRun(sha256_override="0" * 64)

    assert ship(str(src), sha, str(hdd_dir), run) is False
    assert any("sha256sum" in call for call in run.calls)


# ── archive_week ─────────────────────────────────────────────────────────────


def test_archive_week_defers_when_hdd_busy(tmp_path):
    """Строка таблицы 2: hdd_busy → nas_jetson_nano-immich-hdd-copy.service —
    итог deferred с причиной, на HDD ничего, дни на SSD."""
    cfg, catalog, hot = _archive_case(tmp_path)
    run = _FakeRun(active_units=("nas_jetson_nano-immich-hdd-copy.service",))

    result = archive_week(cfg, catalog, "2026-W40", run)

    assert result["status"] == "deferred"
    assert isinstance(result["reason"], str) and result["reason"]
    assert any("nas_jetson_nano-immich-hdd-copy.service" in call
               for call in run.calls)
    assert not any("cp" in call for call in run.calls)  # копирование не начиналось
    assert _files_under(str(tmp_path / "hdd")) == []
    assert _days_present(hot, W40_PRESENT_DAYS) == W40_PRESENT_DAYS
    assert catalog.archives() == []


def test_archive_week_defers_when_hdd_not_alive(tmp_path):
    """Строка таблицы 3: hdd_alive → False — итог deferred с причиной,
    на HDD ничего, дни на SSD."""
    cfg, catalog, hot = _archive_case(tmp_path)
    run = _FakeRun(stat_ok=False)

    result = archive_week(cfg, catalog, "2026-W40", run)

    assert result["status"] == "deferred"
    assert isinstance(result["reason"], str) and result["reason"]
    assert not any("cp" in call for call in run.calls)
    assert _files_under(str(tmp_path / "hdd")) == []
    assert _days_present(hot, W40_PRESENT_DAYS) == W40_PRESENT_DAYS
    assert catalog.archives() == []


def test_archive_week_failed_on_sha256_mismatch_keeps_days(tmp_path):
    """Строка таблицы 4: sha256 на HDD не совпал — failed, дни на SSD целы,
    событие archiver/verify_failed, записи в catalog.archives() нет."""
    cfg, catalog, hot = _archive_case(tmp_path)
    run = _FakeRun(sha256_override="0" * 64)

    result = archive_week(cfg, catalog, "2026-W40", run)

    assert result["status"] == "failed"
    assert isinstance(result["reason"], str) and result["reason"]
    assert any("sha256sum" in call for call in run.calls)
    assert _days_present(hot, W40_PRESENT_DAYS) == W40_PRESENT_DAYS
    assert catalog.archives() == []

    events = catalog.events(0, 4102444800, source="archiver")  # до 2100 года
    assert [e["kind"] for e in events] == ["verify_failed"]
    assert events[0]["severity"] in ("warn", "crit")


def test_archive_week_ships_to_hdd_and_removes_week_days(tmp_path):
    """Строка таблицы 5: успех — <hdd_archive_root>/2026/blackbox-2026-W40.tar.xz
    и рядом .sha256; дни недели удалены с SSD, следующие дни целы; запись
    в catalog.archives() видна и через archive_for_day()."""
    cfg, catalog, hot = _archive_case(tmp_path)
    run = _FakeRun()

    result = archive_week(cfg, catalog, "2026-W40", run)

    assert result["status"] == "shipped"

    year_dir = os.path.join(cfg.hdd_archive_root, "2026")
    archive = os.path.join(year_dir, "blackbox-2026-W40.tar.xz")
    sha_file = archive + ".sha256"
    assert sorted(os.listdir(year_dir)) == [
        "blackbox-2026-W40.tar.xz", "blackbox-2026-W40.tar.xz.sha256"]
    with open(archive, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    with open(sha_file, "r", encoding="utf-8") as fh:
        sha_text = fh.read()
    assert digest in sha_text

    # дни W40 ушли с SSD (включая отсутствовавшие 28–30.09 — их и не было)…
    for day in W40_DAYS:
        assert not os.path.exists(os.path.join(hot, day)), day
    # …а дни после недели остались нетронутыми
    assert _days_present(hot, LATER_DAYS) == LATER_DAYS

    archives = catalog.archives()
    assert len(archives) == 1
    assert archives[0]["week"] == "2026-W40"
    assert archives[0]["sha256"] == digest
    assert archives[0]["verified"]
    assert catalog.archive_for_day("2026-10-02")["week"] == "2026-W40"


# ── prune_hdd ────────────────────────────────────────────────────────────────


def test_prune_hdd_deletes_only_archives_older_than_retention(tmp_path):
    """Строка таблицы 6: архив за 2025-W30 при today=2026-10-13 удалён
    (443 суток > 365), архив 2026-W02 — на месте (275 суток < 365);
    файл .sha256 уходит вместе со своим архивом."""
    hdd_root = tmp_path / "hdd" / "backups" / "blackbox"
    old_archive = hdd_root / "2025" / "blackbox-2025-W30.tar.xz"
    old_sha = hdd_root / "2025" / "blackbox-2025-W30.tar.xz.sha256"
    new_archive = hdd_root / "2026" / "blackbox-2026-W02.tar.xz"
    new_sha = hdd_root / "2026" / "blackbox-2026-W02.tar.xz.sha256"
    os.makedirs(str(old_archive.parent))
    os.makedirs(str(new_archive.parent))
    for path in (old_archive, old_sha, new_archive, new_sha):
        path.write_bytes(b"archive")

    prune_hdd(str(hdd_root), TODAY, 365)

    assert not old_archive.exists()
    assert not old_sha.exists()
    assert new_archive.exists()
    assert new_sha.exists()
