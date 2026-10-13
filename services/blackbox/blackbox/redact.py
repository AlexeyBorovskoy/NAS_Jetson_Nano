"""Маскирование секретов и русского текста семьи (OBS-1, задача 1, спецификация §4.3).

Два независимых правила:

- `mask_secrets` — токены, ключи, пароли, строки вида `<tenant>:<keyId>` —
  **всегда**, во всех контейнерах. Образцы ключевых слов — те же, что у
  `scripts/security/check_no_secrets.sh` (assignment/human_password): token
  и любое поле "*_token" (id_token, access_token, refresh_token, ...),
  secret, password/passwd, api[_-]?key, x-api-key, client_secret, Bearer,
  Authorization.
- `mask_family_text` — подряд идущие русские слова (от трёх) у контейнеров
  семьи — см. `redact_line`.

Python 3.6: только стандартная библиотека (`re`).
"""
import re

#: Плейсхолдеры вывода — дословно по таблице случаев задачи 1.
HIDDEN = "<скрыто>"
TEXT_HIDDEN = "<текст скрыт>"

# Имена ключей секретов. Длинные/обобщённые варианты — раньше коротких:
# `[\w-]*_token` ловит ЛЮБОЕ поле, оканчивающееся на "_token" (id_token,
# access_token, refresh_token, session_token, ...) — грабли проекта 20.09
# ответа OAuth были не только про id_token, а про всё семейство полей "*_token".
# Бэктрекинг жадного `[\w-]*` сам находит границу (напр. "access"+"_token"),
# поэтому отдельных алиасов на каждое поле не нужно. Голый "token" — ниже,
# для form/query стиля без подчёркивания (`token=...`).
_KEY_ALTS = (
    r"x-api-key|api[_-]?key|client[_-]?secret|[\w-]*_token|"
    r"token|secret|password|passwd"
)

# key=value / key: value (без кавычек или с одной парой кавычек у значения).
_KV_RE = re.compile(
    r"(?i)(" + _KEY_ALTS + r")(\s*[:=]\s*)([\"']?)[^\s&\"',]+(\3)"
)

# "key":"value" (JSON-журналы, в т.ч. грабли 20.09 — все поля "*_token").
_JSON_KV_RE = re.compile(
    r'(?i)"(' + _KEY_ALTS + r')"\s*:\s*"([^"]*)"'
)

# Authorization: Bearer <токен> — скрывается целиком вместе со схемой.
_AUTH_BEARER_RE = re.compile(r"(?i)(Authorization\s*:\s*)Bearer\s+\S+")

# Bearer <токен> без заголовка Authorization (отдельный образец спецификации).
_BEARER_RE = re.compile(r"(?i)\bBearer\s+\S+")

# "<tenant>:<keyId>" — пара длинных идентификаторов через двоеточие (ключи
# облачных хранилищ вида Cloud.ru AWS_ACCESS_KEY_ID). Короткие host:port
# ("host:8080") не попадают — второй отрезок у портов короче порога.
_TENANT_KEY_RE = re.compile(r"\b[0-9A-Za-z]{8,}:[0-9A-Za-z+/]{24,}\b")

# Три и более русских слова подряд. Разбираем построчно на лексемы (а не одним
# регулярным выражением с повторением): у повторения с необязательным разделителем
# между копиями движок способен раздвоить само слово на две "копии" через backtracking
# ("ошибка: диск" с порогом {3,} иначе ложно считался бы тремя словами — проверено
# при реализации задачи 1), а слово либо целиком русское, либо нет.
_CHUNK_RE = re.compile(r"\S+|\s+")
_NON_CYR_EDGE_RE = re.compile(r"^[^А-Яа-яЁё]+|[^А-Яа-яЁё]+$")


def _json_kv_repl(match):
    return '"' + match.group(1) + '":"' + HIDDEN + '"'


def _kv_repl(match):
    quote = match.group(3)
    return match.group(1) + match.group(2) + quote + HIDDEN + quote


def _auth_repl(match):
    return match.group(1) + HIDDEN


def mask_secrets(line):
    """Скрывает токены/ключи/пароли в строке. Строка без секретов — без изменений."""
    out = _JSON_KV_RE.sub(_json_kv_repl, line)
    out = _AUTH_BEARER_RE.sub(_auth_repl, out)
    out = _KV_RE.sub(_kv_repl, out)
    out = _BEARER_RE.sub("Bearer " + HIDDEN, out)
    out = _TENANT_KEY_RE.sub(HIDDEN, out)
    return out


def _is_cyr_word(chunk):
    """Лексема без пробелов — русское слово, если ядро (без краевой пунктуации/цифр) есть и целиком буквы."""
    core = _NON_CYR_EDGE_RE.sub("", chunk)
    return bool(core) and core.isalpha()


def _scan_cyr_run(chunks, flags, start):
    """От русского слова chunks[start] — (индекс конца пробега, число слов в нём).

    Пробег — слово, затем ноль-или-один пробельный разделитель и снова слово,
    и так далее; первый не-пробельный не-русский токен или конец списка его рвёт.
    """
    if not flags[start]:
        return start + 1, 0
    i = start + 1
    words = 1
    total = len(chunks)
    while i < total:
        if chunks[i].isspace():
            if i + 1 < total and flags[i + 1]:
                i += 2
                words += 1
                continue
            return i, words
        if not flags[i]:
            break
        i += 1
        words += 1
    return i, words


def mask_family_text(line):
    """Скрывает подряд идущие русские слова (от трёх) целиком как совпавший отрезок."""
    chunks = _CHUNK_RE.findall(line)
    flags = [not chunk.isspace() and _is_cyr_word(chunk) for chunk in chunks]
    out = []
    i = 0
    total = len(chunks)
    while i < total:
        end, words = _scan_cyr_run(chunks, flags, i)
        if words >= 3:
            out.append(TEXT_HIDDEN)
        else:
            out.append(chunks[i])
            end = i + 1
        i = end
    return "".join(out)


def redact_line(container, line, cfg):
    """Маскирование строки журнала контейнера `container` по правилам `cfg`.

    Секреты — всегда; русский текст — только для контейнеров из
    `cfg.family_containers` (список берётся из конфига, не зашит в код).
    """
    out = mask_secrets(line)
    if container in cfg.family_containers:
        out = mask_family_text(out)
    return out
