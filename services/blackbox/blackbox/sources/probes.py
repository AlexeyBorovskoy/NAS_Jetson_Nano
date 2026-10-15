"""Пробы сети и монтирований (OBS-1, задача 5, спецификация §4.1, цикл probes).

Шлюз, DNS, туннель VPS, прокси Telegram — это так/нет сети; монтирования
SSD/HDD — отдельная проба процессом (`MountProbe`), потому что зависший
`ntfs-3g` на `/mnt/hdd2tb` держит обратившийся к пути процесс в D-state
навсегда (живой случай 13–14.10, CLAUDE.md). Правило: в СВОЁМ процессе к
такому пути не обращаться никогда — только `timeout 5 stat -f <path>` в
дочернем, и второй не запускается, пока первый не вернулся.

Внешние процессы и сеть — только через параметры-заменители (`run`, `popen`),
как в интерфейсах задания; ни один тест не трогает настоящую сеть/диск.

Python 3.6: только стандартная библиотека, без f-строк с `=`, без
`dataclasses`, без `:=`.
"""
import os
import socket
import struct
import subprocess

#: Состояние TCP-соединения ESTABLISHED, как оно печатается в /proc/net/tcp.
_TCP_ESTABLISHED = "01"

#: Порт 22 (SSH-туннель до VPS) в формате /proc/net/tcp (hex, big-endian).
_PORT_22_HEX = "0016"


def _mount_event(kind, subject, now, severity="warn", detail=None, **extra):
    """Собирает событие пробы монтирования (контракт `event`, план «Контракты данных»)."""
    event = {
        "ts": now,
        "source": "probe",
        "kind": kind,
        "subject": subject,
        "severity": severity,
        "detail": detail or {},
    }
    event.update(extra)
    return event


class MountProbe(object):
    """Однопроходная проверка монтирования: один процесс за раз.

    `poll(now)` вызывается периодически (цикл probes, план — 60 с). Пока
    предыдущий `timeout 5 stat -f <path>` не вернулся, новый не запускается —
    иначе зависший `ntfs-3g` копил бы по одному процессу на опрос. Событие
    `mount_hung` отдаётся ровно один раз на эпизод зависания (не на каждый
    опрос) — фокус ревью №1 (план задачи 5).
    """

    def __init__(self, path, timeout_s=5, popen=subprocess.Popen):
        self.path = path
        self.timeout_s = timeout_s
        self._popen = popen
        self._process = None
        self._start = None
        self._hung_reported = False

    def _launch(self, now):
        cmd = ["timeout", str(self.timeout_s), "stat", "-f", self.path]
        self._process = self._popen(cmd, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
        self._start = now
        self._hung_reported = False

    def _finish(self, returncode, now):
        """Процесс вернулся: собирает mount_error/mount_recovered (или ничего)."""
        was_hung = self._hung_reported
        self._process = None
        self._start = None
        self._hung_reported = False
        if returncode != 0:
            return _mount_event("mount_error", self.path, now,
                                 detail={"returncode": returncode})
        if was_hung:
            return _mount_event("mount_recovered", self.path, now, severity="info")
        return None

    def poll(self, now):
        """Событие пробы (`dict`) или `None`; запускает новый процесс при надобности."""
        if self._process is None:
            self._launch(now)
            return None
        returncode = self._process.poll()
        if returncode is not None:
            return self._finish(returncode, now)
        elapsed = now - self._start
        if elapsed >= self.timeout_s + 5 and not self._hung_reported:
            self._hung_reported = True
            return _mount_event("mount_hung", self.path, now, since=self._start)
        return None


# ── Шлюз, DNS, TCP ───────────────────────────────────────────────────────────

def _default_gateway_ip(route_path="/proc/net/route"):
    """IPv4 шлюза по умолчанию из `/proc/net/route`, или `None`."""
    try:
        with open(route_path, "r", encoding="utf-8") as stream:
            lines = stream.readlines()
    except OSError:
        return None
    for line in lines[1:]:
        fields = line.split()
        if len(fields) >= 3 and fields[1] == "00000000":
            packed = struct.pack("<I", int(fields[2], 16))
            return socket.inet_ntoa(packed)
    return None


def probe_gateway(run):
    """True, если шлюз по умолчанию отвечает на `ping -c1 -W1`.

    Адрес — из `/proc/net/route`; если определить не удалось (нет записи по
    умолчанию), используется псевдо-имя `_gateway`. `run` — замена
    `subprocess.run`, подменяется в тестах.
    """
    target = _default_gateway_ip() or "_gateway"
    completed = run(["ping", "-c1", "-W1", target],
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return completed.returncode == 0


def probe_dns(name="api.telegram.org", timeout=3):
    """True, если имя `name` разрешается за `timeout` секунд."""
    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout)
    try:
        socket.getaddrinfo(name, None)
        return True
    except socket.error:
        return False
    finally:
        socket.setdefaulttimeout(old_timeout)


def probe_tcp(host, port, timeout=3):
    """True, если TCP-соединение к `(host, port)` устанавливается за `timeout` с."""
    try:
        conn = socket.create_connection((host, port), timeout=timeout)
    except socket.error:
        return False
    conn.close()
    return True


# ── Туннель VPS: /proc/net/tcp ───────────────────────────────────────────────

def _ipv4_hex(ip):
    """IPv4-строка -> 8 hex-символов, как адрес в `/proc/net/tcp`."""
    packed = socket.inet_aton(ip)
    value = struct.unpack("<I", packed)[0]
    return "%08X" % value


def _tcp_lines(proc_root):
    """Строки `/proc/net/tcp` без заголовка, или `[]`, если файла нет."""
    path = os.path.join(proc_root, "net", "tcp")
    try:
        with open(path, "r", encoding="utf-8") as stream:
            lines = stream.readlines()
    except OSError:
        return []
    return lines[1:]


def probe_tunnel(proc_root, vps_hosts):
    """True, если есть ESTABLISHED-соединение к одному из `vps_hosts` на порту 22."""
    targets = set(_ipv4_hex(host) for host in vps_hosts)
    for line in _tcp_lines(proc_root):
        fields = line.split()
        if len(fields) < 4:
            continue
        addr, sep, port = fields[2].partition(":")
        if not sep:
            continue
        if addr in targets and port == _PORT_22_HEX and fields[3] == _TCP_ESTABLISHED:
            return True
    return False


# ── Событие при смене состояния пробы ────────────────────────────────────────

def probes_event(results, prev):
    """Список событий `<имя>_down`/`<имя>_up` только для проб, сменивших состояние.

    `results`/`prev` — `{"gateway": bool, "dns": bool, "tunnel": bool,
    "tg_proxy": bool, ...}`; проба без записи в `prev` (первый опрос) событий
    не даёт — отсутствует база для сравнения.
    """
    events = []
    for name, value in results.items():
        was = prev.get(name)
        if was is None or value == was:
            continue
        suffix = "down" if value is False else "up"
        severity = "warn" if value is False else "info"
        events.append({
            "kind": name + "_" + suffix,
            "subject": name,
            "severity": severity,
            "detail": {"value": value, "prev": was},
        })
    return events
