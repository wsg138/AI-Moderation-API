from __future__ import annotations

import asyncio
from collections import OrderedDict, deque
from datetime import timedelta

from .models import ContextMessage


class RollingContextStore:
    def __init__(
        self,
        window_seconds: int,
        max_scopes: int,
        messages_per_scope: int,
        sender_messages: int,
        channel_messages: int,
    ) -> None:
        self._window = timedelta(seconds=window_seconds)
        self._max_scopes = max_scopes
        self._messages_per_scope = messages_per_scope
        self._sender_messages = sender_messages
        self._channel_messages = channel_messages
        self._scopes: OrderedDict[
            tuple[str, str, str | None], deque[ContextMessage]
        ] = OrderedDict()
        self._lock = asyncio.Lock()

    async def snapshot_for(self, current: ContextMessage) -> tuple[ContextMessage, ...]:
        async with self._lock:
            bucket = self._touch_scope(_scope_key(current), create=False)
            if bucket is None:
                return ()
            candidates = self._eligible(bucket, current)
            return self._select(candidates, current)

    async def record(self, message: ContextMessage) -> None:
        async with self._lock:
            key = _scope_key(message)
            bucket = self._touch_scope(key, create=True)
            assert bucket is not None
            bucket.append(message)
            while len(self._scopes) > self._max_scopes:
                self._scopes.popitem(last=False)

    def _touch_scope(
        self,
        key: tuple[str, str, str | None],
        create: bool,
    ) -> deque[ContextMessage] | None:
        bucket = self._scopes.pop(key, None)
        if bucket is None and create:
            bucket = deque(maxlen=self._messages_per_scope)
        if bucket is not None:
            self._scopes[key] = bucket
        return bucket

    def _eligible(
        self,
        bucket: deque[ContextMessage],
        current: ContextMessage,
    ) -> list[ContextMessage]:
        cutoff = current.occurred_at - self._window
        return [
            item
            for item in bucket
            if cutoff <= item.occurred_at <= current.occurred_at
        ]

    def _select(
        self,
        candidates: list[ContextMessage],
        current: ContextMessage,
    ) -> tuple[ContextMessage, ...]:
        selected: dict[str, ContextMessage] = {}
        same_sender = [item for item in candidates if item.sender_id == current.sender_id]
        for item in same_sender[-self._sender_messages :]:
            selected[item.external_message_id] = item
        for item in candidates[-self._channel_messages :]:
            selected[item.external_message_id] = item
        if current.reply_to_message_id:
            for item in reversed(candidates):
                if item.external_message_id == current.reply_to_message_id:
                    selected[item.external_message_id] = item
                    break
        return tuple(sorted(selected.values(), key=lambda item: item.occurred_at))


def _scope_key(message: ContextMessage) -> tuple[str, str, str | None]:
    return message.platform, message.scope_id, message.channel_id
