#!/usr/bin/env python3
"""Code metrics baseline for the audit (docs/audit/<date>_code_audit/).

Measures Python (ast) and shell (line heuristics) sources tracked by git,
plus git churn. No third-party dependencies: lizard/radon/jscpd are not
installed on the workstation and the audit forbids installing tools without
the owner's consent.

Usage: python scripts/quality/code_metrics.py --out baseline.json [--summary]
Metric definitions are written into the JSON ("definitions") so numbers stay
comparable between sessions.
"""
import argparse
import ast
import datetime as dt
import hashlib
import io
import json
import re
import subprocess
import sys
import tokenize
from collections import defaultdict
from pathlib import Path

EXCLUDE_TOP = {"archive", "research", "kaggle", "tools", "docs", "DNS",
               "assets", "artifacts"}
DATE_RE = re.compile(r"\b(\d{2}\.\d{2}\.\d{4}|20\d{2}-\d{2}-\d{2}|\d{1,2}\.\d{2}(?!\.\d))\b")
STRICT_DATE_RE = re.compile(r"\b(\d{2}\.\d{2}\.20\d{2}|20\d{2}-\d{2}-\d{2})\b")
TODO_RE = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b")
BUG_RE = re.compile(r"\b(fix|bug|hotfix|revert)|почин|исправ|откат", re.I)
LOG_ATTRS = {"debug", "info", "warning", "warn", "error", "exception",
             "log", "critical"}
DUP_WINDOW = 6

THRESHOLDS = {
    "loc": [600, 1200], "func_loc": [60, 120], "cyclomatic": [12, 25],
    "nesting_depth": [4, 6], "func_params": [5, 8], "class_methods": [20, 35],
    "constructor_params": [8, 14], "constructor_state_fields": [12, 20],
    "catch_per_module": [3, 10], "dated_comments": [15, 40],
}
DEFINITIONS = {
    "loc": "non-blank lines that are not comments; Python docstrings excluded",
    "cyclomatic": "McCabe: 1 + if/elif/for/while/except/with-less; +1 per "
                  "boolean operand beyond first, ternary, comprehension if, "
                  "match case, assert",
    "nesting_depth": "max depth of if/for/while/try/with/match blocks in a function",
    "broad_catch": "bare except / except Exception / BaseException (py); "
                   "'|| true' and '|| :' (sh)",
    "silent_catch": "py handler whose body is only pass/continue/break/"
                    "return-None/logging calls; sh: '2>/dev/null' count",
    "dated_comments": "comment or docstring lines containing DD.MM.YYYY or "
                      "YYYY-MM-DD",
    "churn": "git log over full history (repo history starts 2026-05-31 after "
             "filter-repo; window < 12 months)",
    "hotspot_score": "(commits/max_commits) * (complexity/max_complexity); "
                     "complexity = sum cyclomatic (py) or loc/10 (sh)",
    "duplication": f"normalised {DUP_WINDOW}-line windows (strip, no blank/"
                   "comment) seen in >=2 places",
}


def git(*args):
    # Python 3.6 (the Jetson host): no capture_output/text keywords.
    out = subprocess.run(["git"] + list(args), stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, check=True).stdout
    return out.decode("utf-8", errors="replace")


def tracked_sources():
    out = []
    for f in git("ls-files").splitlines():
        top = f.split("/", 1)[0]
        if top in EXCLUDE_TOP:
            continue
        if f.endswith(".py") or f.endswith(".sh"):
            out.append(f)
    return out


# ── Python ────────────────────────────────────────────────────────────────
BRANCH = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler,
          ast.IfExp, ast.Assert)
BLOCK = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.With,
         ast.AsyncWith) + ((ast.Match,) if hasattr(ast, "Match") else ())


def cyclomatic(fn):
    c = 1
    for n in ast.walk(fn):
        if n is not fn and isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef,
                                          ast.Lambda)):
            continue
        if isinstance(n, BRANCH):
            c += 1
        elif isinstance(n, ast.BoolOp):
            c += len(n.values) - 1
        elif isinstance(n, ast.comprehension):
            c += len(n.ifs)
        elif hasattr(ast, "match_case") and isinstance(n, ast.match_case):
            c += 1
    return c


