"""OBS-1, задача 10: правила вердиктов (blackbox.why.rules) — то, на чём стоит `nas-why`.

План: docs/superpowers/plans/2026-10-13-obs1-blackbox.ru.md, «### Задача 10».
Спецификация: docs/superpowers/specs/2026-10-13-blackbox-forensics-design.ru.md, раздел 6
(«Правила вердиктов»), контракты данных — раздел «Контракты данных» плана.

Каждый тест — строка таблицы «Случаи для тестов» задачи 10, с точными значениями
оттуда (класс, уверенность, названные фразы). Пункты «Фокуса ревью» плана к задаче 10
не относятся — они в задачах 5, 7, 3, 4 и 11 — и здесь намеренно не дублируются.

TDD: пакета services/blackbox ещё нет, поэтому файл обязан падать на импорте
(ModuleNotFoundError: No module named 'blackbox'), а не на утверждениях.

Только чистые функции: Evidence собирается вручную из словарей контракта; ни
subprocess, ни сети, ни сокетов, ни живой системы, ни файлов на диске — тесты
одинаково идут на Windows и Linux.

Форма величин, которых план не назвал дословно (закреплена этими тестами):

* ``Evidence(...)`` принимает все свои атрибуты по имени: ``window``, ``boot``,
  ``samples``, ``disk_samples``, ``procs``, ``events``, ``journal``, ``pstore``,
  ``heartbeat``, ``snapshots``;
* ``Evidence.snapshots`` — список ``summary.json`` снимков загрузок (задача 8),
  от старой загрузки к новой; отображение «буква ↔ by-id» лежит в ключе
  ``"disks"`` (``{"sda": "usb-…"}``);
* события сетевых проб — ``kind`` вида ``"<имя>_down"``: ``dns_down`` закреплён
  таблицей задачи 5, ``gateway_down`` — этим файлом;
* хвост журнала контейнера приходит в событии ``detail["tail"]`` (задача 7),
  а в вердикт попадает через ``evidence``.
"""
from blackbox.config import Config
from blackbox.why.rules import (
    Evidence,
    evaluate,
    rule_container,
    rule_disk_hang,
    rule_memory,
    rule_network,
    rule_thermal,
    rule_unclean_boot,
    rule_usb,
)

# ── контракты данных (значения — из плана) ───────────────────────────────────

TS = 1791861274          # 2026-10-13 03:14:34 UTC — ts из контракта «sample»
SINCE = TS - 3600        # окно разбора — час до последнего признака жизни
UNTIL = TS
BOOT_ID = "boot-2026-10-13-0314"

SSD_BY_ID = "usb-JMicron_SSD-0:0"
HDD_BY_ID = "usb-WD_HDD-0:0"

VERDICT_KEYS = {"cls", "verdict", "confidence", "evidence"}
CONFIDENCE_VALUES = {"fact", "probable", "unknown"}

# Как сторож OPS-1 пишет своё действие в журнал (nas_jetson_nano-container-watchdog.py).
WATCHDOG_RESTART_LINE = ("nas_jetson_nano-container-watchdog[1234]: watchdog: "
                         "homecloud_stt: был running/unhealthy → docker restart OK")

# Хвост журнала контейнера, который задача 7 кладёт в событие detail["tail"].
TAIL_LINES = ["stt ERROR: не удалось открыть микрофон\n",
              "Traceback (most recent call last):\n"]


# ── сборка Evidence вручную (никаких источников) ─────────────────────────────

def ev(since=SINCE, until=UNTIL, boot=None, samples=(), disk_samples=(), procs=(),
       events=(), journal=(), pstore=(), heartbeat=None, snapshots=()):
    """Evidence из словарей контракта — ровно атрибуты из интерфейса задачи 10."""
    return Evidence(window=(since, until), boot=boot, samples=list(samples),
                    disk_samples=list(disk_samples), procs=list(procs),
                    events=list(events), journal=list(journal), pstore=list(pstore),
                    heartbeat=heartbeat, snapshots=list(snapshots))


