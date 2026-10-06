from __future__ import annotations

import json
from pathlib import Path

from tools.chat_mining.ingest import ingest_paths
from tools.chat_mining.mining import load_scores, mine_candidates
from tools.chat_mining.parsing import parse_line
from tools.chat_mining.privacy import pseudonymize, redact_text
from tools.chat_mining.review import export_reviewed, write_review_queue
from tools.chat_mining.splitting import finalize_splits, split_manifest
from tools.chat_mining.store import MiningStore


def _check(condition: object) -> None:
    if not condition:
        raise AssertionError("test condition failed")


def _write(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _ingest(tmp_path: Path, lines: list[str]) -> tuple[Path, Path]:
    source = tmp_path / "latest.log"
    database = tmp_path / "mine.sqlite"
    _write(source, lines)
    with MiningStore(database) as store:
        ingest_paths(store, [source], progress_every=1000)
    return database, source


def test_parses_paper_and_discord_formats() -> None:
    paper = parse_line("[12:00:01] [Server thread/INFO]: <Steve> hello")
    discord = parse_line('[12:00:02] [#general] Alex: hi there')
    payload = parse_line(json.dumps({"author": "Kim", "content": "yo", "channel": "general"}))
    _check(paper is not None and paper.platform == "minecraft" and paper.sender == "Steve")
    _check(discord is not None and discord.platform == "discord" and discord.channel == "general")
    _check(payload is not None and payload.sender == "Kim")


def test_parses_finalized_enthusia_export_schema() -> None:
    payload = parse_line(
        json.dumps(
            {
                "date": "2026-10-05",
                "time": "16:42:01",
                "player": "Steve",
                "message": "hello there",
                "channel": "private",
                "recipient": "Alex",
                "source_platform": "minecraft",
            }
        )
    )
    if payload is None:
        raise AssertionError("expected finalized export record")
    _check(payload.platform == "minecraft")
    _check(payload.sender == "Steve")
    _check(payload.channel == "private")
    _check(payload.recipient == "Alex")
    _check(payload.timestamp_ms is not None)


def _export_record(
    player: str,
    message: str,
    channel: str,
    time: str,
    recipient: str | None = None,
) -> str:
    value = {
        "date": "2026-10-05",
        "time": time,
        "player": player,
        "message": message,
        "channel": channel,
        "source_platform": "minecraft",
    }
    if recipient is not None:
        value["recipient"] = recipient
    return json.dumps(value)


def test_private_export_context_is_pair_scoped_and_staff_is_excluded(tmp_path: Path) -> None:
    lines = [
        _export_record("A", "first dm", "private", "16:42:01", "B"),
        _export_record("B", "reply dm", "private", "16:42:02", "A"),
        _export_record("C", "unrelated dm", "private", "16:42:03", "D"),
        _export_record("Staffer", "staff-only note", "staff", "16:42:04"),
    ]
    database, _ = _ingest(tmp_path, lines)
    with MiningStore(database) as store:
        rows = list(store.iter_messages())
    _check(len(rows) == 3)
    _check(rows[0]["channel"] == rows[1]["channel"])
    _check(rows[2]["channel"] != rows[0]["channel"])
    _check(rows[0]["channel_profile"] == "minecraft_private")
    raw = database.read_bytes()
    _check(b"Staffer" not in raw)
    _check(b"staff-only note" not in raw)


def test_rejects_system_noise() -> None:
    _check(
        parse_line("[12:00:00] [Server thread/INFO]: Done (4.123s)! For help, type help")
        is None
    )
    _check(parse_line("[12:00:01] [Server thread/INFO]: UUID of player Steve is abc") is None)


def test_pseudonymization_and_redaction_are_deterministic() -> None:
    key = b"k" * 32
    first = pseudonymize("Steve", key)
    second = pseudonymize("Steve", key)
    _check(first == second)
    _check(first != pseudonymize("Alex", key))
    value = redact_text("mail me at a@example.com from 203.0.113.9 or 2606:4700:4700::1111")
    _check("a@example.com" not in value)
    _check("203.0.113.9" not in value)
    _check("2606:4700:4700::1111" not in value)


def test_ingest_excludes_private_channels_and_raw_identifiers(tmp_path: Path) -> None:
    database, _ = _ingest(
        tmp_path,
        [
            "[12:00:01] [#general] Lincoln: server is fun 203.0.113.9",
            "[12:00:02] [#staff-chat] Lincoln: private staff note",
        ],
    )
    raw = database.read_bytes()
    _check(b"Lincoln" not in raw)
    _check(b"203.0.113.9" not in raw)
    _check(b"staff-chat" not in raw)
    with MiningStore(database) as store:
        rows = list(store.iter_messages())
        _check(len(rows) == 1)
        _check(rows[0]["channel"].startswith("channel_"))
        _check(rows[0]["text"].endswith("<IP>"))


def test_exact_and_near_spam_deduplicate_but_reformulation_is_kept(tmp_path: Path) -> None:
    database, _ = _ingest(
        tmp_path,
        [
            "[12:00:01] [Server thread/INFO]: <Steve> meet at spawn now",
            "[12:00:02] [Server thread/INFO]: <Steve> meet at spawn now",
            "[12:00:10] [Server thread/INFO]: <Steve> meet at spawn pls",
        ],
    )
    with MiningStore(database) as store:
        rows = list(store.iter_messages())
    _check(len(rows) == 2)
    _check(int(rows[-1]["reformulation"]) == 1)


def test_same_platform_duplicate_text_in_different_channels_is_retained(
    tmp_path: Path,
) -> None:
    database, _ = _ingest(
        tmp_path,
        [
            _export_record("Steve", "same text", "global", "12:00:01"),
            _export_record("Steve", "same text", "private", "12:00:02", "Alex"),
        ],
    )
    with MiningStore(database) as store:
        rows = list(store.iter_messages())
    _check(len(rows) == 2)
    _check(rows[0]["channel"] != rows[1]["channel"])


def test_identity_map_deduplicates_cross_platform_mirror(tmp_path: Path) -> None:
    source = tmp_path / "relay.log"
    database = tmp_path / "mine.sqlite"
    identities = tmp_path / "identities.json"
    _write(
        source,
        [
            "[12:00:01] [Server thread/INFO]: <SteveMC> hello everyone",
            "[12:00:02] [#general] SteveDiscord: hello everyone",
        ],
    )
    identities.write_text(json.dumps({"SteveMC": "person1", "SteveDiscord": "person1"}))
    with MiningStore(database) as store:
        stats = ingest_paths(store, [source], identities, progress_every=1000)
    _check(stats.stored == 1)
    _check(stats.duplicates == 1)


def test_context_window_is_bounded(tmp_path: Path) -> None:
    database, _ = _ingest(
        tmp_path,
        [
            "[12:00:01] [Server thread/INFO]: <A> first message",
            "[12:00:02] [Server thread/INFO]: <B> second message",
            "[12:00:03] [Server thread/INFO]: <A> third message",
        ],
    )
    with MiningStore(database) as store:
        target = list(store.iter_messages())[-1]
        rows = store.context_rows(target["channel"], target["relative_ms"], 2, 120_000)
    _check([row["text"] for row in rows] == ["second message", "third message"])


def test_group_aware_split_keeps_surface_variants_together(tmp_path: Path) -> None:
    database, _ = _ingest(
        tmp_path,
        [
            "[12:00:01] [Server thread/INFO]: <A> build the TNT cannon",
            "[12:05:01] [Server thread/INFO]: <B> BUILD THE TNT CANNON!!!",
        ],
    )
    with MiningStore(database) as store:
        finalize_splits(store, "seed-1")
        rows = list(store.iter_messages())
    _check(rows[0]["session_id"] != rows[1]["session_id"])
    _check(rows[0]["partition_name"] == rows[1]["partition_name"])


def test_split_manifest_is_deterministic(tmp_path: Path) -> None:
    database, _ = _ingest(tmp_path, ["[12:00:01] [Server thread/INFO]: <A> hello there friend"])
    one = tmp_path / "one.json"
    two = tmp_path / "two.json"
    with MiningStore(database) as store:
        finalize_splits(store, "same-seed")
        first = split_manifest(store, one)
        finalize_splits(store, "same-seed")
        second = split_manifest(store, two)
    _check(first == second)
    _check(one.read_bytes() == two.read_bytes())


def test_holdout_rejects_model_scores(tmp_path: Path) -> None:
    database, _ = _ingest(tmp_path, ["[12:00:01] [Server thread/INFO]: <A> ordinary message"])
    scores = tmp_path / "scores.jsonl"
    with MiningStore(database) as store:
        row = list(store.iter_messages())[0]
        store.connection.execute("UPDATE messages SET partition_name='holdout'")
        store.commit()
        score = {
            "message_id": row["message_id"],
            "model": "m",
            "action": "ALLOW",
            "block_confidence": 0.1,
        }
        _write(scores, [json.dumps(score)])
        try:
            load_scores(store, scores)
        except ValueError as exc:
            _check("protected holdout" in str(exc))
        else:
            raise AssertionError("expected protected holdout rejection")


def test_mining_and_review_queue_include_model_evidence(tmp_path: Path) -> None:
    database, _ = _ingest(tmp_path, ["[12:00:01] [Server thread/INFO]: <A> tnt the base"])
    output = tmp_path / "review.jsonl"
    with MiningStore(database) as store:
        store.connection.execute("UPDATE messages SET partition_name='development'")
        row = list(store.iter_messages())[0]
        store.add_score(row["message_id"], "tfidf", "BLOCK", 0.91)
        store.add_score(row["message_id"], "bert", "ALLOW", 0.22)
        mine_candidates(store, "seed", ordinary_sample=0)
        _check(write_review_queue(store, output) == 1)
    payload = json.loads(output.read_text().splitlines()[0])
    _check("model_disagreement" in payload["buckets"])
    _check(len(payload["model_decisions"]) == 2)
    _check(all(value is None for value in payload["adjudication"].values()))


def test_json_discord_bot_messages_are_rejected() -> None:
    payload = json.dumps(
        {
            "author": {"username": "RelayBot", "bot": True},
            "content": "mirrored player chat",
            "channel": "general",
        }
    )
    _check(parse_line(payload) is None)


def test_busy_channel_sessions_have_a_maximum_span(tmp_path: Path) -> None:
    lines = [
        f"[12:{minute:02d}:00] [Server thread/INFO]: <P{minute}> message number {minute}"
        for minute in range(20)
    ]
    database, _ = _ingest(tmp_path, lines)
    with MiningStore(database) as store:
        session_ids = {str(row["session_id"]) for row in store.iter_messages()}
    _check(len(session_ids) >= 2)


def test_split_freezes_corpus_and_seed(tmp_path: Path) -> None:
    database, source = _ingest(
        tmp_path, ["[12:00:01] [Server thread/INFO]: <A> immutable corpus message"]
    )
    with MiningStore(database) as store:
        finalize_splits(store, "frozen-seed")
        try:
            finalize_splits(store, "different-seed")
        except ValueError as exc:
            _check("already frozen" in str(exc))
        else:
            raise AssertionError("expected split seed change rejection")
        try:
            ingest_paths(store, [source], progress_every=1000)
        except ValueError as exc:
            _check("corpus is frozen" in str(exc))
        else:
            raise AssertionError("expected post-split ingest rejection")


def test_score_load_rolls_back_on_protected_holdout(tmp_path: Path) -> None:
    database, _ = _ingest(
        tmp_path,
        [
            "[12:00:01] [Server thread/INFO]: <A> development message",
            "[12:03:01] [Server thread/INFO]: <B> holdout message",
        ],
    )
    scores = tmp_path / "mixed-scores.jsonl"
    with MiningStore(database) as store:
        rows = list(store.iter_messages())
        store.connection.execute(
            "UPDATE messages SET partition_name='development' WHERE message_id=?",
            (rows[0]["message_id"],),
        )
        store.connection.execute(
            "UPDATE messages SET partition_name='holdout' WHERE message_id=?",
            (rows[1]["message_id"],),
        )
        store.commit()
        _write(
            scores,
            [
                json.dumps(
                    {
                        "message_id": rows[0]["message_id"],
                        "model": "tfidf",
                        "action": "ALLOW",
                        "block_confidence": 0.1,
                    }
                ),
                json.dumps(
                    {
                        "message_id": rows[1]["message_id"],
                        "model": "tfidf",
                        "action": "ALLOW",
                        "block_confidence": 0.1,
                    }
                ),
            ],
        )
        try:
            load_scores(store, scores)
        except ValueError as exc:
            _check("protected holdout" in str(exc))
        else:
            raise AssertionError("expected protected holdout rejection")
        count = store.connection.execute("SELECT COUNT(*) FROM scores").fetchone()[0]
        _check(count == 0)


def _complete_review_record(message_id: str = "msg_abc") -> dict[str, object]:
    return {
        "message_id": message_id,
        "platform_hint": "minecraft",
        "channel_profile": "minecraft_public",
        "group_id": "group_0123456789abcdefabcd",
        "target_message_id": message_id,
        "messages": [
            {
                "message_id": message_id,
                "speaker": "user_0123456789ab",
                "offset_ms": 0,
                "text": "hi a@example.com",
            }
        ],
        "adjudication": {
            "policy_version": "v1",
            "domain": "safe",
            "difficulty": "hard",
            "label": "SAFE",
            "action": "ALLOW",
            "review_priority": "NONE",
            "strike": False,
            "containment": "NONE",
            "containment_duration_seconds": None,
            "support_flow": "NONE",
            "reason_codes": ["minecraft_gameplay_explicit"],
            "notes": "Human reviewed.",
        },
    }


def test_reviewed_export_accepts_nullable_duration_and_has_no_raw_pii(tmp_path: Path) -> None:
    reviews = tmp_path / "reviews.jsonl"
    output = tmp_path / "curated.jsonl"
    _write(reviews, [json.dumps(_complete_review_record())])
    _check(export_reviewed(reviews, output) == 1)
    exported = json.loads(output.read_text())
    _check(exported["containment_duration_seconds"] is None)
    _check("a@example.com" not in output.read_text())
    _check(exported["source"] == "production_reviewed_redacted")
    _check(exported["family_id"] == "real.0123456789abcdefabcd")


def test_reviewed_export_rolls_back_on_invalid_later_record(tmp_path: Path) -> None:
    reviews = tmp_path / "reviews.jsonl"
    output = tmp_path / "curated.jsonl"
    invalid = _complete_review_record("msg_def")
    adjudication = invalid["adjudication"]
    if not isinstance(adjudication, dict):
        raise AssertionError("expected adjudication object")
    adjudication["label"] = None
    _write(
        reviews,
        [json.dumps(_complete_review_record()), json.dumps(invalid)],
    )
    output.write_text("existing output\n", encoding="utf-8")
    try:
        export_reviewed(reviews, output)
    except ValueError as exc:
        _check("incomplete" in str(exc))
    else:
        raise AssertionError("expected invalid review rejection")
    _check(output.read_text(encoding="utf-8") == "existing output\n")


def test_review_queue_uses_split_component_as_group_id(tmp_path: Path) -> None:
    database, _ = _ingest(
        tmp_path,
        [
            "[12:00:01] [Server thread/INFO]: <A> build the TNT cannon",
            "[12:05:01] [Server thread/INFO]: <B> BUILD THE TNT CANNON!!!",
        ],
    )
    output = tmp_path / "review.jsonl"
    with MiningStore(database) as store:
        finalize_splits(store, "group-seed")
        rows = list(store.iter_messages())
        store.add_candidates(
            (str(row["message_id"]), "test_group", 1.0)
            for row in rows
        )
        _check(write_review_queue(store, output) == 2)
    payloads = [json.loads(line) for line in output.read_text().splitlines()]
    _check(payloads[0]["group_id"] == payloads[1]["group_id"])
    _check(payloads[0]["group_id"].startswith("group_"))
    _check(all("chronology_bucket" in item for item in payloads))
