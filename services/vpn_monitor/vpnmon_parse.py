"""Учёт VPN и нагрузки VPS: разбор сырых данных (спецификация 2026-10-04 §5–6).

Только чистые функции: на вход текст, на выход числа и словари. Ни файлов, ни процессов.
"""
import json

SECTION_MARK = "@@"
# От самого точного к общему: строка «System is powering down (hypervisor initiated
# shutdown).» содержит два маркера, а нужен первый.
SHUTDOWN_MARKERS = (
    "hypervisor initiated shutdown",
    "Power key pressed",
    "System is rebooting",
    "System is powering down",
)


def split_sections(text, count):
    """Вывод постоянного скрипта чтения → `count` частей, разделённых строками «@@»."""
    parts = [[]]
    for line in text.splitlines():
        if line.strip() == SECTION_MARK:
            parts.append([])
        else:
            parts[-1].append(line)
    if len(parts) != count:
        raise ValueError("ожидалось %d секций, получено %d" % (count, len(parts)))
    return ["\n".join(part) for part in parts]


def parse_key_values(text):
    """Вывод `wg show <if> <поле>`: «ключ значение…» → {ключ: [значения]}."""
    out = {}
    for line in text.splitlines():
        fields = line.split()
        if len(fields) >= 2:
            out[fields[0]] = fields[1:]
    return out


def parse_peers(allowed_text, transfer_text, handshake_text):
    """Три поля `wg show` → {ключ: {vpn_ip, rx, tx, handshake}}.

    rx — получено сервером от клиента (отдача пользователя), tx — отправлено клиенту
    (загрузка пользователя); handshake — секунды эпохи, 0 = не было с запуска интерфейса.
    """
    transfer = parse_key_values(transfer_text)
    handshakes = parse_key_values(handshake_text)
    peers = {}
    for key, ips in parse_key_values(allowed_text).items():
        rx, tx = (transfer.get(key) or ["0", "0"])[:2]
        first_ip = ips[0].split("/")[0]
        peers[key] = {
            "vpn_ip": None if first_ip == "(none)" else first_ip,
            "rx": int(rx),
            "tx": int(tx),
            "handshake": int((handshakes.get(key) or ["0"])[0]),
        }
    return peers


def parse_clients_table(text):
    """`clientsTable` Amnezia (JSON-список) → {ключ: имя}. Ошибка разбора — ValueError."""
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("clientsTable: ожидался список")
    names = {}
    for entry in data:
        user = entry.get("userData") if isinstance(entry, dict) else None
        name = user.get("clientName") if isinstance(user, dict) else None
        if name and entry.get("clientId"):
            names[entry["clientId"]] = str(name).strip()
    return names


def parse_names_conf(text):
    """`names.conf`: строки «префикс_ключа = имя» → [(префикс, имя)]; # — комментарий."""
    pairs = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        prefix, name = (part.strip() for part in line.split("=", 1))
        if len(prefix) >= 6 and name:
            pairs.append((prefix, name))
    return pairs


def _name_from_conf(key, conf):
    for prefix, name in conf:
        if key.startswith(prefix):
            return name
    return None


def resolve_names(keys, table, conf):
    """Имя каждого пира: clientsTable → names.conf → «ключ abcd1234».

    table=None (clientsTable не прочитан): только имена из names.conf; остальных
    ключей в ответе нет — хранилище оставит им прежние имена.
    """
    out = {}
    for key in keys:
        name = table.get(key) if table is not None else None
        name = name or _name_from_conf(key, conf)
        if name is None and table is not None:
            name = "ключ " + key[:8]
        if name is not None:
            out[key] = name
    return out


def parse_cpu(stat_text):
    """Строка `cpu` из /proc/stat → (занято, всего) в тиках; iowait считается простоем."""
    for line in stat_text.splitlines():
        if line.startswith("cpu "):
            ticks = [int(x) for x in line.split()[1:9]]
            idle = ticks[3] + ticks[4]
            return sum(ticks) - idle, sum(ticks)
    raise ValueError("в /proc/stat нет строки cpu")


def parse_btime(stat_text):
    """Время загрузки (секунды эпохи) из /proc/stat."""
    for line in stat_text.splitlines():
        if line.startswith("btime "):
            return int(line.split()[1])
    raise ValueError("в /proc/stat нет btime")


def parse_mem(meminfo_text):
    """/proc/meminfo → (занято, всего) в байтах; занято = MemTotal − MemAvailable."""
    vals = {}
    for line in meminfo_text.splitlines():
        name, _, rest = line.partition(":")
        if name in ("MemTotal", "MemAvailable"):
            vals[name] = int(rest.split()[0]) * 1024
    if len(vals) != 2:
        raise ValueError("в /proc/meminfo нет MemTotal/MemAvailable")
    return vals["MemTotal"] - vals["MemAvailable"], vals["MemTotal"]


def parse_load1(loadavg_text):
    """Первое число /proc/loadavg."""
    return float(loadavg_text.split()[0])


def parse_net_dev(text, iface):
    """/proc/net/dev → (rx_bytes, tx_bytes) интерфейса; None, если его нет."""
    for line in text.splitlines():
        name, sep, rest = line.partition(":")
        if sep and name.strip() == iface:
            fields = rest.split()
            return int(fields[0]), int(fields[8])
    return None


def parse_default_iface(route_text):
    """/proc/net/route → интерфейс маршрута по умолчанию; None, если его нет."""
    for line in route_text.splitlines()[1:]:
        fields = line.split()
        if len(fields) > 1 and fields[1] == "00000000":
            return fields[0]
    return None


def parse_inspect(text):
    """Вывод `docker inspect -f '{{.State.Pid}}|{{.State.StartedAt}}|{{.State.Running}}'`."""
    pid, started, running = text.strip().split("|")
    return int(pid), started, running == "true"


def shutdown_reason(journal_text):
    """Причина конца прошлой загрузки по её последним строкам журнала; None — не найдена."""
    for marker in SHUTDOWN_MARKERS:
        if marker in journal_text:
            return marker
    return None
