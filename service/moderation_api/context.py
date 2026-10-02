from __future__ import annotations

import asyncio
from collections import OrderedDict, deque
from datetime import timedelta

from .models import ContextMessage

ScopeKey = tuple[str, str, str | None]


class RollingContextStore:
    def __init__(
        self,
        window_seconds: int,
        max_scopes: int,
        messages_per_scope: int,
        sender_messages: int,
        channel_messages: int,
        linked_scopes: int = 16,
        intervening_messages: int = 20,
    ) -> None:
        self._window = timedelta(seconds=window_seconds)
        self._max_scopes = max_scopes
        self._messages_per_scope = messages_per_scope
        self._sender_messages = sender_messages
        self._channel_messages = channel_messages
        self._linked_scopes = linked_scopes
        self._intervening_messages = intervening_messages
        self._scopes: OrderedDict[ScopeKey, deque[ContextMessage]] = OrderedDict()
        self._relation_scopes: dict[str, OrderedDict[ScopeKey, None]] = {}
        self._event_ids: set[str] = set()
        self._canonical_ids: set[str] = set()
        self._lock = asyncio.Lock()

    async def snapshot_for(self, current: ContextMessage) -> tuple[ContextMessage, ...]:
        async with self._lock:
            keys = self._candidate_scopes(current)
            candidates = self._collect_candidates(keys, current)
            return self._select(candidates, current)

    async def record(self, message: ContextMessage) -> bool:
        async with self._lock:
            if self._is_duplicate(message):
                return False
            self._record_locked(message)
            return True

    async def rehydrate(self, messages: tuple[ContextMessage, ...]) -> int:
        count = 0
        for message in sorted(messages, key=lambda item: item.occurred_at):
            count += int(await self.record(message))
        return count

    async def remove(self, event_id: str) -> None:
        async with self._lock:
            self._remove_locked(event_id)

    def _record_locked(self, message: ContextMessage) -> None:
        key = _scope_key(message)
        bucket = self._touch_scope(key, create=True)
        assert bucket is not None
        if len(bucket) >= self._messages_per_scope:
            self._forget_message(bucket.popleft())
        bucket.append(message)
        self._event_ids.add(message.event_id)
        if message.canonical_message_id:
            self._canonical_ids.add(message.canonical_message_id)
        self._index_scope(key, message)
        self._evict_scopes()

    def _candidate_scopes(self, current: ContextMessage) -> tuple[ScopeKey, ...]:
        keys: OrderedDict[ScopeKey, None] = OrderedDict()
        keys[_scope_key(current)] = None
        for relation in _relation_keys(current):
            for key in self._relation_scopes.get(relation, ()):
                keys[key] = None
                if len(keys) >= self._linked_scopes:
                    return tuple(keys)
        return tuple(keys)

    def _collect_candidates(
        self,
        keys: tuple[ScopeKey, ...],
        current: ContextMessage,
    ) -> list[ContextMessage]:
        cutoff = current.occurred_at - self._window
        candidates: list[ContextMessage] = []
        for key in keys:
            bucket = self._touch_scope(key, create=False)
            if bucket is None:
                continue
            recent = list(bucket)[-self._intervening_messages :]
            candidates.extend(
                item
                for item in recent
                if cutoff <= item.occurred_at <= current.occurred_at
                and _related(item, current)
            )
        return _deduplicate(candidates)

    def _select(
        self,
        candidates: list[ContextMessage],
        current: ContextMessage,
    ) -> tuple[ContextMessage, ...]:
        selected: dict[str, ContextMessage] = {}
        self._add_sender_context(selected, candidates, current)
        self._add_scope_context(selected, candidates, current)
        strong = (item for item in candidates if _strong_relation(item, current))
        for item in strong:
            selected[item.event_id] = item
        ordered = sorted(selected.values(), key=lambda item: item.occurred_at)
        return tuple(ordered[-24:])

    def _add_sender_context(
        self,
        selected: dict[str, ContextMessage],
        candidates: list[ContextMessage],
        current: ContextMessage,
    ) -> None:
        same_sender = [item for item in candidates if _same_sender(item, current)]
        for item in same_sender[-self._sender_messages :]:
            selected[item.event_id] = item

    def _add_scope_context(
        self,
        selected: dict[str, ContextMessage],
        candidates: list[ContextMessage],
        current: ContextMessage,
    ) -> None:
        same_scope = [item for item in candidates if _scope_key(item) == _scope_key(current)]
        for item in same_scope[-self._channel_messages :]:
            selected[item.event_id] = item

    def _touch_scope(self, key: ScopeKey, create: bool) -> deque[ContextMessage] | None:
        bucket = self._scopes.pop(key, None)
        if bucket is None and create:
            bucket = deque()
        if bucket is not None:
            self._scopes[key] = bucket
        return bucket

    def _index_scope(self, key: ScopeKey, message: ContextMessage) -> None:
        for relation in _relation_keys(message):
            scopes = self._relation_scopes.setdefault(relation, OrderedDict())
            scopes.pop(key, None)
            scopes[key] = None
            while len(scopes) > self._linked_scopes:
                scopes.popitem(last=False)

    def _evict_scopes(self) -> None:
        while len(self._scopes) > self._max_scopes:
            key, bucket = self._scopes.popitem(last=False)
            for message in bucket:
                self._forget_message(message)
            self._drop_scope_from_indices(key)

    def _remove_locked(self, event_id: str) -> None:
        for key, bucket in list(self._scopes.items()):
            removed = [item for item in bucket if item.event_id == event_id]
            if not removed:
                continue
            for item in removed:
                self._forget_message(item)
            kept = [item for item in bucket if item.event_id != event_id]
            self._replace_scope(key, kept)
            return

    def _replace_scope(self, key: ScopeKey, kept: list[ContextMessage]) -> None:
        if kept:
            self._scopes[key] = deque(kept)
            return
        self._scopes.pop(key, None)
        self._drop_scope_from_indices(key)

    def _forget_message(self, message: ContextMessage) -> None:
        self._event_ids.discard(message.event_id)
        canonical = message.canonical_message_id
        if canonical and not self._canonical_exists_elsewhere(canonical, message.event_id):
            self._canonical_ids.discard(canonical)

    def _canonical_exists_elsewhere(self, canonical: str, event_id: str) -> bool:
        return any(
            item.canonical_message_id == canonical and item.event_id != event_id
            for bucket in self._scopes.values()
            for item in bucket
        )

    def _drop_scope_from_indices(self, key: ScopeKey) -> None:
        empty: list[str] = []
        for relation, scopes in self._relation_scopes.items():
            scopes.pop(key, None)
            if not scopes:
                empty.append(relation)
        for relation in empty:
            self._relation_scopes.pop(relation, None)

    def _is_duplicate(self, message: ContextMessage) -> bool:
        if message.event_id in self._event_ids:
            return True
        canonical = message.canonical_message_id
        return canonical is not None and canonical in self._canonical_ids