def nesting(node, depth=0):
    best = depth
    for ch in ast.iter_child_nodes(node):
        if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        d = depth + 1 if isinstance(ch, BLOCK) else depth
        best = max(best, nesting(ch, d))
    return best


def is_silent(handler):
    for st in handler.body:
        if isinstance(st, (ast.Pass, ast.Continue, ast.Break)):
            continue
        if isinstance(st, ast.Return) and (st.value is None or (
                isinstance(st.value, ast.Constant) and st.value.value in (None, False, "", 0))):
            continue
        if isinstance(st, ast.Expr) and isinstance(st.value, ast.Call):
            f = st.value.func
            name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            if name in LOG_ATTRS or name == "print":
                continue
        return False
    return True


def is_broad(handler):
    t = handler.type
    if t is None:
        return True
    names = t.elts if isinstance(t, ast.Tuple) else [t]
    return any(isinstance(x, ast.Name) and x.id in ("Exception", "BaseException")
               for x in names)


def py_code_lines(src, tree):
    doc = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef,
                          ast.AsyncFunctionDef)) and n.body:
            b = n.body[0]
            if isinstance(b, ast.Expr) and isinstance(b.value, ast.Constant) \
                    and isinstance(b.value.value, str):
                doc.update(range(b.lineno, b.end_lineno + 1))
    code, comments = set(), []
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.COMMENT:
            comments.append((tok.start[0], tok.string))
        elif tok.type not in (tokenize.NL, tokenize.NEWLINE, tokenize.INDENT,
                              tokenize.DEDENT, tokenize.ENDMARKER):
            for ln in range(tok.start[0], tok.end[0] + 1):
                if ln not in doc:
                    code.add(ln)
    doc_lines = [(ln, src.splitlines()[ln - 1]) for ln in sorted(doc)
                 if ln - 1 < len(src.splitlines())]
    return code, comments, doc_lines