def smp(ts, **over):
    """Строка контракта `sample` (ключи ровно как в плане)."""
    s = {"ts": ts, "vin_mv": 5080, "vin_ma": 1450, "cpu_mw": 1200, "gpu_mw": 40,
         "t_cpu": 630, "t_gpu": 605, "t_pmic": 500, "t_ao": 645,
         "cpu_pct": 37.5, "freq_mhz": 1479, "mem_avail_mb": 1327, "swap_mb": 272,
         "zram_mb": 455, "load1": 1.76, "net_rx": 123456789, "net_tx": 98765432}
    s.update(over)
    return s


def proc(ts, pid, state="S", wchan="", comm="python3", owner="host"):
    """Строка контракта `proc row`."""
    return {"ts": ts, "pid": pid, "comm": comm, "owner": owner, "cmd": comm,
            "state": state, "wchan": wchan, "cpu_pct": 0.0, "rss_mb": 1.0}


def event(ts, source, kind, subject, severity="info", detail=None):
    """Строка контракта `event`."""
    return {"ts": ts, "source": source, "kind": kind, "subject": subject,
            "severity": severity, "detail": {} if detail is None else detail}


def boot_after_crash(**over):
    """Строка контракта `boot row`: загрузка без штатного выключения прошлой."""
    b = {"boot_id": BOOT_ID, "start": TS - 7200, "end": TS, "clean": False,
         "last_heartbeat": TS, "reset_source": "TEGRA_POWER_ON_RESET",
         "pstore": [], "verdict": None, "confidence": None}
    b.update(over)
    return b


def heartbeat_at(ts, vin_mv=5080, vin_ma=1450):
    """Файл heartbeat (задача 3): boot_id, ts, последний замер питания."""
    return {"boot_id": BOOT_ID, "ts": ts,
            "power": {"vin_mv": vin_mv, "vin_ma": vin_ma}}


# ── помощники проверок ───────────────────────────────────────────────────────

def only(verdicts):
    """Ровно один вердикт — так сформулированы ожидания таблицы."""
    assert len(verdicts) == 1, "ожидался один вердикт, получено: %r" % (verdicts,)
    return verdicts[0]


def evidence_blob(verdict):
    """Доказательства вердикта одной строкой (контракт: список (ts, source, text))."""
    return " | ".join(str(item) for item in (verdict.get("evidence") or []))


def full_text(verdict):
    """Вердикт вместе с доказательствами — одной строкой."""
    return verdict["verdict"] + " | " + evidence_blob(verdict)


# ── нештатная загрузка (rule_unclean_boot) ───────────────────────────────────

def test_rule_unclean_boot_pstore_is_fact_kernel_panic():
    """Строка таблицы: boot.clean=False, pstore=["dmesg-ramoops-0"] —
    unclean_boot, fact, «паника ядра»."""
    evidence = ev(boot=boot_after_crash(pstore=["dmesg-ramoops-0"]),
                  pstore=["dmesg-ramoops-0"], heartbeat=heartbeat_at(TS))
    verdict = only(rule_unclean_boot(evidence, Config()))
    assert verdict["cls"] == "unclean_boot"
    assert verdict["confidence"] == "fact"
    assert "паника ядра" in verdict["verdict"].lower()
    # раздел 6 обещает «+ выдержку»: имя файла pstore видно в разборе
    assert "dmesg-ramoops-0" in full_text(verdict).lower()


def test_rule_unclean_boot_power_drop_is_probable():
    """Строка таблицы: за 60 с до heartbeat vin_mv 5080→4610 (ниже порога
    4750 мВ) — probable, «питание»."""
    samples = [smp(TS - 60, vin_mv=5080), smp(TS - 30, vin_mv=5090),
               smp(TS - 1, vin_mv=4610)]
    verdict = only(rule_unclean_boot(
        ev(boot=boot_after_crash(), samples=samples,
           heartbeat=heartbeat_at(TS, vin_mv=4610)), Config()))
    assert verdict["confidence"] == "probable"
    assert "питание" in verdict["verdict"].lower()


