#!/usr/bin/env python3
"""D2 — алерт владельцу в Telegram после аварийной загрузки Jetson.

ЗАЧЕМ. ИБП отложен, копии архива 1,4 ТБ нет и не будет — риски приняты
владельцем 2026-09-19 (CLAUDE.md, решения D1/D3). Единственная оставшаяся
защита от провала питания — узнать о нём СРАЗУ, а не задним числом. Именно
так и было 2026-08-17: Jetson перезагрузился аппаратно, и заметили это
только разбирая логи через несколько дней.

ЧТО СЧИТАЕТСЯ "нештатной" загрузкой. Смотрим на согласии с CLAUDE.md
(раздел «Грабли», точка про три признака): штатная остановка ВСЕГДА
оставляет парную запись `shutdown` в `last -x` непосредственно перед
записью `reboot` этой загрузки. Если такой записи нет — молчать нельзя
(«Штатная — молчит» относится только к ДОКАЗАННО штатной остановке;
неопределённость — это НЕ штатность, и на ней тоже нужно говорить,
честно называя её неопределённостью). Ramoops и `dmesg PMC reset source`
идут в сообщение как дополнительные признаки, но НЕ решают дилемму
"провал питания или PMIC-watchdog" — CLAUDE.md прямо фиксирует, что этими
данными они неразличимы, и врать про причину нельзя (правило проекта
"не выдумывать причину").

Доставка — Telegram, не Talk: Jetson не достаёт api.telegram.org напрямую,
путь наружу — SOCKS через `nas_jetson_nano-tg-socks.service`
(`ssh -D 172.17.0.1:1080` на VPS, см. тот юнит и
docs/superpowers/specs/2026-09-19-telegram-family-bot-design.md). Отправка
идёт локальным `curl --socks5-hostname`, а не через питоновские SOCKS-либы
(на Jetson их нет, а curl уже используется другими скриптами проекта).

Требование 5 (SOCKS может быть ещё не поднят сразу после боевой загрузки):
несколько попыток с паузой; если и это не помогло — сообщение НЕ теряется
молча: пишется в pending-файл и в journal (stderr, ненулевой код выхода —
юнит перезапустит себя по Restart=on-failure и попробует снова).

Требование 4 (не дублировать при перезапуске юнита): состояние хранит
boot_id текущей загрузки (/proc/sys/kernel/random/boot_id, меняется на
каждой загрузке ядра) и считается «обработанным» только когда для ЭТОГО
boot_id либо подтверждена штатность, либо алерт реально доставлен.

Запуск на устройстве — systemd-юнит `nas_jetson_nano-boot-alert.service`
(oneshot при старте). Ручная проверка канала: `--test`. Повторный прогон
для того же boot_id без сброса состояния: `--force`.
"""
import glob
import json
import os
import re
import subprocess
import sys
import time

# Раскладка хоста — единая точка правды (scripts/lib/layout.sh, NAS-STO-001).
for _lib in (os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"),
             "/usr/local/lib/nas_jetson_nano"):
    if os.path.isfile(os.path.join(_lib, "nas_layout.py")):
        sys.path.insert(0, _lib)
        break
import nas_layout  # noqa: E402

LAYOUT = nas_layout.resolve()
ENV_FILE = LAYOUT["NAS_ENV_FILE"]
STATE_FILE = os.path.join(LAYOUT["NAS_STATE_DIR"], "boot-alert-state.json")
PENDING_FILE = os.path.join(LAYOUT["NAS_STATE_DIR"], "boot-alert-pending.json")

TELEGRAM_API = "https://api.telegram.org"
RAMOOPS_PRIMARY = "/sys/fs/pstore/console-ramoops-0"
RAMOOPS_GLOB = "/sys/fs/pstore/console-ramoops-*"
STAT_PATH = "/proc/stat"
BOOT_ID_PATH = "/proc/sys/kernel/random/boot_id"

DEFAULT_RETRY_ATTEMPTS = 5
DEFAULT_RETRY_DELAY_SEC = 20


# ── чтение конфигурации (родня read_env() из nas_jetson_nano-talk-alert.py) ────