def _scope_key(message: ContextMessage) -> ScopeKey:
    return message.platform.value, message.scope_id, message.channel_id


def _relation_keys(message: ContextMessage) -> tuple[str, ...]:
    keys = {f"sender:{message.platform.value}:{message.scope_id}:{message.sender_id}"}
    if message.conversation_id:
        keys.add(
            f"conversation:{message.platform.value}:{message.scope_id}:{message.conversation_id}"
        )
    for value in _platform_participants(message):
        keys.add(f"participant:{message.platform.value}:{message.scope_id}:{value}")
    for value in _identity_participants(message):
        keys.add(f"identity:{value}")
    return tuple(sorted(keys))


def _platform_participants(message: ContextMessage) -> set[str]:
    return {message.sender_id, *message.recipient_ids, *message.target_ids}


def _identity_participants(message: ContextMessage) -> set[str]:
    values = {*message.recipient_identity_ids, *message.target_identity_ids}
    if message.sender_identity_id:
        values.add(message.sender_identity_id)
    return values


def _related(prior: ContextMessage, current: ContextMessage) -> bool:
    if _scope_key(prior) == _scope_key(current):
        return True
    if _explicit_reply(prior, current) or _same_conversation(prior, current):
        return True
    if _same_platform_sender(prior, current):
        return True
    if _same_platform_relationship(prior, current):
        return True
    return _linked_cross_platform_relationship(prior, current)


def _strong_relation(prior: ContextMessage, current: ContextMessage) -> bool:
    return (
        _explicit_reply(prior, current)
        or _same_conversation(prior, current)
        or _same_platform_sender(prior, current)
        or _same_platform_relationship(prior, current)
        or _linked_cross_platform_relationship(prior, current)
    )


def _explicit_reply(prior: ContextMessage, current: ContextMessage) -> bool:
    return current.reply_to_message_id == prior.external_message_id


def _same_conversation(prior: ContextMessage, current: ContextMessage) -> bool:
    return (
        prior.platform is current.platform
        and prior.scope_id == current.scope_id
        and prior.conversation_id is not None
        and prior.conversation_id == current.conversation_id
    )


def _same_platform_sender(prior: ContextMessage, current: ContextMessage) -> bool:
    return (
        prior.platform is current.platform
        and prior.scope_id == current.scope_id
        and prior.sender_id == current.sender_id
    )


def _same_sender(prior: ContextMessage, current: ContextMessage) -> bool:
    if prior.platform is current.platform and prior.sender_id == current.sender_id:
        return True
    return bool(
        prior.sender_identity_id
        and current.sender_identity_id
        and prior.sender_identity_id == current.sender_identity_id
    )


def _same_platform_relationship(prior: ContextMessage, current: ContextMessage) -> bool:
    if prior.platform is not current.platform or prior.scope_id != current.scope_id:
        return False
    prior_people = _platform_participants(prior)
    current_people = _platform_participants(current)
    return len(prior_people & current_people) >= 2


def _linked_cross_platform_relationship(
    prior: ContextMessage,
    current: ContextMessage,
) -> bool:
    if prior.platform is current.platform:
        return False
    if _linked_sender(prior, current):
        return True
    return len(_identity_participants(prior) & _identity_participants(current)) >= 2


def _linked_sender(prior: ContextMessage, current: ContextMessage) -> bool:
    return bool(
        prior.sender_identity_id
        and current.sender_identity_id
        and prior.sender_identity_id == current.sender_identity_id
    )


def _deduplicate(messages: list[ContextMessage]) -> list[ContextMessage]:
    by_event: dict[str, ContextMessage] = {}
    canonical_seen: set[str] = set()
    for message in sorted(messages, key=lambda item: item.occurred_at):
        canonical = message.canonical_message_id
        if canonical and canonical in canonical_seen:
            continue
        by_event[message.event_id] = message
        if canonical:
            canonical_seen.add(canonical)
    return list(by_event.values())