def test_rule_unclean_boot_flat_power_is_sudden_loss():
    """Строка таблицы: питание ровно 5080 до последней секунды — probable,
    «внезапное пропадание питания или аппаратный сброс», «различить нечем»."""
    samples = [smp(TS - 60, vin_mv=5080), smp(TS - 30, vin_mv=5080),
               smp(TS - 1, vin_mv=5080)]
    verdict = only(rule_unclean_boot(
        ev(boot=boot_after_crash(), samples=samples,
           heartbeat=heartbeat_at(TS)), Config()))
    text = verdict["verdict"].lower()
    assert verdict["confidence"] == "probable"
    assert "внезапное пропадание питания или аппаратный сброс" in text
    assert "различить нечем" in text


def test_rule_unclean_boot_poweroff_command_is_planned_shutdown():
    """Строка таблицы: событие boot/poweroff_command перед концом —
    вердикт «штатное выключение командой» (REL-10)."""
    events = [event(TS - 5, "boot", "poweroff_command", "host", "info",
                    {"command": "shutdown"})]
    verdicts = rule_unclean_boot(
        ev(boot=boot_after_crash(), events=events, heartbeat=heartbeat_at(TS)),
        Config())
    planned = [v for v in verdicts
               if "штатное выключение командой" in v["verdict"].lower()]
    assert len(planned) == 1


def test_rule_unclean_boot_d_state_growth_is_hang():
    """Строка таблицы: рост D-state и mem_avail_mb=120 (ниже порога 150) за
    минуту до конца — probable, «зависание, затем сброс»."""
    samples = [smp(TS - 60, mem_avail_mb=420), smp(TS - 30, mem_avail_mb=180),
               smp(TS - 1, mem_avail_mb=120)]
    procs = [proc(TS - 60, 900, state="S"),
             proc(TS - 30, 4242, state="D", wchan="request_wait_answer", comm="ntfs-3g"),
             proc(TS - 10, 4242, state="D", wchan="request_wait_answer", comm="ntfs-3g"),
             proc(TS - 10, 4243, state="D", wchan="fuse_request_wait", comm="python3")]
    verdict = only(rule_unclean_boot(
        ev(boot=boot_after_crash(), samples=samples, procs=procs,
           heartbeat=heartbeat_at(TS)), Config()))
    assert verdict["confidence"] == "probable"
    assert "зависание, затем сброс" in verdict["verdict"].lower()


def test_rule_unclean_boot_always_names_reset_source():
    """Раздел 6 спецификации («всегда — PMC reset source»): по нему владелец
    отличает пропадание питания от сторожа PMIC, и он обязан быть в разборе."""
    samples = [smp(TS - 60, vin_mv=5080), smp(TS - 1, vin_mv=4610)]
    verdict = only(rule_unclean_boot(
        ev(boot=boot_after_crash(), samples=samples,
           heartbeat=heartbeat_at(TS, vin_mv=4610)), Config()))
    assert "tegra_power_on_reset" in full_text(verdict).lower()


# ── контейнеры (rule_container) ──────────────────────────────────────────────

def test_rule_container_watchdog_restart_is_fact():
    """Строка таблицы: die 143 + строка сторожа OPS-1 «docker restart» в ±2 мин —
    container, «перезапущен сторожем OPS-1», fact."""
    events = [event(TS, "docker", "die", "homecloud_stt", "warn",
                    {"exitCode": 143, "signal": "SIGTERM",
                     "image": "homecloud/stt:latest"})]
    journal = [(TS - 20, WATCHDOG_RESTART_LINE)]
    verdict = only(rule_container(ev(events=events, journal=journal), Config()))
    assert verdict["cls"] == "container"
    assert verdict["confidence"] == "fact"
    assert "перезапущен сторожем ops-1" in verdict["verdict"].lower()


def test_rule_container_watchdog_line_outside_two_minutes_is_not_blamed():
    """Интерфейс, условие «±2 мин» той же строки таблицы: строка сторожа за
    5 минут до падения — перезапуск ему не приписывается, но код 143 всё равно
    разобран (раздел 6: «143 — SIGTERM»), а не проглочен молча."""
    events = [event(TS, "docker", "die", "homecloud_stt", "warn",
                    {"exitCode": 143})]
    journal = [(TS - 300, WATCHDOG_RESTART_LINE)]
    verdicts = rule_container(ev(events=events, journal=journal), Config())
    assert verdicts
    assert all("сторожем ops-1" not in v["verdict"].lower() for v in verdicts)


