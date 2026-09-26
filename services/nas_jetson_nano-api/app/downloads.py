"""Домашняя качалка: закачки через aria2 по командам из чата.

Спецификация: docs/superpowers/specs/2026-09-19-home-downloader-design.md.
Решение владельца 2026-09-26: всё качается ТОЛЬКО на HDD, у каждого члена семьи своя
папка — недокачанное в `.incomplete/.u/<логин>/`, готовое хук aria2 переносит в
`Downloads/<логин>/`. SSD закачки не трогают (там Immich/Nextcloud).
Страж раз в 30 с держит запас на HDD (архив 1,4 ТБ).
"""
from __future__ import annotations

import asyncio
import base64
import ipaddress
import json
import logging
import os
import re
import socket
import time
import urllib.parse

import httpx

from app.config import settings

log = logging.getLogger("nas_jetson_nano_api.downloads")

GB = 1024 ** 3
DONE_HINT = "\\\\192.168.0.50\\hdd2tb\\Downloads"
USER_PREFIX = ".u"  # .incomplete/.u/<логин>/… — хуки отличают папку человека от каталога торрента
_LOGIN_RE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
HDD_MARKER = ".nas-hdd-marker"  # И6: в корне Downloads на HDD — признак реального монтирования
_LINK_RE = re.compile(r"(magnet:\?\S+|https?://\S+)", re.IGNORECASE)
_BAD_SUFFIXES = (".local", ".lan", ".internal", ".localdomain")
# 2130706433, 0x7f.1, 017700000001, 127.1 — такие формы понимают резолверы и HTTP-клиенты
_NUMERIC_HOST = re.compile(r"^((0x[0-9a-f]*|[0-9]+)\.){0,3}(0x[0-9a-f]*|[0-9]+)$")
_KEYS = ["gid", "status", "totalLength", "completedLength", "downloadSpeed",
         "files", "bittorrent", "followedBy", "errorMessage", "infoHash"]
# Рестарт aria2 (пересоздание контейнера, сбой) поднимает торрент из сессии с НОВЫМ GID:
# в сессии хранится magnet, описание скачивается заново (инцидент 2026-09-26). Такие
# записи журнала — «lost»: сверка находит их в очереди по info-hash (или имени) и
# переносит на новый GID; не нашла за час — честная ошибка с сообщением.
_ADOPTABLE = ("lost", "error")
LOST_GRACE = 3600
_RESUME_MARGIN = 5 * GB  # гистерезис стража: продолжаем, когда запас восстановлен с лихвой


class LinkError(ValueError):
    """Ссылку ставить нельзя; текст исключения показывается человеку."""


