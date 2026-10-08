# G10 second-pass source assessment — 21 strong-cue + 35 mixed-risk cases

**State: coordinator preliminary interpretation; NOT an independent human adjudication or accepted training truth.** The owner explicitly allows blackmail involving only Minecraft gameplay and prohibits coercion involving real-world stakes (2026-10-08). The 500-record G10 source is frozen at Git blob `3604b8e139892595fd280764869dc3ca1786044d`.

## 21 strong-gameplay-cue cases not included in the first 86 proposals

I examined the messages available through the target, rather than post-target messages, source notes or assumed user history. This yielded **14 additional provisional game-only proposals** and **7 still uncertain**.

| Preliminary disposition | Source IDs | Why |
|---|---|---|
| 9 game-cheating/moderation-report leverage proposals | G10-0043, G10-0049, G10-0050, G10-0053, G10-0056, G10-0061, G10-0068, G10-0083, G10-0104 | Requests for Minecraft items in exchange for suppressing alleged Minecraft cheat evidence or server reports |
| 3 in-game account-rule exposure proposals | G10-0079, G10-0138, G10-0281 | In-game items demanded to avoid exposing possible Minecraft account-sharing / alternate-account rule violations |
| 2 base/grief leverage proposals | G10-0163, G10-0381 | Threat to reveal previous in-game spawn griefing or current Minecraft coordinates in exchange for items |
| 7 still unclear, no proposed replacement label | G10-0047, G10-0144, G10-0161, G10-0279, G10-0311, G10-0324, G10-0380 | Unspecified clips, secrets, reputational impact or other candidate; the visible threat is not securely limited to Minecraft gameplay |

Even the proposed 14 are **provisional**. Some Minecraft cheating reports can be genuine moderation matters; allowing in-game blackmail does not excuse a separately prohibited false report, staff abuse, threats of real-world harm, or other violation. The source contexts are synthetic and not evidence of actual cheating or wrongdoing.

## 35 cases marked as possible real-world or mixed stakes

These cases were inspected for preliminary risk *type*. **None are automatically reclassified SAFE; none are claimed as confirmed real-world crimes or harms.**

| Risk requiring independent interpretation | Source IDs | Cases |
|---|---|---:|
| Personal voice-chat embarrassment/exposure | G10-0136, G10-0137, G10-0141, G10-0149, G10-0165 | 5 |
| Disclosure that someone bought a game account | G10-0148, G10-0157, G10-0166 | 3 |
| VIP/MVP/Enthusiast/Devotee server rank or store purchase, potentially involving real money | G10-0195, G10-0197, G10-0198, G10-0199, G10-0200, G10-0201, G10-0204, G10-0206, G10-0207, G10-0208, G10-0210, G10-0211, G10-0212, G10-0213, G10-0215, G10-0216 | 16 |
| Screenshots, campaign messages or other disclosures whose scope is not established | G10-0319, G10-0321, G10-0322, G10-0323, G10-0325, G10-0326, G10-0331, G10-0333, G10-0334, G10-0346, G10-0355 | 11 |
| **Total** | | **35** |

**Interpretation:** A game platform/channel alone does not turn coerced real-money transactions or exposure of a real person's sensitive information into harmless gameplay. At the same time, phrases such as "screenshots" and "bought your account" do not, on their own, establish a real-world privacy violation. These remain pending factual and policy review.

## Source-linked reproducibility

The code records every one of these **56** source IDs once with the original file SHA-256, source line, hash of target-time-available messages, preliminary disposition, and pending human adjudication state:

```bash
python -m tools.dataset_qa.gameplay_blackmail_second_pass

# Optional source manifest OUTSIDE Git checkout, coordinator-only:
python -m tools.dataset_qa.gameplay_blackmail_second_pass \
  --coordinator-second-pass-out /tmp/g10-second-pass-private.jsonl
```

The records carry `review_origin=coordinator_preliminary_screen_only`, `independent_review=not_received`, `adjudicated=false`, and `training_eligible=false`. The source file is not rewritten, and source drift fails closed.

## Revised total queue

| Status | Cases | Gate |
|---|---:|---|
| First-pass game-only preliminary proposals | 86 | Independent review / owner adjudication pending |
| Second-pass game-only preliminary proposals | 14 | Independent review / owner adjudication pending |
| Second-pass stronger-cue uncertainties | 7 | More semantic context/review required |
| Possible mixed or real-world risk | 35 | Independent scope review required |
| Previously insufficiently scoped | 199 | Context review required |
| **Total G10 previously flagged BLOCK records** | **341** | **0 corrections accepted or training-admitted** |

The next semantic-review priority is verifying the **100 provisional proposals** against Policy v1 and reviewing the remaining **241** unresolved records. These buckets are priority queues and do not measure model accuracy.

Do **not** merge PR #58, admit training data, alter G10 or private player data, run GPU training, or deploy/punish players as a consequence of this coordinator screening.