def analyse_py(path, src):
    tree = ast.parse(src)
    code, comments, doc_lines = py_code_lines(src, tree)
    m = {"lang": "py", "loc": len(code), "functions": [], "classes": [],
         "broad_catch": [], "silent_catch": [], "dynamic": 0,
         "stringly_typed": 0, "magic_numbers": 0, "imports": [],
         "private_imports": []}
    text_lines = comments + doc_lines
    m["dated_comments"] = [ln for ln, t in text_lines if STRICT_DATE_RE.search(t)]
    m["todo"] = [ln for ln, t in comments if TODO_RE.search(t)]
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            a = n.args
            params = [p.arg for p in a.posonlyargs + a.args + a.kwonlyargs
                      if p.arg not in ("self", "cls")]
            defaults = list(a.defaults) + [d for d in a.kw_defaults if d is not None]
            bools = sum(1 for d in defaults if isinstance(d, ast.Constant)
                        and isinstance(d.value, bool))
            bools += sum(1 for p in a.args + a.kwonlyargs if isinstance(
                p.annotation, ast.Name) and p.annotation.id == "bool"
                and not any(isinstance(d, ast.Constant) and isinstance(d.value, bool)
                            for d in defaults))
            floc = sum(1 for ln in code if n.lineno <= ln <= n.end_lineno)
            m["functions"].append({"name": n.name, "line": n.lineno,
                                   "loc": floc, "cc": cyclomatic(n),
                                   "nest": nesting(n), "params": len(params),
                                   "bool_params": bools})
        elif isinstance(n, ast.ClassDef):
            meths = [b for b in n.body if isinstance(b, (ast.FunctionDef,
                                                          ast.AsyncFunctionDef))]
            init = next((b for b in meths if b.name == "__init__"), None)
            ctor_p = ctor_s = 0
            if init:
                ctor_p = len(init.args.args) - 1 + len(init.args.kwonlyargs)
                ctor_s = sum(1 for x in ast.walk(init) if isinstance(x, ast.Attribute)
                             and isinstance(x.ctx, ast.Store)
                             and getattr(x.value, "id", "") == "self")
            m["classes"].append({"name": n.name, "line": n.lineno,
                                 "loc": sum(1 for ln in code if n.lineno <= ln <= n.end_lineno),
                                 "methods": len(meths), "ctor_params": ctor_p,
                                 "ctor_state": ctor_s})
        elif isinstance(n, ast.ExceptHandler):
            if is_broad(n):
                m["broad_catch"].append(n.lineno)
            if is_silent(n):
                m["silent_catch"].append(n.lineno)
        elif isinstance(n, ast.Call) and getattr(n.func, "id", "") in (
                "getattr", "setattr", "hasattr"):
            m["dynamic"] += 1
        elif isinstance(n, ast.Name) and n.id == "Any":
            m["dynamic"] += 1
        elif isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant) \
                and isinstance(n.slice.value, str):
            m["stringly_typed"] += 1
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                and n.func.attr == "get" and n.args and isinstance(n.args[0], ast.Constant) \
                and isinstance(n.args[0].value, str):
            m["stringly_typed"] += 1
        elif isinstance(n, ast.Compare):
            for c in [n.left] + n.comparators:
                if isinstance(c, ast.Constant) and isinstance(c.value, (int, float)) \
                        and not isinstance(c.value, bool) and c.value not in (0, 1, -1, 2):
                    m["magic_numbers"] += 1
        elif isinstance(n, ast.ImportFrom) and n.module:
            mod = "." * n.level + n.module
            m["imports"].append(mod)
            # `from pkg import mod` imports a submodule; the resolver falls
            # back to `pkg` when `pkg.name` is not a module.
            m["imports"].extend(f"{mod}.{al.name}" for al in n.names)
            for al in n.names:
                if al.name.startswith("_") and not al.name.startswith("__"):
                    m["private_imports"].append({"line": n.lineno, "from": mod,
                                                 "name": al.name})
        elif isinstance(n, ast.ImportFrom) and n.level:
            for al in n.names:
                m["imports"].append("." * n.level + al.name)
        elif isinstance(n, ast.Import):
            m["imports"].extend(al.name for al in n.names)
    return m


# ── Shell ─────────────────────────────────────────────────────────────────
SH_FUNC = re.compile(r"^\s*(?:function\s+)?([A-Za-z_][\w:-]*)\s*\(\)\s*\{?\s*$|"
                     r"^\s*function\s+([A-Za-z_][\w:-]*)\s*\{?\s*$")


def analyse_sh(path, src):
    lines = src.splitlines()
    code_idx = [i for i, ln in enumerate(lines, 1)
                if ln.strip() and not ln.strip().startswith("#")]
    m = {"lang": "sh", "loc": len(code_idx), "functions": [], "classes": [],
         "broad_catch": [i for i, ln in enumerate(lines, 1)
                         if re.search(r"\|\|\s*(true|:)\b", ln) and not ln.strip().startswith("#")],
         "silent_catch": [i for i, ln in enumerate(lines, 1)
                          if "2>/dev/null" in ln and not ln.strip().startswith("#")],
         "dated_comments": [i for i, ln in enumerate(lines, 1)
                            if "#" in ln and STRICT_DATE_RE.search(ln.split("#", 1)[1])],
         "todo": [i for i, ln in enumerate(lines, 1) if "#" in ln and TODO_RE.search(ln)],
         "strict_mode": bool(re.search(r"set -[a-z]*e[a-z]*u|set -euo|set -eu", src)),
         "dynamic": src.count("eval "), "stringly_typed": 0, "magic_numbers": 0,
         "imports": [], "private_imports": []}
    i = 0
    while i < len(lines):
        mt = SH_FUNC.match(lines[i])
        if mt:
            name, start, j = mt.group(1) or mt.group(2), i + 1, i
            # Brace counting is fooled by ${...}, awk and heredocs; the
            # closing brace is the first "}" at the definition's indentation.
            indent = len(lines[i]) - len(lines[i].lstrip())
            j = i + 1
            while j < len(lines):
                ln = lines[j]
                if ln.strip() == "}" and len(ln) - len(ln.lstrip()) == indent:
                    break
                j += 1
            body = [k for k in code_idx if start <= k <= j + 1]
            nest = 0
            depth_ctl = 0
            for k in range(start, j + 1):
                w = re.sub(r"#.*$", "", lines[k - 1])
                depth_ctl += len(re.findall(r"\b(if|for|while|until|case)\b", w))
                depth_ctl -= len(re.findall(r"\b(fi|done|esac)\b", w))
                nest = max(nest, depth_ctl)
            cc = 1 + sum(len(re.findall(r"\b(if|elif|for|while|until)\b|&&|\|\||;;",
                                       re.sub(r"#.*$", "", lines[k - 1])))
                         for k in range(start, j + 1))
            m["functions"].append({"name": name, "line": start, "loc": len(body),
                                   "cc": cc, "nest": nest, "params": 0,
                                   "bool_params": 0})
            i = j
        i += 1
    return m


