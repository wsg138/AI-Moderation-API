# Optional owner-only solo pilot (16 public synthetic cases)

The owner may independently screen the 16-case **public-synthetic** pilot without recruiting additional reviewers. This is useful for documenting **owner Policy-v1 intent** and identifying label-correction proposals, but **a single-owner screen is not double-blind certification, training approval, or production-punishment authorization**.

A single self-contained `Enthusia-Easy-Review-16.html` file with all 16 **blinded** packets was delivered directly to the owner in ChatGPT (as a downloadable local file, **not** committed to this source branch or served publicly). It does not include gold labels, original `Gxx` example IDs, the private coordinator crosswalk, or post-target messages.

## Owner procedure

1. Download and open the HTML file locally in Chrome or Edge on Windows. The examples are already inside it; no JSONL import or sign-in.
2. For each highlighted target message, choose one of `ALLOW`, `BLOCK` or `REVIEW`. Optional fields: why, whether a strike is recommended, staff alert priority, and free-text notes. These fields are deliberately optional for low-friction policy screening.
3. Click `Save & Next` across the 16 cases. The local browser tries to preserve progress, but the export is the authoritative owner feedback snapshot.
4. Click `Export my answers`; the local file is `Enthusia-my-16-reviews.json`. Return it privately in ChatGPT to the coordinator. Do not publish labels or proprietary coordinator source mappings.
5. Only after the owner feedback is recorded should the coordinator compare against the private crosswalk/source labels and draft proposed corrections, emphasizing policy disagreements and uncertain cases.

## Distinguish pilot feedback from certified decisions

The exported JSON has `format: enthusia_owner_solo_pilot_v1`, `review_mode: owner_feedback_not_independent_validation`, `training_eligible: false`, opaque `packet_id`, and selected action with optional reasons/strike/staff notes. It is **not** the strict `review_decisions.py` decision schema and **must not** be silently passed to `review_intake.py` or counted as an independently verified second review.

The existing independent-review and policy adjudication gates remain in force for severe/safety labels and any examples treated as authoritative training truth, unless the owner explicitly changes that release policy with a documented scope and risk acceptance. Dataset source lineage, leakage-safe family splitting, independent prospective evaluation and any Codacy security blockers are separate gates.

There is no automatic upload or network request from the owner feedback page, and it does not update the repository or production moderation decisions. Actual browser verification is a separate usability check; the HTML's JavaScript syntax and embedded packet schema were checked when the artifact was generated.
