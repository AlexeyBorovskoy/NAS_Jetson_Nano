"""Архитектурный тест: роутеры NAS API больше не библиотека друг для друга (CQ-02).

docs/audit/2026-10-02_code_audit/REPORT.ru.md §4, §6: `app/routers/talk_bot.py` звал
приватные имена чужих роутеров (`system_mod._read_meminfo`, `photos_mod._immich_get`,
`from app.routers.talk import _OCS_HEADERS, _admin_auth, _ocs_post`), а
`app/telegram_bot.py` — приватную `app.routers.talk_bot._build_health` через ленивый
импорт. Переименование внутри роутера молча ломало бы чужой код, а тесты роутера
этого не видели — симптом был не в том месте, где причина.

Стадия 11 (PLAN.ru.md) вынесла эти имена в `app/services/*` как публичный API. Этот
тест читает исходники `app/` статически (`ast`, без импорта — никакого побочного
эффекта от конфигурации/сети) и проверяет три инварианта:

  (а) ни один модуль `app/` не импортирует и не вызывает `_`-имя другого модуля
      `app/` (никто не библиотека по приватным именам ни для кого);
  (б) ни один модуль, кроме `app/main.py` и самих `app/routers/*`, не импортирует
      `app.routers.*` — ни верхнеуровнево, ни лениво внутри функции;
  (в) `app/services/*` не импортируют `app.routers.*` и `app.telegram_bot`.

Пойманные здесь нарушения — ровно те 3 импорта и 10 вызовов, что перечислены в
REPORT.ru.md §4 (CQ-02) и воспроизведены ниже в тесте "на доисторическом коде"
(см. docstring test_rules_catch_the_original_cq02_violations).

Run: python -m pytest tests/nas_api -q
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = ROOT / "services" / "nas_jetson_nano-api" / "app"

# (импортирующий модуль, импортируемая цель) -> почему это допустимое исключение.
# Цель — либо точный dotted-путь модуля/имени, либо префикс с завершающей точкой.
ALLOWLIST = {
    (
        "app.telegram_bot", "app.routers.talk_bot",
    ): (
        "CQ-02: импортируется ТОЛЬКО публичный `talk_bot.answer` (не приватное имя — "
        "находка CQ-02 была про `_`-имена). `answer` — вершина всей Phase C-логики "
        "(_STATE, gate_reply, _ask_llm, remember, bobik_gate); перенести её означало "
        "бы вынести весь этот блок разом, а это отдельная, более рискованная задача, "
        "не входящая в перечень стадии 11 (PLAN.ru.md: только system/photos/talk/"
        "health-хелперы). Оставлено сознательно, см. REPORT.ru.md и отчёт стадии 11."
    ),
    (
        "app.services.home_health", "app.routers.storage",
    ): (
        "CQ-02: disk_info/backup_info в routers/storage.py уже публичные функции "
        "(не часть находки CQ-02 — та была про `_`-имена) и используются только для "
        "чтения. Перенос самого storage.py в сервисный слой — отдельная, не начатая "
        "задача (вне рамок стадии 11, PLAN.ru.md). Без этого исключения build_health() "
        "пришлось бы либо дублировать disk_info/backup_info, либо менять поведение — "
        "оба варианта запрещены постановкой задачи («логика не меняется ни на байт»)."
    ),
}


def _module_name(path: Path) -> str:
    rel = path.relative_to(APP_ROOT.parent)  # включает ведущий "app"
    parts = list(rel.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _iter_app_modules():
    for path in sorted(APP_ROOT.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        yield path, _module_name(path)


def _import_targets(tree: ast.AST):
    """Все dotted-пути, которые модуль импортирует (включая ленивые импорты внутри
    функций — ast.walk обходит всё дерево независимо от вложенности)."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            for alias in node.names:
                target = f"{base}.{alias.name}" if base else alias.name
                yield node.lineno, target


def _private_import_violations(tree: ast.AST, module: str) -> list[str]:
    """Правило (а), часть 1: `from app.X import _имя`."""
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "app" or node.module.startswith("app."):
                if node.module == module:
                    continue  # импорт из самого себя невозможен, но на всякий случай
                for alias in node.names:
                    if alias.name.startswith("_"):
                        out.append(
                            "%s:%d: `from %s import %s` — импорт приватного имени "
                            "чужого модуля" % (module, node.lineno, node.module, alias.name)
                        )
    return out


