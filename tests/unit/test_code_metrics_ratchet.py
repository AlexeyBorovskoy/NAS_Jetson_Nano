#!/usr/bin/env python3
"""Stage 8 (code audit 2026-10-02): the metrics ratchet's pure compare().

ЗАЧЕМ. docs/audit/2026-10-02_code_audit/PLAN.ru.md, раздел «Храповик»: без
гейта структурный рефакторинг свободно откатывается обратно, никто не узнаёт
об этом до следующего ручного аудита. `compare()` в
scripts/quality/code_metrics.py — чистая функция (без git/argv/файлов),
поэтому здесь она проверяется на синтетических словарях-фикстурах, а не на
реальном дереве: тест должен падать от логической ошибки в правилах R1-R4,
а не от того, что кто-то поправил код в соседнем сервисе.

Правила (R1-R4), которые здесь проверяются:
  R1 — число модулей уровня `fail` (только продуктовые файлы) не растёт.
  R2 — модуль, уже бывший `warn`/`fail` в baseline, не ухудшает
       cc_max/func_loc_max/nest_max/(broad_catch+silent_catch); `loc`
       разрешено вырасти не больше чем на 10%.
  R3 — функция, которой нет в фингерпринте `funcs` baseline-файла (новая,
       или любая функция в совсем новом файле), обязана иметь CC <= 10 и
       длину <= 40 строк — порог строже легаси-порогов, чтобы новый код не
       проезжал на правах старого.
  R4 — нарушение в файле из allow выводится как «разрешено: <причина>» и не
       считается провалом.
  Отдельно: commits/churn_lines/bug_commits/hotspot_score не сравниваются —
  они меняются с каждым коммитом независимо от качества кода.

Запуск (без pytest, идёт и на Jetson с Python 3.6):
    python3 tests/unit/test_code_metrics_ratchet.py
Тот же файл собирается pytest'ом: функции test_* используют обычный assert.
"""
import importlib.util
import os
import sys

# No stdout re-wrap here: loading code_metrics.py below performs the same
# UTF-8-console fix once, and wrapping it a second time garbage-collects the
# first TextIOWrapper, which closes the shared buffer out from under it
# ("I/O operation on closed file") — see code_metrics.py's own guard comment.

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE_PATH = os.path.join(HERE, "..", "..", "scripts", "quality", "code_metrics.py")


