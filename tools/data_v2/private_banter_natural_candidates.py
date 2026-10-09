"""Natural short-form Minecraft private-banter DEV examples, not training gold."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from tools.dataset_qa.asof_input import serialize_as_of_target

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/development/private_banter_natural_candidate_v2.jsonl"

# Actual casual phrasing, contrasting sincere and joking 'stop', not just
# polite elaborate moderation-policy cue sentences.
TOPICS: tuple[tuple[str, ...], ...] = (
    (
        "ur dog at carts lmao",
        "bro u died first 💀",
        "still a bot tho",
        "stop",
        "nah ur aim is ass",
        "bro fr stop",
        "still dogwater",
    ),
    (
        "shit base lmfao",
        "says the dirt hut owner",
        "it's a toilet house",
        "stop clowning my base",
        "looks like a toilet lol",
        "im serious stop",
        "looks awful anyway",
    ),
    (
        "u suck at pvp",
        "u literally got rolled by a cow",
        "nah you're worse",
        "stop",
        "lmao nah ur washed",
        "leave it now",
        "u still suck",
    ),
    (
        "you drive boats like a blind chicken",
        "LMAO I saw u crash too",
        "learn to steer",
        "stop insulting me",
        "skill issue",
        "stop messaging me about it",
        "nah ur still terrible",
    ),
    (
        "bot behavior",
        "lol says my carried teammate",
        "carried u for hours",
        "can u stop",
        "nah still carried",
        "stop seriously",
        "u're useless",
    ),
    (
        "your armor looks goofy as hell",
        "haha so does yours",
        "clown armor",
        "stop",
        "still looks dumb",
        "bro i'm not joking stop",
        "ur armor is shit",
    ),
    (
        "0 braincells crafting that",
        "lol u made 12 sticks",
        "actual clown",
        "stop being a dick",
        "u are a clown tho",
        "stop fr",
        "nah loser",
    ),
    (
        "ur parkour is trash",
        "lmao you fell on the first jump",
        "get good",
        "stop",
        "ur still so bad",
        "dude stop i'm getting annoyed",
        "still trash",
    ),
)

# Other patterns matter: playful 'stop', hard no-contact, someone complying,
# incidental profanity, a clear 'don't talk to me' boundary with later pestering.
ADDITIONAL: tuple[tuple[str, list[tuple[str, str]], str, str], ...] = (
    (
        "playful_stop_1",
        [("A", "ur so shit at skywars 😂"), ("B", "STOPP 💀💀"), ("A", "lmaooo")],
        "ALLOW",
        "playful_stop",
    ),
    (
        "playful_stop_2",
        [("A", "bro missed again"), ("B", "stop 😂"), ("A", "haha no way")],
        "ALLOW",
        "playful_stop",
    ),
    (
        "playful_stop_3",
        [("A", "you owe me 50 diamonds noob"), ("B", "stop lol"), ("A", "fine 49")],
        "ALLOW",
        "mutual_gameplay_banter",
    ),
    (
        "one_word_stop",
        [("A", "u can't aim"), ("B", "stop"), ("A", "lol u can't though")],
        "ALLOW",
        "first_continuation_after_stop_not_automatic_flag",
    ),
    (
        "short_stop_respected",
        [("A", "ur so bad"), ("B", "stop"), ("A", "ok my bad")],
        "ALLOW",
        "honored_boundary",
    ),
    (
        "no_contact_respected",
        [("A", "ur an idiot"), ("B", "stop messaging me"), ("A", "ok sorry")],
        "ALLOW",
        "honored_no_contact_request",
    ),
    (
        "no_contact_ignored",
        [
            ("A", "you're a loser"),
            ("B", "stop messaging me"),
            ("A", "nah answer me"),
            ("B", "seriously leave me alone"),
            ("A", "reply already idiot"),
        ],
        "BLOCK",
        "repeated_unwanted_contact",
    ),
    (
        "single_no_contact_reply",
        [("A", "u suck"), ("B", "stop messaging me"), ("A", "why lol")],
        "REVIEW",
        "explicit_no_contact_boundary_uncertain_escalation",
    ),
    (
        "one_sided_unsolicited",
        [
            ("A", "ur trash"),
            ("A", "u hear me"),
            ("A", "hello loser"),
            ("B", "stop messaging me"),
            ("A", "shut up reply"),
        ],
        "BLOCK",
        "targeted_unwanted_contact",
    ),
    (
        "consent_restore",
        [
            ("A", "you suck"),
            ("B", "stop"),
            ("A", "ok"),
            ("B", "nah i'm joking roast me again"),
            ("A", "lol u still suck"),
        ],
        "ALLOW",
        "explicit_mutual_banter_resumed",
    ),
    (
        "threat_not_just_a_joke",
        [("A", "haha get wrecked"), ("B", "lol"), ("A", "i'll find your irl address")],
        "BLOCK",
        "real_world_threat_override",
    ),
    (
        "disagreement_isnt_harassment",
        [("A", "I hate that rule"), ("B", "same"), ("A", "it's a shit update")],
        "ALLOW",
        "criticism_not_targeted_harassment",
    ),
)


def record(
    family: str, phase: str, exchange: list[tuple[str, str]], action: str, flag: str
) -> dict[str, Any]:
    messages = [
        {"speaker": speaker, "offset_ms": i * 1200, "text": message}
        for i, (speaker, message) in enumerate(exchange)
    ]
    row = {
        "example_id": f"PMN-{family}-{phase}",
        "family_id": f"PMN-{family}",
        "source": "fictional_developer_authored_natural_chat",
        "platform_hint": "minecraft",
        "channel_profile": "minecraft_private",
        "messages": messages,
        "target_index": len(messages) - 1,
        "contrast_phase": phase,
        "candidate_action": action,
        "candidate_reason_flags": [flag],
        "annotation_status": "unverified_policy_candidate",
        "owner_reviewed": False,
        "semantic_label_verified": False,
        "training_eligible": False,
    }
    serialize_as_of_target(row)
    return row


def family_set(n: int, v: tuple[str, ...]) -> list[dict[str, Any]]:
    tease, response, again, stop, first, second, unwanted = v
    banter = [("A", tease), ("B", response), ("A", again)]
    boundary = banter + [("B", stop)]
    return [
        record(str(n), "reciprocal", banter, "ALLOW", "reciprocal_joking"),
        record(str(n), "short_stop", boundary, "ALLOW", "stop_request_itself"),
        record(
            str(n),
            "first_continuation",
            boundary + [("A", first)],
            "ALLOW",
            "owner_prefers_monitor_not_immediate_flag",
        ),
        record(
            str(n),
            "repeated_unwanted",
            boundary + [("A", first), ("B", second), ("A", unwanted)],
            "BLOCK",
            "persistent_after_multiple_stop_requests",
        ),
        record(str(n), "apology", boundary + [("A", "ok sorry")], "ALLOW", "stops_after_boundary"),
    ]


def build_candidates() -> list[dict[str, Any]]:
    records = [r for n, topic in enumerate(TOPICS, 1) for r in family_set(n, topic)]
    records.extend(
        record(fid, "context_target", msgs, action, flag) for fid, msgs, action, flag in ADDITIONAL
    )
    return records


def inventory(rows: list[dict[str, Any]]) -> dict[str, object]:
    return {
        "total": len(rows),
        "families": len({r["family_id"] for r in rows}),
        "candidate_actions": dict(sorted(Counter(r["candidate_action"] for r in rows).items())),
        "training_eligible": False,
        "owner_reviewed": False,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    rows = build_candidates()
    if args.write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with OUT.open("x", encoding="utf-8", newline="\n") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps(inventory(rows), sort_keys=True))


if __name__ == "__main__":
    main()
