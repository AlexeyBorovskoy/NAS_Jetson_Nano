"""OBS-1, задача 4: дочитывание журналов контейнеров (json-file, ротация).

План — docs/superpowers/plans/2026-10-13-obs1-blackbox.ru.md (задача 4);
спецификация — docs/superpowers/specs/2026-10-13-blackbox-forensics-design.ru.md.

Файлы журналов подставные, в tmp_path; с живого хоста не читается ничего.
Состояние {имя: {"inode": ..., "offset": ...}} хранит вызывающий (в бою —
Catalog через set_cursor("logs", json)); LogTailer получает тот же словарь
и обновляет его на месте, поэтому состояние обязано переживать json-сериализацию.

Возвращаемые строки — значения поля "log" как есть, вместе с завершающим
переводом строки: такими их отдаёт Docker json-file, такими их ждут
split_health и запись в <день>/containers/<имя>.log.gz (задача 7).
"""
import json
import os

from blackbox.sources.container_logs import LogTailer, split_health, tail_lines

TIME = "2026-10-13T03:20:01.000000000Z"


def _json_line(text, stream="stdout"):
    """Одна физическая строка файла json-file: JSON-объект и перевод строки."""
    return json.dumps({"log": text, "stream": stream, "time": TIME}) + "\n"


def _payload(texts):
    return b"".join(_json_line(t).encode("utf-8") for t in texts)


def _write(path, texts):
    with open(path, "wb") as fh:
        fh.write(_payload(texts))


def _append(path, texts):
    with open(path, "ab") as fh:
        fh.write(_payload(texts))


def test_tailer_reads_initial_batch_and_keeps_position(tmp_path):
    """Строка таблицы: 3 строки, затем дописали 2 — второй вызов ровно 2."""
    state = {}
    tailer = LogTailer(state)
    path = str(tmp_path / "stt.log")
    texts = ["one\n", "two\n", "three\n"]
    _write(path, texts)

    assert tailer.read_new("homecloud_stt", path) == texts
    entry = state["homecloud_stt"]
    assert "inode" in entry and "offset" in entry
    assert json.loads(json.dumps(state)) == state  # состояние уезжает в курсор catalog.db

    _append(path, ["four\n", "five\n"])
    got = tailer.read_new("homecloud_stt", path)
    assert len(got) == 2
    assert got == ["four\n", "five\n"]
    assert tailer.read_new("homecloud_stt", path) == []  # прочитанное не дублируется


def test_tailer_partial_last_line_waits(tmp_path):
    """Строка таблицы: неполная последняя строка (без \\n) не потребляется,
    пока не допишется."""
    tailer = LogTailer({})
    path = str(tmp_path / "stt.log")
    complete = _payload(["one\n", "two\n"])
    partial = _json_line("three\n")[:-1]  # JSON дописан, перевод строки — нет
    with open(path, "wb") as fh:
        fh.write(complete + partial.encode("utf-8"))

    assert tailer.read_new("homecloud_stt", path) == ["one\n", "two\n"]

    with open(path, "ab") as fh:
        fh.write(b"\n")  # строка наконец дописана
    assert tailer.read_new("homecloud_stt", path) == ["three\n"]
    assert tailer.read_new("homecloud_stt", path) == []


def test_tailer_rotation_new_inode(tmp_path):
    """Фокус ревью №4: файл заменён (другой inode), новый короче — строки нового
    файла возвращаются с начала, без дублей и потерь."""
    tailer = LogTailer({})
    path = str(tmp_path / "immich.log")
    _write(path, ["old one\n", "old two\n", "old three\n"])
    assert len(tailer.read_new("homecloud_immich_server", path)) == 3

    rotated = tmp_path / "immich.log.1"
    _write(str(rotated), ["fresh one\n", "fresh two\n"])
    os.replace(str(rotated), path)  # на месте старого файла — новый, короче

    assert tailer.read_new("homecloud_immich_server", path) == ["fresh one\n",
                                                                "fresh two\n"]
    assert tailer.read_new("homecloud_immich_server", path) == []


def test_tailer_rotated_longer_file_reads_from_zero(tmp_path):
    """Ротация, у которой новый файл длиннее старого смещения: сбросить смещение
    обязан именно признак другого inode («размер меньше смещения» такой случай
    не ловит). inode в состоянии подменяем заведомо чужим (~значение), чтобы
    тест не зависел от поведения файловой системы (Windows и Linux)."""
    state = {}
    tailer = LogTailer(state)
    path = str(tmp_path / "nc.log")
    _write(path, ["old one\n", "old two\n"])
    assert len(tailer.read_new("homecloud_nextcloud", path)) == 2

    fresh = ["new one\n", "new two\n", "new three\n", "new four\n", "new five\n"]
    _write(path, fresh)  # перезапись на месте; inode мог остаться прежним, поэтому:
    state["homecloud_nextcloud"]["inode"] = ~os.stat(path).st_ino

    assert tailer.read_new("homecloud_nextcloud", path) == fresh