# ── Repo-level ────────────────────────────────────────────────────────────
def churn():
    out = git("log", "--numstat", "--format=%x00%s")
    stats = defaultdict(lambda: {"commits": 0, "lines": 0, "bug_commits": 0})
    for block in out.split("\x00")[1:]:
        lines = block.strip("\n").splitlines()
        subj, files = lines[0], lines[1:]
        bug = bool(BUG_RE.search(subj))
        for fl in files:
            parts = fl.split("\t")
            if len(parts) != 3:
                continue
            a, d, f = parts
            s = stats[f]
            s["commits"] += 1
            s["lines"] += (int(a) if a.isdigit() else 0) + (int(d) if d.isdigit() else 0)
            s["bug_commits"] += bug
    return stats


def norm_line(ln, lang):
    s = ln.strip()
    if not s or s.startswith("#") or (lang == "py" and s in ("(", ")", "]", "[", "{", "}", "):", "else:", "try:", "pass", "return")):
        return None
    if s in ("fi", "done", "}", "esac", "then", "else", "do", ";;"):
        return None
    return re.sub(r"\s+", " ", s)


def duplication(files):
    windows = defaultdict(list)
    norm = {}
    for f, (src, lang) in files.items():
        seq = [(i, n) for i, n in ((i, norm_line(ln, lang))
                                   for i, ln in enumerate(src.splitlines(), 1))
               if n is not None]
        norm[f] = seq
        for k in range(len(seq) - DUP_WINDOW + 1):
            h = hashlib.sha1("\n".join(x[1] for x in seq[k:k + DUP_WINDOW]).encode()).hexdigest()
            windows[h].append((f, k))
    dup_lines = defaultdict(set)
    pairs = defaultdict(int)
    for h, occ in windows.items():
        if len(occ) < 2:
            continue
        for f, k in occ:
            for x in norm[f][k:k + DUP_WINDOW]:
                dup_lines[f].add(x[0])
        fs = sorted({f for f, _ in occ})
        for a in range(len(fs)):
            for b in range(a + 1, len(fs)):
                pairs[(fs[a], fs[b])] += 1
    per_file = {f: len(dup_lines[f]) for f in files}
    total = sum(len(v) for v in norm.values())
    return per_file, total, sorted(((v, a, b) for (a, b), v in pairs.items()),
                                   reverse=True)


def service_root(f):
    p = f.split("/")
    if p[0] == "services" and len(p) > 2:
        return "/".join(p[:2])
    return None


