#!/usr/bin/env python3
"""D2: алерт владельцу в Telegram после аварийной загрузки Jetson.

ЗАЧЕМ. ИБП отложен, копии архива нет (CLAUDE.md, решения владельца D1/D3
2026-09-19) — единственная защита от провала питания состоит в том, чтобы о
нём вовреме узнать. 17.08.2026 Jetson перезагрузился аппаратно, и это
заметили только задним числом, разбирая логи вручную. Этот тест — прямая
регрессия на тот случай: `classify_shutdown()` обязана распознавать именно
такую последовательность `last -x` (реальная находка 23.08: "парной строки
shutdown в wtmp нет"), не выдумывая причину — CLAUDE.md отдельно фиксирует,
что провал питания и срабатывание PMIC-watchdog по трём доступным признакам
(last -x / ramoops / dmesg PMC reset source) неразличимы.

Боевой модуль импортируется целиком — никаких копий логики.
Запуск (без pytest, идёт и на Jetson с Python 3.6):
    python3 tests/unit/test_boot_alert.py
"""
import importlib.util
import io
import json
import os
import sys
import tempfile

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE_PATH = os.path.join(HERE, "..", "..", "scripts", "monitoring",
                           "nas_jetson_nano-boot-alert.py")


def load_module():
    spec = importlib.util.spec_from_file_location("boot_alert", MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── фикстуры: реальный формат `last -x` ────────────────────────────────────────

# Штатная перезагрузка: перед каждой записью reboot есть парная shutdown.
ORDERLY_LAST_X = """\
reboot   system boot  4.9.253-tegra   Fri Sep 19 04:37 - 09:12  (04:34)
runlevel (to lvl 5)   3.10             Fri Sep 19 04:37 - 04:37  (00:00)
shutdown system down  4.9.253-tegra   Fri Sep 19 04:36 - 04:37  (00:00)
reboot   system boot  4.9.253-tegra   Thu Sep 18 20:00 - 04:36 (08:36)
runlevel (to lvl 5)   3.10             Thu Sep 18 20:00 - 20:00  (00:00)
shutdown system down  4.9.253-tegra   Thu Sep 18 08:00 - 20:00  (12:00)
reboot   system boot  4.9.253-tegra   Wed Sep 17 11:05 - 08:00 (20:55)

wtmp begins Wed Sep 17 11:05:00 2026
"""

# Регрессия на настоящий инцидент 2026-08-17 (CLAUDE.md, точка 23.08 §3.1):
# после записи reboot сразу идёт ЕЩЁ ОДНА reboot — записи shutdown между ними нет.
ABNORMAL_LAST_X_2026_08_17 = """\
reboot   system boot  4.9.253-tegra   Mon Aug 17 11:05 - 20:45  (09:40)
reboot   system boot  4.9.253-tegra   Sun Aug 16 09:00 - 11:04 (1+02:04)
shutdown system down  4.9.253-tegra   Sun Aug 16 08:59 - 09:00  (00:00)
reboot   system boot  4.9.253-tegra   Sat Aug 15 07:00 - 08:59 (1+01:59)

wtmp begins Sat Aug 15 07:00:00 2026
"""

# Только одна запись в истории (первая загрузка устройства, или wtmp только
# что заведён/обрезан). Сравнивать не с чем — решение по умолчанию: НЕ
# считать это штатным молча, а честно сказать "не удалось определить".
FIRST_BOOT_LAST_X = """\
reboot   system boot  4.9.253-tegra   Fri Sep 19 04:37   still running

wtmp begins Fri Sep 19 04:37:00 2026
"""

DMESG_HARDWARE_RESET = """\
[    0.000000] Booting Linux on physical CPU 0x0
[    0.123456] Tegra Revision: SILICON CPU Revision: 0.2.2
[    0.234567] PMC reset source: TEGRA_POWER_ON_RESET
[    0.345678] PMIC reset reason: 00000000
"""

DMESG_SOFTWARE_RESET = """\
[    0.000000] Booting Linux on physical CPU 0x0
[    0.234567] PMC reset source: TEGRA_SW_RESET
"""

DMESG_NO_PMC_LINE = "[    0.000000] Booting Linux on physical CPU 0x0\n"

RAMOOPS_PANIC = """\
<4>[  123.456] Kernel panic - not syncing: Fatal exception
<4>[  123.457] CPU: 0 PID: 1 Comm: swapper/0
Call trace:
[<c010a1b0>] (unwind_backtrace)
"""

RAMOOPS_CLEAN_TAIL = "console output tail, last lines before reset, nothing unusual\n"


def main():
    mod = load_module()
    failures = 0

    def case(name, cond, got=None):
        nonlocal failures
        if cond:
            print("  [ok]   %s" % name)
        else:
            print("  [FAIL] %s\n         получено: %r" % (name, got))
            failures += 1

    print("D2: алерт после аварийной загрузки")

    # ── classify_shutdown ────────────────────────────────────────────────────
    print("\n-- classify_shutdown() --")

    status, detail = mod.classify_shutdown(ORDERLY_LAST_X)
    case("штатная перезагрузка (shutdown перед reboot) — orderly",
         status == "orderly", (status, detail))

    status, detail = mod.classify_shutdown(ABNORMAL_LAST_X_2026_08_17)
    case("регрессия 2026-08-17: reboot сразу за reboot, без shutdown — abnormal",
         status == "abnormal", (status, detail))
    case("причина не выдумывается — в тексте нет утверждения о провале питания",
         "питани" not in detail.lower(), detail)

    status, detail = mod.classify_shutdown(FIRST_BOOT_LAST_X)
    case("только одна запись в wtmp — unknown, а не молчаливое orderly",
         status == "unknown", (status, detail))

    status, detail = mod.classify_shutdown("")
    case("пустой last -x — unknown, не падение", status == "unknown", (status, detail))

    status, detail = mod.classify_shutdown("какая-то ерунда без записей\n")
    case("неразбираемый last -x — unknown", status == "unknown", (status, detail))

    # ── classify_ramoops ─────────────────────────────────────────────────────
    print("\n-- classify_ramoops() --")

    panic, detail = mod.classify_ramoops(None)
    case("файл ramoops отсутствует — трассы паники нет", panic is False, detail)

    panic, detail = mod.classify_ramoops("")
    case("файл ramoops пуст — трассы паники нет", panic is False, detail)

    panic, detail = mod.classify_ramoops(RAMOOPS_CLEAN_TAIL)
    case("непустой ramoops без маркеров паники — panic=False", panic is False, detail)

    panic, detail = mod.classify_ramoops(RAMOOPS_PANIC)
    case("ramoops с Kernel panic — panic=True", panic is True, detail)

    # ── parse_pmc_reset_source ───────────────────────────────────────────────
    print("\n-- parse_pmc_reset_source() --")

    source, detail = mod.parse_pmc_reset_source(DMESG_HARDWARE_RESET)
    case("PMC reset source распознан (TEGRA_POWER_ON_RESET)",
         source == "TEGRA_POWER_ON_RESET", (source, detail))

    source, detail = mod.parse_pmc_reset_source(DMESG_SOFTWARE_RESET)
    case("другое значение PMC reset source распознаётся как есть",
         source == "TEGRA_SW_RESET", (source, detail))

    source, detail = mod.parse_pmc_reset_source(DMESG_NO_PMC_LINE)
    case("строки PMC reset source нет в dmesg — None, не падение",
         source is None, (source, detail))

    # ── build_alert_text: честная формулировка, не выдуманная причина ──────────
    print("\n-- build_alert_text() --")

    text = mod.build_alert_text(
        "17.08.2026 11:05:00", "abnormal",
        "перед этой загрузкой нет записи об штатном выключении",
        False, "файл отсутствует — трассы паники нет",
        "TEGRA_POWER_ON_RESET", "PMC reset source: TEGRA_POWER_ON_RESET")
    case("текст называет время загрузки", "17.08.2026 11:05:00" in text, text)
    case("текст называет все три признака",
         "last -x" in text and "ramoops" in text and "PMC reset source" in text, text)
    case("честная формулировка о неразличимости провала питания и PMIC-watchdog",
         "PMIC-watchdog" in text and "невозможно" in text, text)
    case("текст НЕ утверждает конкретную причину как факт",
         "это был провал питания" not in text.lower()
         and "точно провал питания" not in text.lower(), text)

    text_panic = mod.build_alert_text(
        "20.09.2026 03:00:00", "abnormal", "нет записи shutdown",
        True, "содержит признаки паники ядра (Kernel panic/Oops/BUG)",
        None, "строка 'PMC reset source' не найдена в dmesg")
    case("при найденной панике текст говорит о программном сбое, не о питании",
         "программн" in text_panic.lower(), text_panic)

    # ── parse_telegram_users / resolve_owner_chat_id ────────────────────────
    print("\n-- resolve_owner_chat_id() --")

    users_str = "123456:admin 777:olga"
    case("владелец находится по логину",
         mod.resolve_owner_chat_id(users_str, "admin") == 123456,
         mod.resolve_owner_chat_id(users_str, "admin"))
    case("логина нет в списке — None, не падение",
         mod.resolve_owner_chat_id(users_str, "nobody") is None,
         mod.resolve_owner_chat_id(users_str, "nobody"))
    case("пустая строка — None", mod.resolve_owner_chat_id("", "admin") is None)
    case("битая запись без ':' молча пропускается, остальные разбираются",
         mod.resolve_owner_chat_id("bad-entry 123456:admin", "admin") == 123456)

    # ── send_telegram / send_with_retries (curl мокается, сети нет) ─────────
    print("\n-- send_telegram() / send_with_retries() --")

    class FakeProc:
        def __init__(self, returncode, stdout="", stderr=""):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def ok_run(cmd, **kw):
        return FakeProc(0, stdout=json.dumps({"ok": True, "result": {"message_id": 1}}))

    result = mod.send_telegram("mocktoken:1234567890", 123456, "текст",
                               proxy="socks5://172.17.0.1:1080", run=ok_run)
    case("успешный ответ Telegram разобран", result == {"message_id": 1}, result)

    seen_cmds = []

    def capturing_run(cmd, **kw):
        seen_cmds.append(cmd)
        return FakeProc(0, stdout=json.dumps({"ok": True, "result": {}}))

    mod.send_telegram("mocktoken:1234567890", 123456, "текст",
                      proxy="socks5://172.17.0.1:1080", run=capturing_run)
    cmd = seen_cmds[0]
    case("SOCKS-прокси передан curl без схемы socks5://",
         "--socks5-hostname" in cmd and "172.17.0.1:1080" in cmd, cmd)
    case("токен уходит в URL запроса, а не в отдельный видимый аргумент-секрет",
         any("mocktoken:1234567890" in c for c in cmd), cmd)

    def curl_fail_run(cmd, **kw):
        return FakeProc(7, stderr="Failed to connect to 172.17.0.1 port 1080")

    threw = False
    try:
        mod.send_telegram("mocktoken:1234567890", 123456, "текст", run=curl_fail_run)
    except Exception:
        threw = True
    case("недоступный SOCKS — исключение, а не тихий провал", threw)

    def bad_json_run(cmd, **kw):
        return FakeProc(0, stdout="не json")

    threw = False
    try:
        mod.send_telegram("mocktoken:1234567890", 123456, "текст", run=bad_json_run)
    except Exception:
        threw = True
    case("не-JSON ответ — исключение", threw)

    def api_error_run(cmd, **kw):
        return FakeProc(0, stdout=json.dumps({"ok": False, "description": "Unauthorized"}))

    threw = False
    try:
        mod.send_telegram("mocktoken:1234567890", 123456, "текст", run=api_error_run)
    except Exception as exc:
        threw = "Unauthorized" in str(exc)
    case("Telegram API ok=false — исключение с описанием", threw)

    # send_with_retries: несколько попыток, требование 5 (SOCKS поднимается не сразу)
    attempts_made = [0]

    def flaky_run(cmd, **kw):
        attempts_made[0] += 1
        if attempts_made[0] < 3:
            return FakeProc(7, stderr="socks недоступен")
        return FakeProc(0, stdout=json.dumps({"ok": True, "result": {}}))

    sleeps = []
    ok, err = mod.send_with_retries("mocktoken:1234567890", 123456, "текст",
                                    attempts=5, delay_sec=1, run=flaky_run,
                                    sleep=lambda s: sleeps.append(s))
    case("успех после двух неудач — retries отработали", ok is True, (ok, err))
    case("между попытками была пауза", len(sleeps) == 2, sleeps)

    attempts_made2 = [0]

    def always_fail_run(cmd, **kw):
        attempts_made2[0] += 1
        return FakeProc(7, stderr="socks недоступен постоянно")

    ok, err = mod.send_with_retries("mocktoken:1234567890", 123456, "текст",
                                    attempts=3, delay_sec=0, run=always_fail_run,
                                    sleep=lambda s: None)
    case("исчерпаны все попытки — False с текстом последней ошибки",
         ok is False and err and "socks" in err, (ok, err))
    case("сделано ровно столько попыток, сколько задано",
         attempts_made2[0] == 3, attempts_made2[0])

    # ── состояние: не дублировать алерт при перезапуске юнита (требование 4) ──
    print("\n-- load_state / save_state / already_handled --")

    tmp = tempfile.mkdtemp()
    state_path = os.path.join(tmp, "sub", "boot-alert-state.json")

    empty = mod.load_state(state_path)
    case("нет файла состояния — пустой словарь, не падение", empty == {}, empty)

    st = mod.mark_resolved("boot-id-AAA", alerted=True)
    mod.save_state(state_path, st)
    loaded = mod.load_state(state_path)
    case("состояние переживает round-trip на диск",
         loaded.get("boot_id") == "boot-id-AAA" and loaded.get("alerted") is True, loaded)

    case("тот же boot_id, уже resolved — повторный запуск юнита молчит",
         mod.already_handled(loaded, "boot-id-AAA") is True)
    case("другой boot_id (новая загрузка) — не считается обработанным",
         mod.already_handled(loaded, "boot-id-BBB") is False)
    case("не-resolved состояние не считается обработанным",
         mod.already_handled({"boot_id": "x", "resolved": False}, "x") is False)

    with open(state_path, "w", encoding="utf-8") as fh:
        fh.write("{битый json")
    case("битый файл состояния — пустой словарь, не падение всего скрипта",
         mod.load_state(state_path) == {})

    # ── pending: сообщение не теряется молча при сорванной отправке ─────────
    print("\n-- write_pending / read_pending --")

    pending_path = os.path.join(tmp, "boot-alert-pending.json")
    mod.write_pending(pending_path, "текст алерта", "socks недоступен", "boot-id-CCC")
    pending = mod.load_state(pending_path)
    case("отложенный алерт сохранён целиком, а не потерян",
         pending.get("text") == "текст алерта"
         and pending.get("error") == "socks недоступен"
         and pending.get("boot_id") == "boot-id-CCC", pending)

    # ── get_boot_time_str / get_boot_id: чтение системных файлов ────────────
    print("\n-- get_boot_time_str() / get_boot_id() --")

    stat_path = os.path.join(tmp, "fake-stat")
    with open(stat_path, "w", encoding="utf-8") as fh:
        fh.write("cpu  0 0 0 0\nbtime 1758273600\nprocesses 123\n")
    boot_time = mod.get_boot_time_str(stat_path)
    case("время загрузки взято из btime, не текст-заглушка",
         boot_time and "не определено" not in boot_time, boot_time)

    case("нет файла /proc/stat — честный текст, а не исключение",
         "не определено" in mod.get_boot_time_str(os.path.join(tmp, "нет-такого")))

    boot_id_path = os.path.join(tmp, "fake-boot-id")
    with open(boot_id_path, "w", encoding="utf-8") as fh:
        fh.write("11111111-2222-3333-4444-555555555555\n")
    case("boot_id читается и обрезается", mod.get_boot_id(boot_id_path) ==
         "11111111-2222-3333-4444-555555555555")
    case("нет файла boot_id — None, не исключение",
         mod.get_boot_id(os.path.join(tmp, "нет-такого")) is None)

    # ── gather_signals: сквозная сборка трёх сырых источников в решение ─────
    print("\n-- gather_signals() (сквозная сборка) --")

    sig = mod.gather_signals(ORDERLY_LAST_X, None, DMESG_HARDWARE_RESET, "19.09.2026 04:37:00")
    case("штатная загрузка — orderly=True и текста алерта нет",
         sig["orderly"] is True and sig["text"] is None, sig)

    sig = mod.gather_signals(ABNORMAL_LAST_X_2026_08_17, None, DMESG_HARDWARE_RESET,
                             "17.08.2026 11:05:00")
    case("регрессия 2026-08-17 целиком: orderly=False и текст алерта собран",
         sig["orderly"] is False and sig["text"] is not None
         and "17.08.2026 11:05:00" in sig["text"], sig)
    case("собранный текст несёт честную формулировку о неразличимости",
         "PMIC-watchdog" in sig["text"], sig["text"])

    print("\nпадений: %d" % failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
