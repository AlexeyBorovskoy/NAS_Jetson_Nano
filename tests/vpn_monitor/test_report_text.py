"""Окна МСК, выборки и текст суточного отчёта (§7). Ключи и имена фиктивные."""
from datetime import date, datetime, timezone

import pytest

import vpnmon_query as vq
import vpnmon_render as vr
import vpnmon_store as vs

KEY_A, KEY_B = "A" * 43 + "=", "B" * 43 + "="
KEY_C, KEY_D = "C" * 43 + "=", "D" * 43 + "="
MB, GB, HOUR, DAY = 1024 ** 2, 1024 ** 3, 3600, 86400
DAY_UNDER_TEST = date(2026, 10, 4)
START = int(datetime(2026, 10, 3, 21, 0, tzinfo=timezone.utc).timestamp())
NOW = START + DAY + 10 * HOUR  # 05.10 10:00 МСК


@pytest.fixture
def db(tmp_path):
    conn = vs.open_db(str(tmp_path / "vpnmon.db"))
    yield conn
    conn.close()


def seed(db):
    db.executemany("INSERT INTO peers (pubkey, name, vpn_ip, first_seen, last_handshake, removed_at) "
                   "VALUES (?, ?, ?, ?, ?, ?)", [
                       (KEY_A, "Клиент-А", "10.8.1.2", START - 40 * DAY, NOW - 30, None),
                       (KEY_B, "<b>&Клиент-Б-очень-длинное", "10.8.1.3", START - 40 * DAY, NOW - 10 * DAY, None),
                       (KEY_C, "Клиент-В", "10.8.1.4", START - 40 * DAY, 0, None),
                       (KEY_D, "Удалённый", "10.8.1.5", START - 40 * DAY, NOW - 100 * DAY, START),
                   ])
    db.executemany("INSERT INTO peer_hourly (pubkey, hour_utc, rx, tx, peak_bps) VALUES (?, ?, ?, ?, ?)", [
        (KEY_A, START, 100 * MB, 3 * GB, 48e6),
        (KEY_A, START - 3 * DAY, 0, 2 * GB, 10e6),
        (KEY_A, START - HOUR, 0, 7 * GB, 99e6),  # 23:00 МСК 03.10 — не в сутках 04.10
        (KEY_B, START + 5 * HOUR, 10 * MB, 500 * MB, 2e6),
    ])
    db.execute("INSERT INTO host_hourly (hour_utc, samples, cpu_n, cpu_sum, cpu_max, mem_max, "
               "mem_total, load_max, disk_pct, wan_rx, wan_tx, xray_rx, xray_tx, conntrack_max) "
               "VALUES (?, 60, 60, 180.0, 41.0, ?, ?, 0.5, 27.0, ?, ?, ?, ?, 900)",
               (START, 610 * MB, 1967 * MB, 24 * GB, 25 * GB, 9 * MB, 9 * MB))
    vs.set_meta(db, "monitoring_start", START - 40 * DAY)
    db.commit()


def text_of(db):
    return vr.render(vq.build_report(db, DAY_UNDER_TEST, NOW))


def test_report_day_and_bounds():
    assert vq.report_day(datetime(2026, 10, 5, 7, 0, tzinfo=timezone.utc).timestamp()) == date(2026, 10, 4)
    assert vq.report_day(datetime(2026, 10, 4, 20, 59, tzinfo=timezone.utc).timestamp()) == date(2026, 10, 3)
    assert vq.day_bounds(DAY_UNDER_TEST) == (START, START + DAY)


def test_day_window_excludes_previous_msk_evening(db):
    seed(db)
    totals = vq.peer_totals(db, START, START + DAY)
    assert totals[KEY_A] == (100 * MB, 3 * GB, 48e6)


def test_render_main_blocks(db):
    seed(db)
    text = text_of(db)
    assert text.splitlines()[0] == "📡 VPN и VPS — 04.10 (МСК)"
    assert "VPS ✅  CPU ср 3 % · пик 41 %  ·  RAM пик 610 / 1967 МБ  ·  диск 27 %" in text
    assert "Сеть VPS: ↓ 24.0 ГБ  ↑ 25.0 ГБ  ·  conntrack пик 900" in text
    assert "AmneziaWG: 3 клиентов · с трафиком за сутки 2 · сейчас в сети 1" in text
    assert "Через туннель за сутки: ↓ 3.5 ГБ ↑ 110 МБ · контейнер xray: 18 МБ" in text
    assert "Сбор: 60 из 1440 мин" in text


def test_render_table_order_and_windows(db):
    seed(db)
    rows = [line for line in text_of(db).splitlines() if line.startswith(("Клиент-А", "<b>&"))]
    assert rows[0].split()[:4] == ["Клиент-А", "3.1G", "12.1G", "12.1G"]
    assert rows[0].endswith("48 Мбит/с")
    assert rows[1].startswith("<b>&Клиент-Б-о ") and "510M" in rows[1]