def import_graph(mods):
    """Intra-service module graph for `app.*` style packages."""
    graph = defaultdict(set)
    by_root = defaultdict(dict)
    for f in mods:
        r = service_root(f)
        if r and f.endswith(".py"):
            rel = f[len(r) + 1:-3].replace("/", ".")
            if rel.endswith(".__init__"):
                rel = rel[:-9]
            by_root[r][rel] = f
    for f, m in mods.items():
        r = service_root(f)
        if not r or m["lang"] != "py":
            continue
        names = by_root[r]
        rel_self = f[len(r) + 1:-3].replace("/", ".")
        pkg = rel_self.rsplit(".", 1)[0] if "." in rel_self else ""
        for imp in m["imports"]:
            if imp.startswith("."):
                lvl = len(imp) - len(imp.lstrip("."))
                base = pkg.split(".")[: max(0, len(pkg.split(".")) - (lvl - 1))] if pkg else []
                imp = ".".join(base + [imp.lstrip(".")]) if imp.lstrip(".") else ".".join(base)
            cand = imp
            while cand:
                if cand in names and names[cand] != f:
                    graph[f].add(names[cand])
                    break
                cand = cand.rsplit(".", 1)[0] if "." in cand else ""
    return graph


def cycles(graph):
    idx, low, st, on, res, c = {}, {}, [], set(), [], [0]
    sys.setrecursionlimit(10000)

    def sc(v):
        idx[v] = low[v] = c[0]
        c[0] += 1
        st.append(v)
        on.add(v)
        for w in graph.get(v, ()):
            if w not in idx:
                sc(w)
                low[v] = min(low[v], low[w])
            elif w in on:
                low[v] = min(low[v], idx[w])
        if low[v] == idx[v]:
            comp = []
            while True:
                w = st.pop()
                on.discard(w)
                comp.append(w)
                if w == v:
                    break
            if len(comp) > 1:
                res.append(sorted(comp))
    for v in list(graph):
        if v not in idx:
            sc(v)
    return res