def read_env(path, key, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith(key + "="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return default


# ── разбор `last -x`: была ли прошлая остановка штатной ────────────────────────

_RECORD_RE = re.compile(r"^(reboot|shutdown)\s+system\s+(boot|down)\b")


def classify_shutdown(last_x_text):
    """Штатная остановка = запись `shutdown`/`system down` непосредственно
    ПЕРЕД записью `reboot`/`system boot` этой загрузки (записи в `last -x`
    идут от новых к старым). Регрессия 2026-08-17 (CLAUDE.md, точка 23.08
    §3.1): после `reboot` этой загрузки шла сразу ЕЩЁ ОДНА `reboot` —
    записи `shutdown` между ними не было вовсе.

    Возвращает ("orderly"|"abnormal"|"unknown", текст-объяснение).
    "unknown" — намеренно НЕ трактуется как штатность: если сравнивать не с
    чем (одна запись, пустой или неразбираемый вывод), правило "штатная —
    молчит" не выполнено, и молчать нельзя."""
    records = [m.group(1) for m in (_RECORD_RE.match(line)
                                    for line in (last_x_text or "").splitlines())
              if m]
    if not records or records[0] != "reboot":
        return "unknown", "не удалось разобрать вывод last -x"
    if len(records) < 2:
        return "unknown", "в wtmp только одна запись о загрузке — сравнивать не с чем"
    if records[1] == "shutdown":
        return "orderly", "перед этой загрузкой есть запись об штатном выключении (shutdown)"
    return "abnormal", "перед этой загрузкой нет записи об штатном выключении — следом идёт ещё одна reboot"


# ── ramoops: оставила бы паника трассу ──────────────────────────────────────────

_PANIC_RE = re.compile(r"Kernel panic|Oops[: ]|BUG:|Call trace", re.I)


def classify_ramoops(content):
    """Паника ядра оставила бы трассу в ramoops (буфер в ОЗУ, переживает
    сброс) — один из трёх согласованных признаков (CLAUDE.md, точка 23.08).
    Пустой/отсутствующий файл НЕ противоречит гипотезе об аппаратном
    сбросе; непустой файл с явными маркерами паники говорит скорее о
    программном сбое ядра — но и это не точный диагноз, только сигнал."""
    if content is None:
        return False, "файл отсутствует — трассы паники нет"
    if not content.strip():
        return False, "файл пуст — трассы паники нет"
    if _PANIC_RE.search(content):
        return True, "содержит признаки паники ядра (Kernel panic/Oops/BUG)"
    return False, "не пуст, но признаков паники ядра не найдено"


# ── dmesg: PMC reset source ─────────────────────────────────────────────────────

_PMC_RE = re.compile(r"PMC reset source:\s*(\S+)")


def parse_pmc_reset_source(dmesg_text):
    """У Tegra `TEGRA_POWER_ON_RESET` — ОДНО И ТО ЖЕ значение и при провале
    питания, и при срабатывании PMIC-watchdog (CLAUDE.md: "различить их
    этими данными нельзя"). Функция только достаёт значение, не решает,
    какая из причин это была."""
    m = _PMC_RE.search(dmesg_text or "")
    if not m:
        return None, "строка 'PMC reset source' не найдена в dmesg"
    source = m.group(1)
    return source, "PMC reset source: %s" % source


# ── текст алерта: честная формулировка, причина не выдумывается ────────────────

def build_alert_text(boot_time_str, shutdown_status, shutdown_detail,
                     ramoops_panic, ramoops_detail, pmc_source, pmc_detail):
    lines = [
        u"⚠️ Jetson загрузился без подтверждённого штатного выключения.",
        u"Загрузка: %s" % boot_time_str,
        u"",
        u"Признаки (CLAUDE.md, все три сразу, ни один не решает вопрос в одиночку):",
        u"• last -x: %s" % shutdown_detail,
        u"• ramoops (%s): %s" % (RAMOOPS_PRIMARY, ramoops_detail),
        u"• dmesg: %s" % pmc_detail,
        u"",
    ]
    if ramoops_panic:
        lines.append(
            u"В ramoops есть признаки паники ядра — вероятнее программный сбой, "
            u"чем провал питания, но однозначно утверждать нельзя.")
    elif pmc_source == "TEGRA_POWER_ON_RESET":
        lines.append(
            u"Провал питания и срабатывание PMIC-watchdog дают на Tegra "
            u"ОДИНАКОВУЮ картину по этим признакам — различить их невозможно. "
            u"Это неизвестная причина, а не удобная версия.")
    else:
        lines.append(
            u"Причину нештатной загрузки по этим трём признакам установить "
            u"не удалось — записываю как неизвестную.")
    return u"\n".join(lines)


# ── Telegram: доставка через curl + SOCKS, владельцу, с повторами ──────────────

def parse_telegram_users(users_str):
    """`user_id:логин user_id:логин ...` — тот же формат, что в
    services/nas_jetson_nano-api/app/telegram_bot.py (TgApi/parse_users),
    здесь не импортируется намеренно: это отдельный host-скрипт на
    Python 3.6, а бот живёт в контейнере на Python 3.9+."""
    users = {}
    for part in (users_str or "").split():
        uid, sep, login = part.partition(":")
        if sep and uid.lstrip("-").isdigit() and login:
            users[login] = int(uid)
    return users


def resolve_owner_chat_id(users_str, owner_login):
    """Личный chat_id владельца в Telegram равен его user_id (стандартное
    поведение приватного чата с ботом)."""
    return parse_telegram_users(users_str).get(owner_login)


def send_telegram(token, chat_id, text, proxy=None, api_base=TELEGRAM_API,
                  run=None, timeout=20, curl_bin="curl"):
    """Один запрос sendMessage через curl. `run` подменяется в тестах —
    никакой реальной сети в tests/unit."""
    run = run or subprocess.run
    cmd = [curl_bin, "-sS", "--max-time", str(timeout)]
    if proxy:
        # curl принимает host:port, а не схему socks5://... — тот же формат,
        # что TELEGRAM_PROXY=socks5://172.17.0.1:1080 в config/.env.
        host_port = proxy.split("://", 1)[-1]
        cmd += ["--socks5-hostname", host_port]
    cmd += ["-X", "POST", "%s/bot%s/sendMessage" % (api_base, token),
            "-d", "chat_id=%s" % chat_id, "--data-urlencode", "text@-"]
    try:
        proc = run(cmd, input=text, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                  universal_newlines=True, timeout=timeout + 10)
    except Exception as exc:  # таймаут curl, PermissionError и т.п.
        raise RuntimeError("curl не выполнен: %s" % exc)
    if proc.returncode != 0:
        raise RuntimeError("curl вышел с кодом %d: %s"
                           % (proc.returncode, (proc.stderr or "").strip()))
    try:
        data = json.loads(proc.stdout)
    except ValueError:
        raise RuntimeError("Telegram вернул не JSON: %s" % (proc.stdout or "")[:200])
    if not data.get("ok"):
        raise RuntimeError("Telegram API: %s" % data.get("description", data))
    return data.get("result")


def send_with_retries(token, chat_id, text, proxy=None,
                      attempts=DEFAULT_RETRY_ATTEMPTS,
                      delay_sec=DEFAULT_RETRY_DELAY_SEC, run=None, sleep=time.sleep):
    """Требование 5: SOCKS-туннель (`nas_jetson_nano-tg-socks.service`)
    может быть ещё не поднят сразу после боевой загрузки. Несколько попыток
    с паузой — прежде чем признать доставку сорванной."""
    last_err = None
    for i in range(attempts):
        try:
            send_telegram(token, chat_id, text, proxy=proxy, run=run)
            return True, None
        except Exception as exc:
            last_err = str(exc)
            if i < attempts - 1:
                sleep(delay_sec)
    return False, last_err


# ── состояние: не дублировать алерт при перезапуске юнита ──────────────────────

def _atomic_write_json(path, data):
    d = os.path.dirname(path)
    if d:
        try:
            os.makedirs(d)
        except OSError:
            pass
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def load_state(path):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_state(path, state):
    _atomic_write_json(path, state)


def mark_resolved(boot_id, alerted):
    return {"boot_id": boot_id, "resolved": True, "alerted": bool(alerted), "ts": time.time()}


def already_handled(state, boot_id):
    """Требование 4. "Обработано" — либо загрузка признана штатной, либо
    алерт для НЕЁ реально доставлен. Если отправка сорвалась, boot_id не
    отмечается resolved, и следующий запуск юнита (Restart=on-failure или
    ручной) попробует снова — а не молчит навсегда."""
    return bool(boot_id) and state.get("boot_id") == boot_id and state.get("resolved") is True


def write_pending(path, text, error, boot_id):
    """Требование 5: сообщение не теряется молча, даже если Telegram
    так и остался недоступен после всех попыток."""
    _atomic_write_json(path, {"boot_id": boot_id, "text": text, "error": error, "ts": time.time()})


# ── сбор сырых данных с системы (не покрыто unit-тестами — тонкие обёртки) ─────

def get_boot_time_str(stat_path=STAT_PATH):
    try:
        with open(stat_path, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("btime "):
                    ts = int(line.split()[1])
                    return time.strftime("%d.%m.%Y %H:%M:%S", time.localtime(ts))
    except (OSError, ValueError, IndexError):
        pass
    return "время загрузки не определено (%s недоступен)" % stat_path


def get_boot_id(path=BOOT_ID_PATH):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read().strip() or None
    except OSError:
        return None


def _read_last_x():
    try:
        out = subprocess.run(["last", "-x"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             universal_newlines=True, timeout=15)
        return out.stdout or ""
    except Exception:
        return ""


def _read_ramoops():
    candidates = [RAMOOPS_PRIMARY]
    try:
        candidates += sorted(glob.glob(RAMOOPS_GLOB))
    except OSError:
        pass
    for p in candidates:
        if os.path.isfile(p):
            try:
                with open(p, encoding="utf-8", errors="replace") as fh:
                    return fh.read()
            except OSError:
                return None
    return None


def _read_dmesg():
    try:
        out = subprocess.run(["dmesg"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             universal_newlines=True, timeout=15)
        return out.stdout or ""
    except Exception:
        return ""


# ── сквозная чистая сборка: три сырых текста -> решение + текст алерта ─────────

def gather_signals(last_x_text, ramoops_content, dmesg_text, boot_time_str):
    shutdown_status, shutdown_detail = classify_shutdown(last_x_text)
    ramoops_panic, ramoops_detail = classify_ramoops(ramoops_content)
    pmc_source, pmc_detail = parse_pmc_reset_source(dmesg_text)
    orderly = shutdown_status == "orderly"
    text = None
    if not orderly:
        text = build_alert_text(boot_time_str, shutdown_status, shutdown_detail,
                                ramoops_panic, ramoops_detail, pmc_source, pmc_detail)
    return {
        "orderly": orderly,
        "shutdown_status": shutdown_status,
        "shutdown_detail": shutdown_detail,
        "ramoops_panic": ramoops_panic,
        "ramoops_detail": ramoops_detail,
        "pmc_source": pmc_source,
        "pmc_detail": pmc_detail,
        "text": text,
    }


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    force = "--force" in args
    test_mode = "--test" in args

    token = read_env(ENV_FILE, "TELEGRAM_BOT_TOKEN")
    users = read_env(ENV_FILE, "TELEGRAM_USERS", "")
    owner_login = read_env(ENV_FILE, "TELEGRAM_OWNER_LOGIN", "admin")
    proxy = read_env(ENV_FILE, "TELEGRAM_PROXY") or None
    chat_id = resolve_owner_chat_id(users, owner_login)

    if test_mode:
        if not token or not chat_id:
            sys.stderr.write("нет TELEGRAM_BOT_TOKEN или владельца %r в TELEGRAM_USERS\n"
                             % owner_login)
            return 1
        ok, err = send_with_retries(
            token, chat_id,
            u"\U0001f9ea Проверка канала алерта после аварийной загрузки (D2). "
            u"Это тест, делать ничего не нужно.",
            proxy=proxy, attempts=3, delay_sec=5)
        print("тест: %s" % ("отправлен" if ok else "ошибка: %s" % err))
        return 0 if ok else 1

    boot_id = get_boot_id()
    state = load_state(STATE_FILE)
    if not force and already_handled(state, boot_id):
        print("эта загрузка (boot_id=%s) уже обработана — молчим" % boot_id)
        return 0

    signals = gather_signals(_read_last_x(), _read_ramoops(), _read_dmesg(), get_boot_time_str())

    if signals["orderly"]:
        save_state(STATE_FILE, mark_resolved(boot_id, alerted=False))
        print("штатная остановка (%s) — алерт не нужен" % signals["shutdown_detail"])
        return 0

    print("нештатная загрузка: %s" % signals["shutdown_detail"])

    if not token or not chat_id:
        msg = ("нет TELEGRAM_BOT_TOKEN или владельца %r в TELEGRAM_USERS — "
              "алерт собран, но не отправлен" % owner_login)
        write_pending(PENDING_FILE, signals["text"], msg, boot_id)
        sys.stderr.write(msg + "\n")
        sys.stderr.write(signals["text"] + "\n")
        return 1

    ok, err = send_with_retries(token, chat_id, signals["text"], proxy=proxy)
    if ok:
        save_state(STATE_FILE, mark_resolved(boot_id, alerted=True))
        print("алерт об аварийной загрузке отправлен владельцу в Telegram")
        return 0

    write_pending(PENDING_FILE, signals["text"], err, boot_id)
    sys.stderr.write("не удалось отправить алерт в Telegram: %s\n" % err)
    sys.stderr.write("сообщение сохранено (не потеряно), будет повтор при "
                     "следующем запуске юнита: %s\n" % PENDING_FILE)
    sys.stderr.write(signals["text"] + "\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