def test_render_silence_and_never(db):
    seed(db)
    text = text_of(db)
    assert "Молчат: >7 дн — 1 · >30 дн — 0 · >90 дн — 0" in text
    assert "  >7 дн: <b>&Клиент-Б-очень-длинное" in text
    assert "Не подключались с 25.08: 1 — Клиент-В" in text
    assert "Удалённый" not in text


def test_render_downtime_and_restart(db):
    seed(db)
    down_from = START + 7 * HOUR + 55 * 60
    down_to = down_from + 32 * 60
    started = datetime.fromtimestamp(down_to + 11, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + ".577Z"
    vs.add_event(db, down_to + 60, "vps_down", {"from": down_from, "to": down_to,
                                                "reason": "hypervisor initiated shutdown"})
    vs.add_event(db, down_to + 60, "container_start", {"name": "amnezia-awg2", "started": started})
    db.commit()
    text = text_of(db)
    assert "VPS ⚠️" in text
    assert "⚠️ Простой 07:55–08:27 (32 мин): hypervisor initiated shutdown" in text
    assert "↻ amnezia-awg2 — старт 08:27 (вместе с VPS)" in text


def test_render_previous_failure_first(db):
    seed(db)
    vs.set_meta(db, "last_report_failed", "2026-10-03")
    db.commit()
    assert text_of(db).splitlines()[0] == "⚠️ отчёт за 03.10 не был доставлен"


def test_render_empty_day(db):
    text = vr.render(vq.build_report(db, DAY_UNDER_TEST, NOW))
    assert "VPS: за сутки нет ни одного замера" in text
    assert "Трафика через туннель за сутки не было" in text


def test_render_escapes_and_truncates_names(db):
    seed(db)
    messages = vr.to_messages(text_of(db))
    body = messages[0][len("<pre>"):-len("</pre>")]
    assert "&lt;b&gt;&amp;Клиент-Б-о " in body
    assert "<b>" not in body
    assert all(len(m) <= vr.TG_LIMIT for m in messages)


def test_to_messages_splits_long_text_by_lines():
    text = "\n".join("строка %03d " % i + "x" * 30 for i in range(300))
    messages = vr.to_messages(text, limit=1000)
    assert len(messages) > 1
    assert all(m.startswith("<pre>") and m.endswith("</pre>") and len(m) <= 1000 for m in messages)
    joined = "\n".join(m[len("<pre>"):-len("</pre>")] for m in messages)
    assert joined == text


def test_formatters():
    assert (vr.fmt_bytes(18 * MB), vr.fmt_bytes(int(3.5 * GB))) == ("18 МБ", "3.5 ГБ")
    assert (vr.fmt_short(510 * MB), vr.fmt_short(int(12.1 * GB))) == ("510M", "12.1G")
    assert (vr.fmt_rate(0), vr.fmt_rate(48e6), vr.fmt_rate(2e5)) == ("—", "48 Мбит/с", "200 кбит/с")
    assert vr.docker_time("мусор") is None


def test_long_line_entities_and_emoji_remain_complete():
    import html
    text = "<&\U0001f600>" * 1500
    messages = vr.to_messages(text, limit=97)
    bodies = [m[5:-6] for m in messages]
    assert "".join(html.unescape(body) for body in bodies) == text
    assert all(len(m.encode("utf-16-le")) // 2 <= 97 for m in messages)
    assert all(not body.endswith(("&", "&l", "&lt", "&a", "&am", "&amp")) for body in bodies)


def test_message_preserves_blank_lines():
    import html
    text = "\n\n<&>\n\n"
    assert html.unescape(vr.to_messages(text)[0][5:-6]) == text


@pytest.mark.parametrize("limit", [0, 11, 12])
def test_message_rejects_limit_that_cannot_fit_character(limit):
    with pytest.raises(ValueError):
        vr.to_messages("&", limit=limit)


def test_removed_peer_traffic_still_in_day_table_not_silence(db):
    seed(db)
    db.execute("INSERT INTO peer_hourly (pubkey, hour_utc, rx, tx, peak_bps) VALUES (?, ?, ?, ?, ?)",
               (KEY_D, START, 0, 20 * MB, 1e6))
    text = text_of(db)
    assert "Удалённый" in text
    assert "с трафиком за сутки 3" in text
    assert "AmneziaWG: 3 клиентов" in text
    assert "Молчат: >7 дн — 1 · >30 дн — 0 · >90 дн — 0" in text


def test_week_and_month_boundaries(db):
    seed(db)
    db.executemany("INSERT INTO peer_hourly (pubkey, hour_utc, rx, tx, peak_bps) VALUES (?, ?, 0, ?, 1)", [
        (KEY_C, START - 6 * DAY, MB),
        (KEY_C, START - 6 * DAY - HOUR, 2 * MB),
        (KEY_C, START - 29 * DAY, 4 * MB),
        (KEY_C, START - 29 * DAY - HOUR, 8 * MB),
        (KEY_C, START + DAY, 16 * MB),
    ])
    data = vq.build_report(db, DAY_UNDER_TEST, NOW)
    assert KEY_C not in data["day_totals"]
    assert data["week_totals"][KEY_C][1] == MB
    assert data["month_totals"][KEY_C][1] == 7 * MB