def load_module():
    spec = importlib.util.spec_from_file_location("code_metrics", MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


code_metrics = load_module()
compare = code_metrics.compare


def prod_module(level="ok", cc_max=5, func_loc_max=10, nest_max=1,
                broad_catch=0, silent_catch=0, loc=100, funcs=None,
                commits=1, churn_lines=1, hotspot_score=0.0):
    return {"test": False, "level": level, "cc_max": cc_max,
            "func_loc_max": func_loc_max, "nest_max": nest_max,
            "broad_catch": broad_catch, "silent_catch": silent_catch,
            "loc": loc, "funcs": funcs if funcs is not None else [],
            "commits": commits, "churn_lines": churn_lines,
            "hotspot_score": hotspot_score}


def only(violations, rule_prefix):
    return [v for v in violations if v["rule"].startswith(rule_prefix)]


# ── R1: число fail-модулей ───────────────────────────────────────────────────

def test_r1_growing_fail_count_is_a_violation():
    baseline = {"modules": {"a.py": prod_module(level="warn")}}
    current = {"modules": {"a.py": prod_module(level="fail", cc_max=30)}}
    violations = compare(baseline, current, {})
    hits = only(violations, "R1")
    assert len(hits) == 1, violations
    assert hits[0]["file"] == "a.py"
    assert hits[0]["before"] == "warn" and hits[0]["after"] == "fail"
    assert hits[0]["allowed"] is False


def test_r1_stable_fail_count_is_not_a_violation():
    baseline = {"modules": {"a.py": prod_module(level="fail", cc_max=30)}}
    current = {"modules": {"a.py": prod_module(level="fail", cc_max=30)}}
    assert only(compare(baseline, current, {}), "R1") == []


def test_r1_brand_new_failing_file_counts_as_growth():
    baseline = {"modules": {"a.py": prod_module(level="ok")}}
    current = {"modules": {"a.py": prod_module(level="ok"),
                           "b.py": prod_module(level="fail", cc_max=99)}}
    hits = only(compare(baseline, current, {}), "R1")
    assert len(hits) == 1 and hits[0]["file"] == "b.py"


# ── R2: регресс уже нездорового модуля ───────────────────────────────────────

def test_r2_legacy_module_worsened_cc_max_is_a_violation():
    baseline = {"modules": {"legacy.py": prod_module(level="warn", cc_max=15)}}
    current = {"modules": {"legacy.py": prod_module(level="warn", cc_max=20)}}
    hits = only(compare(baseline, current, {}), "R2 cc_max")
    assert len(hits) == 1
    assert hits[0]["before"] == 15 and hits[0]["after"] == 20


def test_r2_legacy_module_improved_is_ok():
    baseline = {"modules": {"legacy.py": prod_module(level="warn", cc_max=15)}}
    current = {"modules": {"legacy.py": prod_module(level="warn", cc_max=12)}}
    assert compare(baseline, current, {}) == []


def test_r2_healthy_module_getting_worse_is_not_r2():
    # R2 only ratchets a module that was ALREADY warn/fail; an "ok" module
    # crossing into "warn" without reaching "fail" is a separate, deliberately
    # unguarded case (R1 only fires on a *fail*-count increase).
    baseline = {"modules": {"ok.py": prod_module(level="ok", cc_max=5)}}
    current = {"modules": {"ok.py": prod_module(level="warn", cc_max=13)}}
    assert compare(baseline, current, {}) == []


def test_r2_catches_sum_regression():
    baseline = {"modules": {"legacy.py": prod_module(level="warn", broad_catch=1,
                                                      silent_catch=0)}}
    current = {"modules": {"legacy.py": prod_module(level="warn", broad_catch=1,
                                                     silent_catch=2)}}
    hits = only(compare(baseline, current, {}), "R2 broad_catch")
    assert len(hits) == 1 and hits[0]["before"] == 1 and hits[0]["after"] == 3


def test_r2_loc_allows_ten_percent_growth():
    baseline = {"modules": {"legacy.py": prod_module(level="warn", loc=100)}}
    current_ok = {"modules": {"legacy.py": prod_module(level="warn", loc=110)}}
    current_bad = {"modules": {"legacy.py": prod_module(level="warn", loc=111)}}
    assert only(compare(baseline, current_ok, {}), "R2 loc") == []
    hits = only(compare(baseline, current_bad, {}), "R2 loc")
    assert len(hits) == 1 and hits[0]["before"] == 100 and hits[0]["after"] == 111


def test_r2_commits_and_churn_changes_are_never_violations():
    baseline = {"modules": {"legacy.py": prod_module(level="warn", commits=1,
                                                      churn_lines=5,
                                                      hotspot_score=0.01)}}
    current = {"modules": {"legacy.py": prod_module(level="warn", commits=40,
                                                     churn_lines=9000,
                                                     hotspot_score=0.9)}}
    assert compare(baseline, current, {}) == []


# ── R3: новая функция ────────────────────────────────────────────────────────

def test_r3_new_function_cc_11_is_a_violation():
    baseline = {"modules": {"a.py": prod_module(funcs=[["old", 1, 5]])}}
    current = {"modules": {"a.py": prod_module(
        funcs=[["old", 1, 5], ["new_fn", 11, 10]])}}
    hits = only(compare(baseline, current, {}), "R3")
    assert len(hits) == 1
    assert hits[0]["file"] == "a.py:new_fn"


def test_r3_new_function_cc_10_is_ok():
    baseline = {"modules": {"a.py": prod_module(funcs=[["old", 1, 5]])}}
    current = {"modules": {"a.py": prod_module(
        funcs=[["old", 1, 5], ["new_fn", 10, 10]])}}
    assert only(compare(baseline, current, {}), "R3") == []


def test_r3_new_function_41_lines_is_a_violation():
    baseline = {"modules": {"a.py": prod_module(funcs=[])}}
    current = {"modules": {"a.py": prod_module(funcs=[["new_fn", 3, 41]])}}
    hits = only(compare(baseline, current, {}), "R3")
    assert len(hits) == 1 and "loc=41" in hits[0]["after"]


def test_r3_new_function_40_lines_is_ok():
    baseline = {"modules": {"a.py": prod_module(funcs=[])}}
    current = {"modules": {"a.py": prod_module(funcs=[["new_fn", 3, 40]])}}
    assert only(compare(baseline, current, {}), "R3") == []


def test_r3_renamed_function_is_not_new_if_qualname_unchanged():
    # moving a method to a different line must not look like a new function.
    baseline = {"modules": {"a.py": prod_module(funcs=[["Bot.handle", 12, 35]])}}
    current = {"modules": {"a.py": prod_module(funcs=[["Bot.handle", 12, 35]])}}
    assert compare(baseline, current, {}) == []


def test_r3_brand_new_file_checks_every_function():
    baseline = {"modules": {}}
    current = {"modules": {"new.py": prod_module(
        funcs=[["small", 2, 5], ["too_big", 1, 41]])}}
    hits = only(compare(baseline, current, {}), "R3")
    assert len(hits) == 1 and hits[0]["file"] == "new.py:too_big"


def test_r3_ignores_test_files():
    baseline = {"modules": {}}
    current = {"modules": {"tests/unit/test_x.py":
                           {"test": True, "level": "ok", "cc_max": 1,
                            "func_loc_max": 1, "nest_max": 1, "broad_catch": 0,
                            "silent_catch": 0, "loc": 5,
                            "funcs": [["huge", 99, 999]]}}}
    assert compare(baseline, current, {}) == []


# ── R4: allow-regression ─────────────────────────────────────────────────────

def test_r4_allow_regression_suppresses_and_prints_reason():
    baseline = {"modules": {"legacy.py": prod_module(level="warn", cc_max=15)}}
    current = {"modules": {"legacy.py": prod_module(level="warn", cc_max=20)}}
    violations = compare(baseline, current, {"legacy.py": "тестовое послабление"})
    assert len(violations) == 1
    v = violations[0]
    assert v["allowed"] is True
    assert v["reason"] == "тестовое послабление"
    line = code_metrics._format_violation(v)
    assert "разрешено: тестовое послабление" in line


def test_r4_allow_regression_is_per_file_not_global():
    baseline = {"modules": {
        "a.py": prod_module(level="warn", cc_max=15),
        "b.py": prod_module(level="warn", cc_max=15),
    }}
    current = {"modules": {
        "a.py": prod_module(level="warn", cc_max=20),
        "b.py": prod_module(level="warn", cc_max=20),
    }}
    violations = compare(baseline, current, {"a.py": "ok for a only"})
    failed = [v for v in violations if not v["allowed"]]
    allowed = [v for v in violations if v["allowed"]]
    assert len(failed) == 1 and failed[0]["file"] == "b.py"
    assert len(allowed) == 1 and allowed[0]["file"] == "a.py"


def test_r4_allow_regression_on_r3_new_function_matches_by_file_not_label():
    # R3 violations are labelled "file:qualname"; --allow-regression is given
    # a bare file path, so the lookup must key on the file, not the label.
    baseline = {"modules": {"a.py": prod_module(funcs=[])}}
    current = {"modules": {"a.py": prod_module(funcs=[["big", 20, 60]])}}
    violations = compare(baseline, current, {"a.py": "перенос legacy-функции"})
    assert len(violations) == 1
    assert violations[0]["allowed"] is True
    assert violations[0]["file"] == "a.py:big"


def main():
    tests = sorted((name, fn) for name, fn in globals().items()
                   if name.startswith("test_") and callable(fn))
    failures = 0
    for name, fn in tests:
        try:
            fn()
        except AssertionError as e:
            print("  [FAIL] %s\n         %s" % (name, e))
            failures += 1
        except Exception as e:  # noqa: BLE001 - report, don't hide, unexpected errors
            print("  [ERROR] %s\n         %s: %s" % (name, type(e).__name__, e))
            failures += 1
        else:
            print("  [ok]   %s" % name)
    print("\nпадений: %d из %d" % (failures, len(tests)))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
