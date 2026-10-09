"""Deterministic invented private-banter contrast candidates, NEVER training gold.

Developer-authored situations contrast reciprocal joking, clear boundaries,
the first ignored boundary, repeated harassment, and respectful compliance.
Explicit slurs are placeholders pending authorized realistic data review.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from tools.dataset_qa.asof_input import serialize_as_of_target

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "data" / "development" / "private_banter_candidate_v1.jsonl"
PHASES = ("mutual_joking", "boundary_request", "ignored_boundary",
          "repeated_after_boundary", "respectful_compliance")
SLUR_TOKEN = "[EXPLICIT_SLUR_PLACEHOLDER]"
# Entirely fictional variations; zero actual player data or external models.
TOPICS = (
    ("aim", "your aim is absolute garbage lmao", "lol says the guy who misses carts",
     "bro you shoot like a potato", "Seriously, stop roasting my aim, it's upsetting me.",
     "Dude I really mean it, stop targeting me over aim.",
     "nah you're still trash at aiming"),
    ("parkour", "holy shit you can't jump two blocks", "lmao and you fell first",
     "you're the parkour clown of this server", "Quit making fun of my jumps now please.",
     "I already asked, stop joking about how I jump.",
     "nope you're still an awful parkour player"),
    ("redstone", "that redstone machine is dumb as hell", "bro your TNT machine exploded",
     "your circuits run on clown energy", "Stop calling my builds stupid; it's annoying.",
     "I'm serious, please don't make fun of my redstone anymore.",
     "too bad, your contraptions are still idiotic"),
    ("inventory", "you loot like a total idiot", "lmao you died carrying a wooden hoe",
     "can't trust you with one diamond", "Please stop insulting my inventory choices.",
     "Seriously, it's not funny anymore. Stop.",
     "I don't care, you still pick items like a moron"),
    ("mining", "you mine like a confused sheep", "lol you lost the diamonds again",
     "the cave is smarter than you", "I don't like the mining jokes now. Stop.",
     "Come on, I said stop bringing it up.",
     "you're still a trash miner deal with it"),
    ("bow", "that bow shot was fucking pathetic", "haha your arrow hit a cow",
     "the skeletons out-aim you every time", "Stop mocking my bow shots now.",
     "Please stop, this is getting genuinely annoying.",
     "nope your bow skills are pure garbage"),
    ("building", "your house looks like shit bro", "lol and yours is a dirt cube",
     "this house needs to be condemned", "Seriously stop roasting my house.",
     "I'm asking again, please don't mock my build.",
     "it still looks ugly as hell don't care"),
    ("farming", "your farm is the dumbest thing I've seen", "lmao says the carrot thief",
     "even the villagers think it's crap", "Stop teasing me about the farm now.",
     "Can you please actually stop insulting my farm?",
     "nah your farm still sucks"),
    ("duels", "you are genuinely dogshit at duels lol", "haha you lost to a chicken",
     "best teammate, worst swordsman", "Stop calling me bad at duels, seriously.",
     "I asked you to stop; I'm not laughing.",
     "don't care you're still dogshit"),
    ("speedrun", "your speedrun time is a fucking joke", "bro you spawned in lava",
     "the clock is your worst enemy", "Please stop mocking my speedruns.",
     "It isn't funny now, can you stop?",
     "no chance, your runs still suck ass"),
    ("potions", "you're a potion-making disaster", "lmao remember when you poisoned yourself",
     "you're basically a walking poison cloud", "Stop making those potion jokes now.",
     "I really don't want to hear that joke again.",
     "too bad you're still a damn potion clown"),
    ("elytra", "you fly like an absolute dumbass", "lol you hit that mountain too",
     "you're a professional wall magnet", "Please stop calling my flying stupid.",
     "I actually want you to stop the flying insults.",
     "nope your flying is still dogshit"),
    ("boat", "that boat driving is straight garbage", "haha you ran into shore again",
     "my grandpa steers better than you", "Enough boat jokes. I'm serious, stop.",
     "Please, I said the boat jokes aren't funny.",
     "still a terrible boat driver lmao"),
    ("gear", "your armor choices are criminally stupid", "lol you wore gold boots into lava",
     "best dressed fool on the SMP", "Stop making fun of my gear right now.",
     "Seriously, I don't want gear jokes anymore.",
     "no your gear is still complete trash"),
    ("arena", "you play arena like a clueless bot", "lmao you forgot the capture point",
     "even the scoreboard is laughing at you", "Please stop making me the arena joke.",
     "I asked already. Stop, it's upsetting.",
     "nah you're still useless in arena"),
    ("crafting", "you are so bad at crafting it's painful", "haha you crafted eight sticks again",
     "the crafting table wants a refund", "Please stop joking about my crafting now.",
     "Quit it, I'm being serious about stopping.",
     "you're still an absolute crafting clown"),
)

def _row(family: int, phase: str, texts: list[tuple[str, str]],
         candidate_action: str, flags: list[str]) -> dict[str, Any]:
    messages = [
        {"speaker": speaker, "offset_ms": number * 5000, "text": line}
        for number, (speaker, line) in enumerate(texts)
    ]
    record = {
        "example_id": f"PMB-{family:02d}-{phase}",
        "source": "synthetic_developer_authored",
        "family_id": f"PMB-F{family:02d}",
        "platform_hint": "minecraft",
        "channel_profile": "minecraft_private",
        "messages": messages,
        "target_index": len(messages) - 1,
        "contrast_phase": phase,
        "candidate_action": candidate_action,
        "candidate_reason_flags": flags,
        "annotation_status": "unverified_policy_candidate",
        "training_eligible": False,
        "owner_reviewed": False,
        "semantic_label_verified": False,
    }
    serialize_as_of_target(record)
    return record


def _family(family: int, topic: tuple[str, ...]) -> list[dict[str, Any]]:
    _, joke, reaction, tease, request, repeat_stop, after = topic
    banter = [("Friend_A", joke), ("Friend_B", reaction),
              ("Friend_A", tease)]
    stop = banter + [("Friend_B", request)]
    return [
        _row(family, "mutual_joking", banter, "ALLOW",
             ["reciprocal_willing_banter", "private_context"]),
        _row(family, "boundary_request", stop, "ALLOW",
             ["recipient_requests_stop", "request_itself_allowed"]),
        _row(family, "ignored_boundary", stop + [("Friend_A", tease)],
             "REVIEW", ["ignored_clear_stop", "human_review_without_auto_sanction"]),
        _row(family, "repeated_after_boundary",
             stop + [("Friend_A", tease), ("Friend_B", repeat_stop),
                     ("Friend_A", after)], "BLOCK",
             ["repeated_unwanted_targeting", "clear_recipient_boundary"]),
        _row(family, "respectful_compliance",
             stop + [("Friend_A", "Sorry, I didn't realize it hurt. I'll stop.")],
             "ALLOW", ["honored_boundary", "no_continued_harassment"]),
    ]


def _slur_family(family: int, intro: str) -> list[dict[str, Any]]:
    prior = [("Friend_A", intro), ("Friend_B", "lol we're friends, I get your jokes")]
    return [
        _row(family, "direct_placeholder",
             prior + [("Friend_A", "you're " + SLUR_TOKEN)],
             "BLOCK", ["explicit_slur_placeholder", "friendship_no_exemption"]),
        _row(family, "reported_placeholder",
             prior + [("Friend_B", "Reporting what someone typed: " + SLUR_TOKEN)],
             "BLOCK", ["explicit_slur_placeholder", "quoted_message_only",
                       "reporter_not_culpable"]),
        _row(family, "after_stop_placeholder",
             prior + [("Friend_B", "Stop saying mean stuff to me, please"),
                      ("Friend_A", "fine " + SLUR_TOKEN)],
             "BLOCK", ["explicit_slur_placeholder", "recipient_boundary"]),
        _row(family, "reference_without_slur",
             prior + [("Friend_B", "Don't use an actual slur; that isn't funny")],
             "ALLOW", ["slur_discussion_without_actual_slur"]),
    ]


def build_candidates() -> list[dict[str, Any]]:
    """Invented contrasts, no source-corpus records or human gold imported."""
    records = [
        row for index, topic in enumerate(TOPICS, 1)
        for row in _family(index, topic)
    ]
    records.extend(
        row for number, intro in enumerate(
            ("you're terrible at duels lol", "that build is shit haha",
             "lol your aim is weak", "you play like a potato"), 17,
        ) for row in _slur_family(number, intro)
    )
    return records


def summarize(records: list[dict[str, Any]]) -> dict[str, object]:
    """Aggregate-only developmental inventory; never infer accuracy."""
    count = Counter(str(row["candidate_action"]) for row in records)
    return {
        "records": len(records),
        "families": len({row["family_id"] for row in records}),
        "candidate_actions": dict(sorted(count.items())),
        "training_eligible": False,
        "independently_adjudicated": False,
        "actual_slurs_included": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    records = build_candidates()
    content = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in records
    )
    if args.write:
        DATASET.parent.mkdir(parents=True, exist_ok=True)
        with DATASET.open("x", encoding="utf-8", newline="\n") as file:
            file.write(content)
    print(json.dumps(summarize(records), sort_keys=True))


if __name__ == "__main__":
    main()
