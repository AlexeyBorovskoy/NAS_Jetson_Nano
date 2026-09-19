#!/usr/bin/env python3
"""Укрепление контейнеров (этап C, задачи C8/C10).

ЗАЧЕМ ОН СУЩЕСТВУЕТ. Аудит 2026-09-19 (NAS-SEC-006, `audit_new` G16): все контейнеры
работали от root; Portainer (полный доступ к Docker = root хоста) слушал
`0.0.0.0:9000/9443` — любой, кто знает пароль Wi-Fi, получал страницу входа в root.

Зафиксировано:
* LLM Gateway — не от root (он ходит в интернет и принимает запросы из LAN/VPN);
* Portainer — только на 127.0.0.1 (доступ: `ssh -L 9443:127.0.0.1:9443 admin@192.168.0.50`).

Осознанные исключения (записаны, а не забыты):
* NAS API остаётся от root: он держит `/var/run/docker.sock`, а доступ к сокету
  равносилен root при любом UID — смена пользователя дала бы видимость, не защиту.
  Настоящая мера — прокси сокета с allowlist (план F);
* Netdata пока слушает LAN: на `192.168.0.50:19999` смотрит монитор Uptime Kuma
  (настройки в её базе, не в git). Решение — D5/R5-02 (консолидация мониторинга).
Запуск: python3 tests/unit/test_container_hardening.py
"""
import io
import os
import re
import sys
import unittest

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", line_buffering=True)

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def read(rel):
    with open(os.path.join(REPO, rel), encoding="utf-8") as fh:
        return fh.read()


class Hardening(unittest.TestCase):

    def test_gateway_runs_as_non_root(self):
        users = re.findall(r"(?m)^\s*USER\s+(\S+)", read("services/llm-gateway/Dockerfile"))
        self.assertTrue(users, "в Dockerfile шлюза нет USER")
        self.assertNotIn(users[-1], ("root", "0", "0:0"))

    def test_portainer_bound_to_localhost(self):
        text = read("docker/compose/docker-compose.monitoring.yml")
        block = text[text.index("portainer"):]
        ports = re.findall(r'-\s*"([^"]*:(?:9000|9443))"', block)
        self.assertTrue(ports, "порты Portainer не найдены")
        for p in ports:
            self.assertTrue(p.startswith("127.0.0.1:"), "Portainer открыт наружу: " + p)


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=1).result
    bad = len(result.failures) + len(result.errors)
    if bad:
        print("[FAIL] падений: %d" % bad)
    sys.exit(1 if bad else 0)
