#!/usr/bin/env python3
"""Версия Immich закреплена, а не берётся по плавающему тегу (D6/DEP-2).

ЗАЧЕМ ОН СУЩЕСТВУЕТ. Замер 2026-09-26: на устройстве работает Immich **2.7.5**, а
образ брался по плавающему тегу — `${IMMICH_VERSION:-release}`. Обычный
`docker compose pull` (или пересоздание контейнера на новой машине, где .env ещё нет)
поднял бы ЛЮБУЮ версию, включая мажорную, и сделал бы это молча. Immich при старте сам
мигрирует схему БД, а миграции в нём необратимы: откатить образ, не откатив дамп БД,
нельзя. Поэтому версия закреплена на v2.7.5 — и здесь проверяется, что она закреплена.

Проверяется две вещи:
1) в самих файлах compose нет плавающего `release`-тега у образов Immich;
2) ворота (`scripts/quality/preflight.sh`, раздел 7б) это действительно ловят:
   плавающий тег Immich — `bad` (ворота краснеют), а `:latest` у netdata/portainer/samba
   — пока только `warn` (отдельная задача DEP-2; покрасневшие ворота начали бы обходить).
   Для этого ворота гоняются на дереве-фикстуре в режиме `--images-only`.

Запуск: python3 tests/unit/test_immich_pinned_version.py   (Python 3.6+, без pytest)
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", line_buffering=True)

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

# Файлы, в которых живут образы Immich. Список явный: если появится третий compose
# с Immich, тест должен это заметить, а не промолчать.
IMMICH_COMPOSES = (
    "docker/compose/docker-compose.immich.yml",
    "docker/compose/docker-compose.immich-ml-rog.yml",
    "docker/compose/docker-compose.stage1.yml",
)

PINNED = "v2.7.5"


def read(rel):
    with io.open(os.path.join(REPO, rel), encoding="utf-8") as fh:
        return fh.read()


def run_gate(files):
    """Прогнать ворота в режиме --images-only на дереве-фикстуре.

    files — словарь {имя файла: содержимое}. Скрипт ворот копируется как есть и сам
    делает `cd` в корень фикстуры, поэтому больше в дереве ничего не нужно.
    Возвращает (код возврата, объединённый вывод).
    """
    tmp = tempfile.mkdtemp()
    try:
        qdir = os.path.join(tmp, "scripts", "quality")
        os.makedirs(qdir)
        shutil.copy(os.path.join(REPO, "scripts", "quality", "preflight.sh"),
                    os.path.join(qdir, "preflight.sh"))
        cdir = os.path.join(tmp, "docker", "compose")
        os.makedirs(cdir)
        for name, body in files.items():
            with io.open(os.path.join(cdir, name), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(body)
        bash = shutil.which("bash") or "bash"
        # encoding задаём явно: ворота печатают по-русски в UTF-8, а `universal_newlines`
        # без него декодирует вывод локальной кодировкой Windows (cp1251) — и проверка
        # русских слов в выводе падала бы на ровном месте.
        p = subprocess.run([bash, os.path.join(qdir, "preflight.sh"), "--images-only"],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           encoding="utf-8", errors="replace")
        return p.returncode, p.stdout
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


FLOATING_IMMICH = (
    "services:\n"
    "  immich-server:\n"
    "    image: ghcr.io/immich-app/immich-server:${IMMICH_VERSION:-release}\n"
)

PINNED_IMMICH = (
    "services:\n"
    "  immich-server:\n"
    "    image: ghcr.io/immich-app/immich-server:${IMMICH_VERSION:-" + PINNED + "}\n"
)

OTHER_LATEST = (
    "services:\n"
    "  netdata:\n"
    "    image: netdata/netdata:latest\n"
)


class ImmichVersionPinned(unittest.TestCase):

    # ── 1. Файлы в репозитории ─────────────────────────────────────────────────

    def test_immich_images_are_pinned_to_measured_version(self):
        # Замер 2026-09-26: /api/server/version → 2.7.5. Дефолт обязан совпадать с тем,
        # что реально работает, иначе деплой «на пустом .env» приедет не туда.
        seen = 0
        for rel in IMMICH_COMPOSES:
            text = read(rel)
            for line in text.splitlines():
                if "image:" not in line or "immich" not in line.lower():
                    continue
                seen += 1
                self.assertIn(PINNED, line, "образ Immich без закреплённой версии: %s: %s" % (rel, line.strip()))
                self.assertNotIn(":-release", line, "плавающий тег вернулся: %s: %s" % (rel, line.strip()))
                self.assertNotIn(":latest", line, "плавающий тег вернулся: %s: %s" % (rel, line.strip()))
        self.assertGreater(seen, 0, "образы Immich не найдены — тест ничего не проверил")

    def test_no_immich_service_uses_floating_tag_in_any_compose(self):
        # Ловушка на будущее: новый compose-файл с Immich тоже обязан быть закреплён.
        offenders = []
        cdir = os.path.join(REPO, "docker", "compose")
        for name in sorted(os.listdir(cdir)):
            if not name.endswith(".yml"):
                continue
            for num, line in enumerate(read("docker/compose/" + name).splitlines(), 1):
                if "image:" not in line or "immich" not in line.lower():
                    continue
                if ":-release" in line or ":latest" in line:
                    offenders.append("%s:%d" % (name, num))
        self.assertEqual([], offenders, "плавающий тег у Immich: " + ", ".join(offenders))

    # ── 2. Ворота действительно ловят ──────────────────────────────────────────

    def test_gate_fails_on_floating_immich_tag(self):
        rc, out = run_gate({"docker-compose.immich.yml": FLOATING_IMMICH})
        self.assertNotEqual(0, rc, "ворота пропустили плавающий тег Immich:\n" + out)
        self.assertIn("immich", out.lower())

    def test_gate_fails_on_latest_immich_tag(self):
        body = PINNED_IMMICH.replace(":-" + PINNED, ":latest")
        rc, out = run_gate({"docker-compose.immich.yml": body})
        self.assertNotEqual(0, rc, "ворота пропустили :latest у Immich:\n" + out)

    def test_gate_passes_on_pinned_immich(self):
        rc, out = run_gate({"docker-compose.immich.yml": PINNED_IMMICH})
        self.assertEqual(0, rc, "ворота покраснели на закреплённой версии:\n" + out)

    def test_gate_warns_but_passes_on_other_latest_images(self):
        # DEP-2 (netdata/portainer/samba) ещё не сделана: ворота обязаны предупредить,
        # но не заблокировать работу — иначе их начнут обходить через --no-verify.
        rc, out = run_gate({"docker-compose.immich.yml": PINNED_IMMICH,
                            "docker-compose.monitoring.yml": OTHER_LATEST})
        self.assertEqual(0, rc, "ворота заблокировали работу из-за :latest у не-Immich образа:\n" + out)
        self.assertIn("latest", out)

    def test_gate_reports_nothing_to_check(self):
        # Пустое дерево не должно выглядеть как успешная проверка (тишина ≠ успех).
        # Слова в выводе не цитируем: проверяем, что предупреждение вообще есть.
        rc, out = run_gate({})
        self.assertEqual(0, rc, out)
        self.assertIn("docker/compose/*.yml", out)


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=1).result
    bad = len(result.failures) + len(result.errors)
    if bad:
        print("[FAIL] падений: %d" % bad)
    sys.exit(1 if bad else 0)
