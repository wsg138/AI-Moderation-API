from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from .privacy import stable_hash
from .store import MiningStore

_ALGORITHM = "sqlite-dsu-session-family-v2-bounded-session"


def _ensure_node(store: MiningStore, node: str) -> None:
    store.connection.execute(
        "INSERT OR IGNORE INTO dsu(node,parent) VALUES(?,?)",
        (node, node),
    )


def _find(store: MiningStore, node: str) -> str:
    _ensure_node(store, node)
    path: list[str] = []
    current = node
    while True:
        row = store.connection.execute("SELECT parent FROM dsu WHERE node=?", (current,)).fetchone()
        parent = current if row is None else str(row["parent"])
        if parent == current:
            break
        path.append(current)
        current = parent
    for child in path:
        store.connection.execute("UPDATE dsu SET parent=? WHERE node=?", (current, child))
    return current


def _union(store: MiningStore, left: str, right: str) -> None:
    left_root = _find(store, left)
    right_root = _find(store, right)
    if left_root == right_root:
        return
    parent, child = sorted((left_root, right_root))
    store.connection.execute("UPDATE dsu SET parent=? WHERE node=?", (parent, child))


def _partition(root: str, seed: str) -> str:
    slot = int(stable_hash(seed, root)[:8], 16) % 100
    if slot < 80:
        return "development"
    if slot < 90:
        return "validation"
    return "holdout"


def _existing_split(store: MiningStore, seed: str) -> dict[str, object] | None:
    existing_seed = store.meta("split_seed")
    if existing_seed is None:
        return None
    algorithm = store.meta("split_algorithm")
    if existing_seed != seed or algorithm != _ALGORITHM:
        raise ValueError("split is already frozen; seed/algorithm cannot be changed")
    return {"algorithm": algorithm, "seed": existing_seed, "counts": store.partition_counts()}


def finalize_splits(store: MiningStore, seed: str) -> dict[str, object]:
    existing = _existing_split(store, seed)
    if existing is not None:
        return existing
    if store.has_model_state():
        raise ValueError("cannot create splits after model scores or candidates exist")
    store.connection.execute("DELETE FROM dsu")
    for row in store.iter_messages():
        _union(store, "s:" + str(row["session_id"]), "f:" + str(row["family_key"]))
    store.commit()
    sessions = store.connection.execute(
        "SELECT DISTINCT session_id FROM messages ORDER BY session_id"
    )
    counts: Counter[str] = Counter()
    for row in sessions:
        session_id = str(row["session_id"])
        partition = _partition(_find(store, "s:" + session_id), seed)
        cursor = store.connection.execute(
            "UPDATE messages SET partition_name=? WHERE session_id=?",
            (partition, session_id),
        )
        counts[partition] += cursor.rowcount
    store.set_meta("split_seed", seed)
    store.set_meta("split_algorithm", _ALGORITHM)
    store.commit()
    return {"algorithm": _ALGORITHM, "seed": seed, "counts": dict(sorted(counts.items()))}


def split_manifest(store: MiningStore, path: Path) -> dict[str, object]:
    digest = hashlib.sha256()
    counts: Counter[str] = Counter()
    query = "SELECT message_id,partition_name FROM messages ORDER BY message_id"
    for row in store.connection.execute(query):
        partition = str(row["partition_name"] or "UNASSIGNED")
        counts[partition] += 1
        digest.update(f"{row['message_id']}\t{partition}\n".encode())
    manifest = {
        "algorithm": store.meta("split_algorithm"),
        "seed": store.meta("split_seed"),
        "assignment_sha256": digest.hexdigest(),
        "counts": dict(sorted(counts.items())),
    }
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest
