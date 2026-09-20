"""Память разговора @бобик: последние реплики чата, только в оперативной памяти.

Спецификация: docs/superpowers/specs/2026-09-19-bobik-dialog-memory-design.md.
На диск ничего не пишется — переписка семьи не должна оседать на Jetson; перезапуск
контейнера = чистый лист. История уходит в шлюз полем `context`, где её так же
фильтрует redaction, а токены считаются в бюджете человека — поэтому пределы жёсткие.
"""
from __future__ import annotations

import time

MAX_TURNS = 10
IDLE_TTL = 30 * 60
MAX_CHARS_TURN = 500
MAX_CHARS_TOTAL = 3000


class DialogMemory:
    def __init__(self, max_turns=MAX_TURNS, idle_ttl=IDLE_TTL,
                 max_chars_turn=MAX_CHARS_TURN, max_chars_total=MAX_CHARS_TOTAL,
                 clock=time.time):
        self.max_turns = max_turns
        self.idle_ttl = idle_ttl
        self.max_chars_turn = max_chars_turn
        self.max_chars_total = max_chars_total
        self.clock = clock
        self._chats: dict = {}

    def _fresh(self, key: str):
        chat = self._chats.get(key)
        if chat is None:
            return None
        if self.clock() - chat["seen"] > self.idle_ttl:
            del self._chats[key]  # разговор протух: вечером не всплывёт утренняя тема
            return None
        return chat

    def add(self, key: str, speaker: str, text: str) -> None:
        text = " ".join((text or "").split())[: self.max_chars_turn]
        if not key or not text:
            return
        chat = self._fresh(key) or {"seen": self.clock(), "turns": []}
        speaker = (speaker or "Кто-то")[:40]
        chat["turns"].append((speaker, text))
        del chat["turns"][: -self.max_turns]
        chat["seen"] = self.clock()
        self._chats[key] = chat

    def history(self, key: str) -> str:
        chat = self._fresh(key)
        if not chat:
            return ""
        lines, total = [], 0
        for speaker, text in reversed(chat["turns"]):
            line = "%s: %s" % (speaker, text)
            if total + len(line) + 1 > self.max_chars_total:
                break  # старое вытесняем первым
            lines.append(line)
            total += len(line) + 1
        return "\n".join(reversed(lines))

    def forget(self, key: str) -> bool:
        return self._chats.pop(key, None) is not None


MEMORY = DialogMemory()