def _module_aliases(tree: ast.AST, module: str) -> dict:
    """local_name -> dotted-путь app-подмодуля, на который реально указывает файл
    (нужно для правила (а), часть 2: `alias._имя`). Отслеживаем только алиасы,
    которые существуют как файл app/.../*.py — иначе это не модуль, а обычный
    публичный объект (settings, admit, ...), и `_`-атрибутов у него не проверяем
    отдельно (это не межмодульная приватность в смысле CQ-02)."""
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            base = node.module
            if base == "app" or base.startswith("app."):
                for alias in node.names:
                    target = f"{base}.{alias.name}"
                    target_path = APP_ROOT.parent / Path(*target.split("."))
                    if (target_path.with_suffix(".py")).exists() or (target_path / "__init__.py").exists():
                        local = alias.asname or alias.name
                        aliases[local] = target
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "app" or alias.name.startswith("app."):
                    local = alias.asname or alias.name.split(".")[0]
                    target = alias.name if alias.asname else "app"
                    aliases[local] = target
    return aliases


def _private_attr_violations(tree: ast.AST, module: str) -> list[str]:
    """Правило (а), часть 2: `module_alias._имя` — звонок в приватное имя чужого
    модуля по алиасу (system_mod._read_meminfo(), photos_mod._immich_get(), ...)."""
    aliases = _module_aliases(tree, module)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr.startswith("_") and not node.attr.startswith("__"):
            base = node.value
            if isinstance(base, ast.Name) and base.id in aliases:
                target_module = aliases[base.id]
                if target_module != module:
                    out.append(
                        "%s:%d: `%s.%s` — обращение к приватному имени модуля %s"
                        % (module, node.lineno, base.id, node.attr, target_module)
                    )
    return out


def _is_allowed(importer: str, target: str) -> bool:
    for (allowed_importer, allowed_target), _reason in ALLOWLIST.items():
        if importer == allowed_importer and (target == allowed_target or target.startswith(allowed_target + ".")):
            return True
    return False


def _routers_as_library_violations(tree: ast.AST, module: str) -> list[str]:
    """Правило (б): кроме app/main.py и app/routers/*, никто не импортирует
    app.routers.* — ни на верхнем уровне, ни лениво внутри функции."""
    if module == "app.main" or module == "app.routers" or module.startswith("app.routers."):
        return []
    out = []
    for lineno, target in _import_targets(tree):
        if target == "app.routers" or target.startswith("app.routers."):
            if _is_allowed(module, target):
                continue
            out.append(
                "%s:%d: импортирует `%s` — не-роутер не должен звать роутер как "
                "библиотеку (CQ-02)" % (module, lineno, target)
            )
    return out


def _services_purity_violations(tree: ast.AST, module: str) -> list[str]:
    """Правило (в): app/services/* не импортируют app.routers.* и app.telegram_bot."""
    if not module.startswith("app.services."):
        return []
    out = []
    for lineno, target in _import_targets(tree):
        forbidden = target == "app.routers" or target.startswith("app.routers.") or \
            target == "app.telegram_bot" or target.startswith("app.telegram_bot.")
        if forbidden:
            if _is_allowed(module, target):
                continue
            out.append(
                "%s:%d: сервис импортирует `%s` — сервисный слой не должен "
                "зависеть от роутеров/бота (CQ-02)" % (module, lineno, target)
            )
    return out


def _all_violations() -> list[str]:
    out: list[str] = []
    for path, module in _iter_app_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        out += _private_import_violations(tree, module)
        out += _private_attr_violations(tree, module)
        out += _routers_as_library_violations(tree, module)
        out += _services_purity_violations(tree, module)
    return out


def test_no_private_cross_module_imports_or_calls():
    """Правило (а): ни `from app.X import _имя`, ни `alias._имя` между модулями."""
    violations = _all_violations()
    private_only = [v for v in violations if "приватн" in v]
    assert private_only == [], "\n" + "\n".join(private_only)


def test_only_main_and_routers_import_routers():
    """Правило (б): роутеры — не библиотека для не-роутеров."""
    violations = _all_violations()
    router_only = [v for v in violations if "как библиотеку" in v]
    assert router_only == [], "\n" + "\n".join(router_only)


def test_services_do_not_depend_on_routers_or_telegram_bot():
    """Правило (в): сервисный слой ниже роутеров и бота, а не наоборот."""
    violations = _all_violations()
    services_only = [v for v in violations if "сервисный слой" in v]
    assert services_only == [], "\n" + "\n".join(services_only)