def level(v, key):
    w, f = THRESHOLDS[key]
    return "fail" if v > f else "warn" if v > w else "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--summary", action="store_true")
    a = ap.parse_args()
    files = tracked_sources()
    mods, srcs = {}, {}
    for f in files:
        src = Path(f).read_text(encoding="utf-8", errors="replace")
        lang = "py" if f.endswith(".py") else "sh"
        srcs[f] = (src, lang)
        try:
            mods[f] = analyse_py(f, src) if lang == "py" else analyse_sh(f, src)
        except SyntaxError as e:
            mods[f] = {"lang": lang, "error": str(e), "loc": 0, "functions": []}
    ch = churn()
    dup_per_file, dup_total, dup_pairs = duplication(srcs)
    graph = import_graph(mods)
    fan_in = defaultdict(int)
    for f, deps in graph.items():
        for d in deps:
            fan_in[d] += 1
    out_mods = {}
    for f, m in mods.items():
        fns = m.get("functions", [])
        cls = m.get("classes", [])
        is_test = f.startswith("tests/") or "/tests/" in f
        cx = sum(x["cc"] for x in fns) if m["lang"] == "py" else m["loc"] / 10
        flocs = sorted(x["loc"] for x in fns)
        rec = {
            "lang": m["lang"], "test": is_test, "loc": m["loc"],
            "functions": len(fns),
            "func_loc_max": max(flocs, default=0),
            "func_loc_p90": flocs[int(len(flocs) * 0.9)] if flocs else 0,
            "func_over_warn": sum(1 for x in fns if x["loc"] > THRESHOLDS["func_loc"][0]),
            "cc_max": max((x["cc"] for x in fns), default=0),
            "cc_sum": sum(x["cc"] for x in fns),
            "cc_over_warn": sum(1 for x in fns if x["cc"] > THRESHOLDS["cyclomatic"][0]),
            "nest_max": max((x["nest"] for x in fns), default=0),
            "params_max": max((x["params"] for x in fns), default=0),
            "bool_params": sum(x["bool_params"] for x in fns),
            "class_methods_max": max((c["methods"] for c in cls), default=0),
            "ctor_params_max": max((c["ctor_params"] for c in cls), default=0),
            "ctor_state_max": max((c["ctor_state"] for c in cls), default=0),
            "broad_catch": len(m.get("broad_catch", [])),
            "silent_catch": len(m.get("silent_catch", [])),
            "dated_comments": len(m.get("dated_comments", [])),
            "todo": len(m.get("todo", [])),
            "dynamic": m.get("dynamic", 0),
            "stringly_typed": m.get("stringly_typed", 0),
            "magic_numbers": m.get("magic_numbers", 0),
            "private_imports": m.get("private_imports", []),
            "fan_out": len(graph.get(f, ())), "fan_in": fan_in.get(f, 0),
            "dup_lines": dup_per_file.get(f, 0),
            "commits": ch[f]["commits"], "churn_lines": ch[f]["lines"],
            "bug_commits": ch[f]["bug_commits"], "complexity": round(cx, 1),
            "worst_functions": sorted(
                ({"name": x["name"], "line": x["line"], "loc": x["loc"], "cc": x["cc"],
                  "nest": x["nest"], "params": x["params"]} for x in fns),
                key=lambda x: (-x["cc"], -x["loc"]))[:5],
        }
        if "strict_mode" in m:
            rec["strict_mode"] = m["strict_mode"]
        if "error" in m:
            rec["parse_error"] = m["error"]
        rec["level"] = max((level(rec["loc"], "loc"), level(rec["func_loc_max"], "func_loc"),
                            level(rec["cc_max"], "cyclomatic"),
                            level(rec["nest_max"], "nesting_depth"),
                            level(rec["params_max"], "func_params"),
                            level(rec["broad_catch"] + rec["silent_catch"], "catch_per_module"),
                            level(rec["dated_comments"], "dated_comments")),
                           key=["ok", "warn", "fail"].index)
        out_mods[f] = rec
    prod = {f: r for f, r in out_mods.items() if not r["test"]}
    mc = max((r["commits"] for r in prod.values()), default=1) or 1
    mx = max((r["complexity"] for r in prod.values()), default=1) or 1
    for r in prod.values():
        r["hotspot_score"] = round((r["commits"] / mc) * (r["complexity"] / mx), 4)
    totals = {
        "files": len(out_mods), "prod_files": len(prod),
        "prod_loc": sum(r["loc"] for r in prod.values()),
        "test_loc": sum(r["loc"] for f, r in out_mods.items() if r["test"]),
        "prod_loc_py": sum(r["loc"] for r in prod.values() if r["lang"] == "py"),
        "prod_loc_sh": sum(r["loc"] for r in prod.values() if r["lang"] == "sh"),
        "warn": sum(r["level"] == "warn" for r in prod.values()),
        "fail": sum(r["level"] == "fail" for r in prod.values()),
        "dup_pct_all": round(100 * sum(dup_per_file.values()) / max(dup_total, 1), 2),
        "import_cycles": cycles(graph),
        "top_dup_pairs": [{"windows": v, "a": x, "b": y} for v, x, y in dup_pairs[:25]],
    }
    top10 = sorted(prod.values(), key=lambda r: -r["loc"])[:10]
    totals["top10_loc_share_pct"] = round(100 * sum(r["loc"] for r in top10) /
                                          max(totals["prod_loc"], 1), 1)
    head = git("rev-parse", "HEAD").strip()
    data = {"schema": 1, "repo": "NAS_Jetson_Nano", "commit": head,
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "stack": ["python", "bash", "docker-compose", "systemd"],
            "tool_versions": {"python": sys.version.split()[0], "metrics": "code_metrics.py v1"},
            "thresholds": THRESHOLDS, "definitions": DEFINITIONS,
            "modules": out_mods, "totals": totals}
    Path(a.out).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    if a.summary:
        t = totals
        print(f"prod files {t['prod_files']}, loc {t['prod_loc']} (py {t['prod_loc_py']}, "
              f"sh {t['prod_loc_sh']}), test loc {t['test_loc']}, warn {t['warn']}, "
              f"fail {t['fail']}, dup {t['dup_pct_all']}%, top10 share {t['top10_loc_share_pct']}%, "
              f"cycles {len(t['import_cycles'])}")


if __name__ == "__main__":
    main()