def test_tailer_truncated_same_inode_reads_from_zero(tmp_path):
    """Строка таблицы: усечение (тот же inode, размер меньше смещения) — чтение с 0."""
    tailer = LogTailer({})
    path = str(tmp_path / "api.log")
    _write(path, ["before one\n", "before two\n", "before three\n"])
    assert len(tailer.read_new("homecloud_nasa_api", path)) == 3

    _write(path, ["after\n"])
    assert tailer.read_new("homecloud_nasa_api", path) == ["after\n"]
    assert tailer.read_new("homecloud_nasa_api", path) == []


def test_tailer_max_bytes_caps_read(tmp_path):
    """За вызов читается не больше max_bytes: длинный хвост дочитывается
    следующей порцией, а не целиком в память (журналы бывают большими)."""
    tailer = LogTailer({})
    path = str(tmp_path / "gw.log")
    texts = ["line 1\n", "line 2\n", "line 3\n", "line 4\n", "line 5\n"]
    _write(path, texts)
    cap = len(_json_line(texts[0]).encode("utf-8")) * 2  # ровно две полные строки

    assert tailer.read_new("homecloud_llm_gateway", path, max_bytes=cap) == texts[:2]
    assert tailer.read_new("homecloud_llm_gateway", path) == texts[2:]


HEALTH_LINES = [
    '172.17.0.1 - - [13/Oct/2026:03:20:01 +0000] "GET /healthcheck HTTP/1.1" 200 15\n',
    '172.17.0.1 - - [13/Oct/2026:03:20:02 +0000] "GET /healthcheck HTTP/1.1" 200 15\n',
    '172.17.0.1 - - [13/Oct/2026:03:20:03 +0000] "GET /health HTTP/1.1" 200 5\n',
    '172.17.0.1 - - [13/Oct/2026:03:20:04 +0000] "GET /status.php HTTP/1.1" 200 22\n',
]
CHAT_LINE = '172.17.0.1 - - [13/Oct/2026:03:20:05 +0000] "POST /v1/chat HTTP/1.1" 200 512\n'


def test_split_health_counts_access_lines():
    """Строка таблицы: 4 строки проверок с кодом 200 и 1 чужая —
    kept = 1 строка, health_count = 4."""
    kept, health_count = split_health(HEALTH_LINES + [CHAT_LINE])
    assert kept == [CHAT_LINE]
    assert health_count == 4


def test_split_health_keeps_non_200():
    """Интерфейс: счётчик ест проверки здоровья только с кодом 200."""
    failed = '172.17.0.1 - - [13/Oct/2026:03:20:06 +0000] "GET /healthcheck HTTP/1.1" 500 0\n'
    kept, health_count = split_health([failed])
    assert kept == [failed]
    assert health_count == 0


def test_tail_lines_returns_last_lines(tmp_path):
    """Строка таблицы: tail_lines(n=2) на 5 строках — две последние."""
    path = str(tmp_path / "immich.log")
    texts = ["entry one\n", "entry two\n", "entry three\n", "entry four\n",
             "entry five\n"]
    _write(path, texts)

    assert tail_lines(path, n=2) == ["entry four\n", "entry five\n"]


def test_tail_lines_bounded_memory_for_large_file(tmp_path):
    """Правка круга 1 ревью (КРИТИЧНОЕ): файл в несколько МБ — tail_lines
    читает блоками с конца (`_read_tail_bytes`), а не целиком через
    `fh.readlines()` (OOM-ловушка ровно в момент аварии контейнера, когда
    журнал может весить сотни МБ при пределе сборщика 64 МБ). Возвращены
    ровно последние n строк и на многотысячном файле (несколько МБ,
    десятки блоков по умолчанию)."""
    path = str(tmp_path / "big.log")
    total_lines = 50000
    texts = ["line %06d\n" % i for i in range(total_lines)]
    _write(path, texts)
    assert os.path.getsize(path) > 2 * 1024 * 1024  # действительно «несколько МБ»

    assert tail_lines(path, n=5) == texts[-5:]


def test_tail_lines_handles_line_split_across_block_boundary(tmp_path):
    """Правка круга 1 ревью (КРИТИЧНОЕ): строка, которую граница блока
    режет ровно посередине, — не теряется и не дублируется. `block_size`
    задан заведомо меньше одной физической строки, чтобы граница блока
    обязательно прошла внутри какой-то строки."""
    path = str(tmp_path / "boundary.log")
    texts = ["aaa\n", "bbb\n", "ccc\n", "ddd\n", "eee\n"]
    _write(path, texts)

    assert tail_lines(path, n=3, block_size=10) == texts[-3:]


def test_tail_lines_file_shorter_than_one_block(tmp_path):
    """Правка круга 1 ревью (КРИТИЧНОЕ): файл короче одного блока читается
    весь, без ошибки — ровно как раньше, просто без лишнего чтения."""
    path = str(tmp_path / "short.log")
    texts = ["only one\n", "and two\n"]
    _write(path, texts)

    assert tail_lines(path, n=10) == texts


def test_tail_lines_missing_file_returns_empty(tmp_path):
    """Правка круга 1 ревью (ВАЖНОЕ 2): файл исчез между вызовами
    (ротация/удаление под ногами) — [], как и LogTailer.read_new, без
    исключения наружу."""
    path = str(tmp_path / "gone.log")
    assert tail_lines(path, n=5) == []