def fmt_size(n: int) -> str:
    if n >= GB:
        return "%.1f ГБ" % (n / GB)
    return "%d МБ" % (n // (1024 * 1024))


def _bad_ip(ip) -> bool:
    return (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
            or ip.is_multicast or ip.is_unspecified)


def parse_link(text: str) -> str:
    m = _LINK_RE.search(text or "")
    if not m:
        raise LinkError("нужна magnet- или http(s)-ссылка")
    link = m.group(1).rstrip(").,;»\"'")
    if link.lower().startswith("magnet:"):
        if "xt=urn:btih:" not in link.lower():
            raise LinkError("в magnet-ссылке нет xt=urn:btih")
        return link
    host = (urllib.parse.urlsplit(link).hostname or "").lower()
    if not host:
        raise LinkError("в ссылке нет адреса")
    if host == "localhost" or host.endswith(_BAD_SUFFIXES):
        raise LinkError("ссылки во внутреннюю сеть запрещены")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
        if _NUMERIC_HOST.match(host):
            try:
                ip = ipaddress.ip_address(socket.inet_aton(host))
            except (OSError, ValueError):
                raise LinkError("непонятный адрес в ссылке")
    if ip is not None and _bad_ip(ip):
        raise LinkError("ссылки во внутреннюю сеть запрещены")
    return link


def choose_target(size, ssd_free: int, hdd_free: int) -> str:
    """Всегда HDD (решение владельца 2026-09-26); SSD для закачек не используется."""
    hdd_room = hdd_free - settings.dl_hdd_min_free_gb * GB
    if size is None:
        if hdd_room > 0:
            return "hdd"
        raise LinkError("нет места на HDD")
    if size > hdd_room:
        raise LinkError("не помещается: нужно %s, на HDD доступно %s"
                        % (fmt_size(size), fmt_size(max(hdd_room, 0))))
    return "hdd"


def user_folder(user) -> str:
    """Папка человека — его логин из TELEGRAM_USERS; всё непохожее на логин — «family»."""
    return str(user) if user and _LOGIN_RE.match(str(user)) else "family"


def user_dir(user) -> str:
    return "%s/%s/%s" % (settings.dl_hdd_dir.rstrip("/"), USER_PREFIX, user_folder(user))


def done_hint(user) -> str:
    return DONE_HINT + "\\" + user_folder(user)


def _options(target: str, user="") -> dict:
    return {"dir": user_dir(user), "file-allocation": "none"}


def total_size(st: dict) -> int:
    """Размер закачки. У торрента на паузе aria2 отдаёт totalLength=0, хотя длины файлов
    уже известны (инцидент 2026-09-26: пять торрентов вечно ждали «размера»)."""
    size = int(st.get("totalLength") or 0)
    if size:
        return size
    return sum(int(f.get("length") or 0) for f in st.get("files") or [])


def _disk_free() -> tuple:
    # И6: HDD — внешний диск на ntfs-3g; примонтирован ли он на самом деле, вместо
    # пустого каталога-заглушки от Docker, проверяем маркером, а не только statvfs.
    if not os.path.exists(os.path.join(settings.dl_hdd_stat_path, HDD_MARKER)):
        raise OSError("HDD не смонтирован — нет %s" % HDD_MARKER)
    ssd = os.statvfs(settings.dl_ssd_stat_path)
    hdd = os.statvfs(settings.dl_hdd_stat_path)
    return ssd.f_bavail * ssd.f_frsize, hdd.f_bavail * hdd.f_frsize


async def _head_size(url: str):
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as c:
            r = await c.head(url)
        n = int(r.headers.get("content-length", "0"))
        return n or None
    except Exception:
        return None


async def _resolves_internal(host: str) -> bool:
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(host, None)
    except OSError:
        return False  # не резолвится — aria2 тоже не сможет, закачка упадёт сама
    for info in infos:
        try:
            if _bad_ip(ipaddress.ip_address(info[4][0].split("%")[0])):
                return True
        except ValueError:
            continue
    return False


def _name(st: dict, fallback: str = "") -> str:
    info = (st.get("bittorrent") or {}).get("info") or {}
    if info.get("name"):
        return info["name"]
    files = st.get("files") or []
    if files and files[0].get("path"):
        return os.path.basename(files[0]["path"])
    return fallback or st.get("gid", "?")


class Aria2:
    """aria2 JSON-RPC. Секрет — первым параметром (`token:…`), в журнал не пишется."""

    def __init__(self, url=None, secret=None, transport=None):
        self.url = url or settings.aria2_rpc_url
        self.secret = settings.aria2_rpc_secret if secret is None else secret
        self._transport = transport

    async def call(self, method: str, *params):
        body = {"jsonrpc": "2.0", "id": "nas", "method": "aria2." + method,
                "params": ["token:" + self.secret, *params]}
        async with httpx.AsyncClient(timeout=15, transport=self._transport) as c:
            r = await c.post(self.url, json=body)
        data = r.json()
        if "error" in data:
            raise RuntimeError("aria2: %s" % data["error"].get("message"))
        return data["result"]


class Ledger:
    """Учёт «GID → кто и откуда поставил»; атомарная запись, битый файл = пусто."""

    def __init__(self, path=None):
        self.path = path or settings.dl_ledger_file

    def load(self) -> dict:
        try:
            with open(self.path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def save(self, data: dict) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False)
        os.replace(tmp, self.path)


class Downloads:
    def __init__(self, aria2=None, ledger=None, head=None, disk_free=None, clock=time.time, resolve=None):
        self.aria2 = aria2 or Aria2()
        self.ledger = ledger or Ledger()
        self.head = head or _head_size
        self.disk_free = disk_free or _disk_free
        self.clock = clock
        self.resolve = resolve or _resolves_internal
        self._lock = asyncio.Lock()

    def _free(self) -> tuple:
        try:
            ssd, hdd = self.disk_free()
            return ssd, hdd, False
        except OSError:
            return 0, 0, True  # диск недоступен = места нет: страж остановит закачки

    def _record(self, gid: str, chat_id: int, user: str, name: str, state: str) -> None:
        data = self.ledger.load()
        data[gid] = {"chat_id": chat_id, "user": user, "name": name, "state": state,
                     "created": int(self.clock())}
        self.ledger.save(data)

    async def add_link(self, link: str, chat_id: int, user: str) -> str:
        if link.lower().startswith("magnet:"):
            async with self._lock:
                gid = await self.aria2.call("addUri", [link], {"dir": user_dir(user)})
                self._record(gid, chat_id, user, "magnet", "metadata")
            log.info("download queued", extra={"fields": {"user": user, "type": "magnet"}})
            return "⏬ Принял, получаю описание торрента…"
        name = os.path.basename(urllib.parse.urlsplit(link).path) or "файл"
        host = (urllib.parse.urlsplit(link).hostname or "").lower()
        if await self.resolve(host):
            return "❌ ссылки во внутреннюю сеть запрещены"
        size = await self.head(link)
        ssd, hdd, _ = self._free()
        try:
            target = choose_target(size, ssd, hdd)
        except LinkError as exc:
            return "❌ %s" % exc
        async with self._lock:
            meta = self.ledger.load().get("_meta", {})
            opts = _options(target, user)  # И4: file-allocation=none — место не предвыделяем
            wait_suffix = ""
            if meta.get("paused"):
                opts["pause"] = "true"
                wait_suffix = " — ждёт места"
            gid = await self.aria2.call("addUri", [link], opts)
            self._record(gid, chat_id, user, name, "active")
            if meta.get("paused"):
                data = self.ledger.load()
                data.setdefault("_meta", {}).setdefault("paused_gids", []).append(gid)
                self.ledger.save(data)
        log.info("download queued", extra={"fields": {"user": user, "type": "http",
                                                      "size": size, "target": target}})
        size_txt = fmt_size(size) if size else "размер неизвестен"
        return "⏬ Принял: %s — %s, на %s%s" % (name, size_txt, target.upper(), wait_suffix)

    async def add_torrent(self, data: bytes, chat_id: int, user: str) -> str:
        b64 = base64.b64encode(data).decode("ascii")
        async with self._lock:
            gid = await self.aria2.call("addTorrent", b64, [], {"pause": "true"})
            self._record(gid, chat_id, user, "torrent", "await_dir")
        log.info("download queued", extra={"fields": {"user": user, "type": "torrent"}})
        return "⏬ Принял торрент, проверяю размер…"

    async def _route_paused(self, gid: str, entry: dict, st: dict, msgs: list, meta: dict) -> None:
        status = st.get("status")
        if status in ("removed", "complete"):
            # И2: закачку отменили/она пропала, пока ждала маршрутизации — тихо, без RPC
            entry["state"] = "cancelled"
            return
        if status == "error":
            entry["state"] = "error"
            name = entry.get("name") or _name(st, entry.get("name", ""))
            msgs.append((entry["chat_id"], "❌ Не скачалось: %s — %s"
                         % (name, st.get("errorMessage") or "ошибка")))
            return
        size = total_size(st)
        if not size:
            return  # размер ещё неизвестен — подождём следующего такта
        name = _name(st, entry.get("name", ""))
        entry["name"] = name
        if st.get("infoHash"):
            entry["info_hash"] = st["infoHash"]
        ssd, hdd, _ = self._free()
        try:
            target = choose_target(size, ssd, hdd)
        except LinkError as exc:
            await self.aria2.call("forceRemove", gid)
            entry["state"] = "error"
            msgs.append((entry["chat_id"], "❌ %s: %s" % (name, exc)))
            return
        await self.aria2.call("changeOption", gid, _options(target, entry.get("user", "")))
        entry["state"] = "active"
        if meta.get("paused"):
            meta.setdefault("paused_gids", []).append(gid)  # снимет страж, когда место появится
        else:
            await self.aria2.call("unpause", gid)
        msgs.append((entry["chat_id"], "⏬ Качаю: %s — %s, на %s"
                     % (name, fmt_size(size), target.upper())))

    async def _tick_entries(self, data: dict, meta: dict, msgs: list) -> None:
        for gid in list(data):
            entry = data.get(gid)
            if entry is None or entry.get("state") in ("done", "error", "cancelled", "lost"):
                continue
            try:
                st = await self.aria2.call("tellStatus", gid, _KEYS)
            except RuntimeError:
                # GID пропал — чаще всего aria2 перезапустился; ищет _reconcile()
                entry["state"] = "lost"
                entry["lost_at"] = int(self.clock())
                continue
            try:
                await self._tick_one(gid, entry, st, data, meta, msgs)
            except RuntimeError:
                # И2: сбой RPC (changeOption/unpause/forceRemove и т.п.) на ОДНОЙ
                # записи не должен вешать такт целиком — остальные GID обрабатываются дальше.
                log.warning("такт: сбой на закачке %s — пропускаю", gid)
                (data.get(gid) or entry)["state"] = "error"

    async def _reconcile(self, data: dict, meta: dict, msgs: list) -> None:
        """Восстановление после рестарта aria2: чужие для журнала закачки в очереди
        сопоставляются с потерянными записями по info-hash, у старых записей — по имени."""
        lost = {g: e for g, e in data.items()
                if e.get("state") in _ADOPTABLE and e.get("name") not in ("", "magnet", "torrent")}
        if not lost:
            return
        queue = list(await self.aria2.call("tellActive", _KEYS))
        queue += list(await self.aria2.call("tellWaiting", 0, 1000, _KEYS))
        for st in queue:
            gid = st.get("gid")
            if gid in data or not ((st.get("bittorrent") or {}).get("info")):
                continue  # своя запись или magnet ещё без описания — подождём followedBy
            ih, nm = st.get("infoHash"), _name(st)
            old = next((g for g, e in lost.items()
                        if (ih and e.get("info_hash") == ih)
                        or (not e.get("info_hash") and e.get("name") == nm)), None)
            if old is None:
                continue
            entry = lost.pop(old)
            del data[old]
            entry.pop("lost_at", None)
            entry["state"] = "await_dir" if st.get("status") == "paused" else "active"
            data[gid] = entry
            log.info("закачка восстановлена после рестарта aria2",
                     extra={"fields": {"user": entry.get("user"), "old": old, "new": gid}})
            if entry["state"] == "await_dir":
                await self._route_paused(gid, entry, st, msgs, meta)
        now = int(self.clock())
        for e in lost.values():
            if e.get("state") == "lost" and now - e.get("lost_at", now) > LOST_GRACE:
                e["state"] = "error"
                msgs.append((e["chat_id"], "❌ Закачка потерялась после перезапуска качалки: %s — "
                             "пришлите ссылку ещё раз." % e.get("name", "?")))

    async def _tick_one(self, gid: str, entry: dict, st: dict, data: dict, meta: dict, msgs: list) -> None:
        if entry["state"] == "metadata":
            if st.get("status") == "complete" and st.get("followedBy"):
                new = st["followedBy"][0]
                data[new] = dict(entry, state="await_dir")
                del data[gid]
                st2 = await self.aria2.call("tellStatus", new, _KEYS)
                await self._route_paused(new, data[new], st2, msgs, meta)
            elif st.get("status") == "error":
                entry["state"] = "error"
                msgs.append((entry["chat_id"], "❌ Не скачалось: %s — %s"
                             % (entry["name"], st.get("errorMessage") or "ошибка")))
            return
        if entry["state"] == "await_dir":
            await self._route_paused(gid, entry, st, msgs, meta)
            return
        name = _name(st, entry.get("name", ""))
        if st.get("status") == "complete":
            entry["state"] = "done"
            msgs.append((entry["chat_id"], "✅ Готово: %s — %s" % (name, done_hint(entry.get("user", "")))))
        elif st.get("status") == "error":
            entry["state"] = "error"
            msgs.append((entry["chat_id"], "❌ Не скачалось: %s — %s"
                         % (name, st.get("errorMessage") or "ошибка")))
        elif st.get("status") == "removed":
            entry["state"] = "cancelled"

    async def tick(self) -> list:
        # И1: сообщения такта копятся в outbox и возвращаются целиком (старые
        # неотправленные + новые), пока их не подтвердят через ack() — иначе
        # недоступный на миг Telegram теряет уведомление насовсем.
        async with self._lock:
            msgs: list = []
            data = self.ledger.load()
            meta = data.pop("_meta", {})
            outbox = data.pop("_outbox", [])
            try:
                await self._tick_entries(data, meta, msgs)
                await self._reconcile(data, meta, msgs)
                await self._guard(data, meta, msgs)
            except httpx.HTTPError:
                log.warning("aria2 недоступен — такт пропущен")
            outbox.extend({"chat_id": c, "text": t} for c, t in msgs)
            data["_meta"] = meta
            data["_outbox"] = outbox
            self.ledger.save(data)
            return [(m["chat_id"], m["text"]) for m in outbox]

    async def ack(self, n: int) -> None:
        async with self._lock:
            data = self.ledger.load()
            outbox = data.get("_outbox", [])
            data["_outbox"] = outbox[n:]
            self.ledger.save(data)

    async def _guard(self, data: dict, meta: dict, msgs: list) -> None:
        ssd, hdd, disk_down = self._free()
        hdd_min = settings.dl_hdd_min_free_gb * GB
        chats = sorted({e["chat_id"] for e in data.values()
                        if e.get("state") in ("active", "metadata", "await_dir")})
        if disk_down or hdd < hdd_min:
            if not meta.get("paused"):
                gids = [st["gid"] for st in await self.aria2.call("tellActive", ["gid"])]
                gids += [st["gid"] for st in await self.aria2.call("tellWaiting", 0, 1000, ["gid", "status"])
                         if st.get("status") == "waiting"]
                for gid in gids:
                    await self.aria2.call("pause", gid)
                meta["paused"] = True
                meta["paused_gids"] = gids
                if disk_down:
                    # И6: диск (обычно HDD — маркер пропал) реально недоступен,
                    # это другая причина паузы, не «мало места»
                    text = "⏸ Пауза закачек — HDD недоступен."
                else:
                    text = "⏸ Пауза закачек — мало места (HDD: нужно ещё %s)." % fmt_size(hdd_min - hdd)
                msgs.extend((c, text) for c in chats)
        elif meta.get("paused") and hdd >= hdd_min + _RESUME_MARGIN:
            for gid in meta.get("paused_gids", []):
                try:
                    await self.aria2.call("unpause", gid)
                except RuntimeError:
                    pass  # закачку успели отменить
            meta["paused"] = False
            meta["paused_gids"] = []
            msgs.extend((c, "▶️ Место есть — продолжаю закачки.") for c in chats)

    async def _queue(self) -> list:
        active = await self.aria2.call("tellActive", _KEYS)
        waiting = await self.aria2.call("tellWaiting", 0, 50, _KEYS)
        return list(active) + list(waiting)

    async def list_text(self) -> str:
        items = await self._queue()
        ledger = self.ledger.load()
        lines = []
        for i, st in enumerate(items, 1):
            total = total_size(st)
            done = int(st.get("completedLength") or 0)
            pct = int(done * 100 / total) if total else 0
            speed = int(st.get("downloadSpeed") or 0) / (1024 * 1024)
            name = _name(st, (ledger.get(st["gid"]) or {}).get("name", ""))
            mark = " ⏸" if st.get("status") == "paused" else ""
            left = fmt_size(total - done) if total else "?"
            lines.append("%d. %s — %d%% · %.1f МБ/с · осталось %s%s"
                         % (i, name, pct, speed, left, mark))
        ssd, hdd, _ = self._free()
        free = "Свободно на HDD: %s (с учётом запаса)" % fmt_size(
            max(hdd - settings.dl_hdd_min_free_gb * GB, 0))
        if not lines:
            return "Закачек нет.\n" + free
        return "\n".join(lines + [free])

    async def cancel(self, n: int) -> str:
        items = await self._queue()
        if n < 1 or n > len(items):
            return "❌ Нет закачки с номером %d — посмотрите «@бобик закачки»." % n
        st = items[n - 1]
        async with self._lock:
            ledger = self.ledger.load()
            name = _name(st, (ledger.get(st["gid"]) or {}).get("name", ""))
            await self.aria2.call("forceRemove", st["gid"])
            if st["gid"] in ledger:
                ledger[st["gid"]]["state"] = "cancelled"
                self.ledger.save(ledger)
        return "🗑 Отменил: %s" % name
