from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Iterator
from pathlib import Path

_SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS checkpoints (
  source_key TEXT PRIMARY KEY, last_line INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS messages (
  message_id TEXT PRIMARY KEY,
  platform TEXT NOT NULL,
  channel TEXT NOT NULL,
  channel_profile TEXT NOT NULL,
  sender_id TEXT NOT NULL,
  text TEXT NOT NULL,
  normalized TEXT NOT NULL,
  relative_ms INTEGER NOT NULL,
  session_id TEXT NOT NULL,
  family_key TEXT NOT NULL,
  partition_name TEXT,
  reformulation INTEGER NOT NULL DEFAULT 0,
  source_key TEXT NOT NULL,
  source_line INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_sender_time ON messages(sender_id, relative_ms);
CREATE INDEX IF NOT EXISTS idx_messages_channel_time ON messages(channel, relative_ms);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_family ON messages(family_key);
CREATE TABLE IF NOT EXISTS scores (
  message_id TEXT NOT NULL,
  model TEXT NOT NULL,
  action TEXT NOT NULL,
  block_confidence REAL NOT NULL,
  PRIMARY KEY (message_id, model),
  FOREIGN KEY(message_id) REFERENCES messages(message_id)
);
CREATE TABLE IF NOT EXISTS candidates (
  message_id TEXT NOT NULL,
  bucket TEXT NOT NULL,
  priority REAL NOT NULL,
  PRIMARY KEY (message_id, bucket),
  FOREIGN KEY(message_id) REFERENCES messages(message_id)
);
CREATE TABLE IF NOT EXISTS dsu (node TEXT PRIMARY KEY, parent TEXT NOT NULL);
"""


class MiningStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(_SCHEMA)

    def close(self) -> None:
        self.connection.commit()
        self.connection.close()

    def __enter__(self) -> MiningStore:
        return self

    def __exit__(self, exc_type: object, *_args: object) -> None:
        if exc_type is None:
            self.connection.commit()
        else:
            self.connection.rollback()
        self.connection.close()

    def meta(self, key: str) -> str | None:
        row = self.connection.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return None if row is None else str(row["value"])

    def set_meta(self, key: str, value: str) -> None:
        self.connection.execute(
            "INSERT INTO meta(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )

    def checkpoint(self, source_key: str) -> int:
        row = self.connection.execute(
            "SELECT last_line FROM checkpoints WHERE source_key = ?", (source_key,)
        ).fetchone()
        return 0 if row is None else int(row["last_line"])

    def save_checkpoint(self, source_key: str, line_no: int) -> None:
        self.connection.execute(
            "INSERT INTO checkpoints(source_key,last_line) VALUES(?,?) "
            "ON CONFLICT(source_key) DO UPDATE SET last_line=excluded.last_line",
            (source_key, line_no),
        )

    def insert_message(self, values: tuple[object, ...]) -> None:
        self.connection.execute(
            "INSERT INTO messages(message_id,platform,channel,channel_profile,sender_id,text,"
            "normalized,"
            "relative_ms,session_id,family_key,reformulation,source_key,source_line) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            values,
        )

    def latest_channel(self, channel: str) -> sqlite3.Row | None:
        return self.connection.execute(
            "SELECT * FROM messages WHERE channel=? ORDER BY relative_ms DESC LIMIT 1",
            (channel,),
        ).fetchone()

    def recent_sender(self, sender_id: str, after_ms: int) -> list[sqlite3.Row]:
        return list(
            self.connection.execute(
                "SELECT * FROM messages WHERE sender_id=? AND relative_ms>=? "
                "ORDER BY relative_ms DESC LIMIT 20",
                (sender_id, after_ms),
            )
        )

    def iter_messages(self, partition: str | None = None) -> Iterator[sqlite3.Row]:
        if partition is None:
            query = "SELECT * FROM messages ORDER BY relative_ms, message_id"
            yield from self.connection.execute(query)
            return
        if partition not in {"development", "validation", "holdout"}:
            raise ValueError(f"unknown partition {partition!r}")
        query = (
            "SELECT * FROM messages WHERE partition_name=? "
            "ORDER BY relative_ms, message_id"
        )
        yield from self.connection.execute(query, (partition,))

    def session_start(self, session_id: str) -> int | None:
        row = self.connection.execute(
            "SELECT MIN(relative_ms) AS started FROM messages WHERE session_id=?",
            (session_id,),
        ).fetchone()
        return None if row is None or row["started"] is None else int(row["started"])

    def has_model_state(self) -> bool:
        query = (
            "SELECT EXISTS(SELECT 1 FROM scores LIMIT 1) "
            "OR EXISTS(SELECT 1 FROM candidates LIMIT 1) AS present"
        )
        row = self.connection.execute(query).fetchone()
        return bool(row["present"]) if row is not None else False

    def partition_counts(self) -> dict[str, int]:
        query = (
            "SELECT partition_name, COUNT(*) AS count FROM messages "
            "WHERE partition_name IS NOT NULL GROUP BY partition_name"
        )
        return {
            str(row["partition_name"]): int(row["count"])
            for row in self.connection.execute(query)
        }

    def add_score(self, message_id: str, model: str, action: str, confidence: float) -> None:
        self.connection.execute(
            "INSERT INTO scores(message_id,model,action,block_confidence) VALUES(?,?,?,?) "
            "ON CONFLICT(message_id,model) DO UPDATE SET action=excluded.action, "
            "block_confidence=excluded.block_confidence",
            (message_id, model, action, confidence),
        )

    def scores(self, message_id: str) -> list[sqlite3.Row]:
        return list(
            self.connection.execute(
                "SELECT model,action,block_confidence FROM scores "
                "WHERE message_id=? ORDER BY model",
                (message_id,),
            )
        )

    def add_candidates(self, rows: Iterable[tuple[str, str, float]]) -> None:
        self.connection.executemany(
            "INSERT INTO candidates(message_id,bucket,priority) VALUES(?,?,?) "
            "ON CONFLICT(message_id,bucket) DO UPDATE SET priority=MAX(priority,excluded.priority)",
            rows,
        )

    def context_rows(
        self, channel: str, relative_ms: int, limit: int, window_ms: int
    ) -> list[sqlite3.Row]:
        rows = self.connection.execute(
            "SELECT * FROM messages WHERE channel=? AND relative_ms<=? AND relative_ms>=? "
            "ORDER BY relative_ms DESC LIMIT ?",
            (channel, relative_ms, relative_ms - window_ms, limit),
        ).fetchall()
        return list(reversed(rows))

    def commit(self) -> None:
        self.connection.commit()