def test_rule_container_oom_killed_137_is_fact():
    """Строка таблицы: die 137 + флаг OOM — «убит по нехватке памяти», fact."""
    events = [event(TS, "docker", "die", "homecloud_immich_server", "crit",
                    {"exitCode": 137, "oom": True})]
    verdict = only(rule_container(ev(events=events), Config()))
    assert verdict["confidence"] == "fact"
    assert "убит по нехватке памяти" in verdict["verdict"].lower()


def test_rule_container_app_error_1_attaches_log_tail():
    """Строка таблицы: die 1 без сторожа — «ошибка приложения (код 1)»,
    приложен хвост журнала."""
    events = [event(TS, "docker", "die", "homecloud_stt", "crit",
                    {"exitCode": 1, "tail": TAIL_LINES})]
    verdict = only(rule_container(ev(events=events), Config()))
    assert "ошибка приложения (код 1)" in verdict["verdict"].lower()
    assert "не удалось открыть микрофон" in evidence_blob(verdict).lower()


# ── зависание диска (rule_disk_hang) ─────────────────────────────────────────

def test_rule_disk_hang_d_state_stalled_hdd_mount_hung():
    """Строка таблицы: 3 процесса D с wchan=request_wait_answer, диск HDD
    0 операций 90 с, mount_hung — disk_hang, probable."""
    # disk_sample — кортеж (ts, disk_id, rios, wios, rsect, wsect, busy_ms):
    # за 90 с счётчики HDD не изменились ни на единицу (ноль операций).
    stalled = [(TS - 90, HDD_BY_ID, 100, 200, 1000, 2000, 500),
               (TS - 30, HDD_BY_ID, 100, 200, 1000, 2000, 500),
               (TS, HDD_BY_ID, 100, 200, 1000, 2000, 500)]
    procs = [proc(TS, 4242, state="D", wchan="request_wait_answer", comm="ntfs-3g"),
             proc(TS, 4243, state="D", wchan="request_wait_answer", comm="python3"),
             proc(TS, 4244, state="D", wchan="request_wait_answer", comm="find")]
    events = [event(TS - 30, "probe", "mount_hung", "/mnt/hdd2tb", "warn",
                    {"since": TS - 120})]
    verdict = only(rule_disk_hang(
        ev(disk_samples=stalled, procs=procs, events=events), Config()))
    assert verdict["cls"] == "disk_hang"
    assert verdict["confidence"] == "probable"


# ── память (rule_memory) ─────────────────────────────────────────────────────

def test_rule_memory_oom_kill_in_kernel_journal_is_fact():
    """Строка таблицы: oom-kill в журнале ядра — memory, fact, назван процесс."""
    journal = [
        (TS - 31, "kernel: oom-kill:constraint=CONSTRAINT_NONE,global_oom,"
                  "task=python3,pid=4242,uid=0"),
        (TS - 30, "kernel: Out of memory: Killed process 4242 (python3) "
                  "total-vm:1234000kB, anon-rss:567000kB, file-rss:0kB"),
    ]
    verdict = only(rule_memory(ev(journal=journal), Config()))
    assert verdict["cls"] == "memory"
    assert verdict["confidence"] == "fact"
    assert "python3" in verdict["verdict"].lower()


# ── сеть и туннель (rule_network) ────────────────────────────────────────────

def test_rule_network_dns_down_with_alive_gateway():
    """Строка таблицы: dns_down при живом шлюзе (события gateway_down нет, то
    есть шлюз не падал) — network, «DNS»."""
    events = [event(TS, "probe", "dns_down", "dns", "warn", {})]
    verdict = only(rule_network(ev(events=events), Config()))
    assert verdict["cls"] == "network"
    assert "dns" in verdict["verdict"].lower()


def test_rule_network_gateway_down_is_home_network():
    """Строка таблицы: шлюз недоступен — network, «домашняя сеть/роутер»."""
    events = [event(TS, "probe", "gateway_down", "gateway", "warn", {})]
    verdict = only(rule_network(ev(events=events), Config()))
    assert verdict["cls"] == "network"
    text = verdict["verdict"].lower()
    assert "домашняя сеть" in text
    assert "роутер" in text


# ── перегрев (rule_thermal) ──────────────────────────────────────────────────

def test_rule_thermal_hot_cpu_with_frequency_drop():
    """Строка таблицы: t_cpu ≥ 950 (95,0 °C) и частота упала (1479 → 307 МГц) —
    thermal, probable."""
    samples = [smp(TS - 120, t_cpu=630, freq_mhz=1479),
               smp(TS - 60, t_cpu=880, freq_mhz=1479),
               smp(TS - 1, t_cpu=950, freq_mhz=307)]
    verdict = only(rule_thermal(ev(samples=samples), Config()))
    assert verdict["cls"] == "thermal"
    assert verdict["confidence"] == "probable"


# ── USB и диски (rule_usb) ───────────────────────────────────────────────────

def test_rule_usb_letters_swapped_between_boots_is_fact():
    """Строка таблицы: в снимке прошлой загрузки sda=usb-WD…, в текущей
    sdb=usb-WD… — usb, «буквы дисков поменялись», fact (REL-11)."""
    previous = {"boot_id": BOOT_ID + "-prev", "start": TS - 86400, "pstore": [],
                "disks": {"sda": HDD_BY_ID, "sdb": SSD_BY_ID}}
    current = {"boot_id": BOOT_ID, "start": TS, "pstore": [],
               "disks": {"sda": SSD_BY_ID, "sdb": HDD_BY_ID}}
    verdict = only(rule_usb(ev(snapshots=[previous, current]), Config()))
    assert verdict["cls"] == "usb"
    assert verdict["confidence"] == "fact"
    assert "буквы дисков поменялись" in verdict["verdict"].lower()


# ── evaluate: все правила разом ──────────────────────────────────────────────

def test_evaluate_empty_window_reports_no_data():
    """Строка таблицы: окно без данных — ровно один вердикт: data/unknown,
    «данных нет за <окно>» (никогда не догадка)."""
    verdicts = evaluate(ev(), Config())
    assert len(verdicts) == 1
    verdict = verdicts[0]
    assert verdict["cls"] == "data"
    assert verdict["confidence"] == "unknown"
    assert verdict["verdict"].startswith("данных нет за")
    assert set(verdict) == VERDICT_KEYS


def test_evaluate_runs_all_rules():
    """Интерфейс: evaluate — «все правила», вердикты разных классов попадают
    в один список (а не первый подошедший)."""
    events = [event(TS, "docker", "die", "homecloud_stt", "crit", {"exitCode": 1}),
              event(TS, "probe", "dns_down", "dns", "warn", {})]
    verdicts = evaluate(ev(events=events), Config())
    classes = set(v["cls"] for v in verdicts)
    assert "container" in classes
    assert "network" in classes


def test_verdict_shape_matches_data_contract():
    """Контракт данных: вердикт — dict {cls, verdict, confidence, evidence};
    confidence — из {fact, probable, unknown}; evidence — список (ts, source, text)
    с целым ts (секунды эпохи UTC)."""
    evidence = ev(boot=boot_after_crash(pstore=["dmesg-ramoops-0"]),
                  pstore=["dmesg-ramoops-0"], heartbeat=heartbeat_at(TS))
    verdict = only(rule_unclean_boot(evidence, Config()))
    assert set(verdict) == VERDICT_KEYS
    assert verdict["confidence"] in CONFIDENCE_VALUES
    assert verdict["evidence"], "вердикт «паника ядра» обязан нести доказательство"
    for item in verdict["evidence"]:
        assert len(item) == 3
        assert isinstance(item[0], int)
        assert isinstance(item[1], str)
        assert isinstance(item[2], str)
