# DATA-V2-05 — Offline owner quick-review page generator (draft)

**Scope:** create an easy-to-use, self-contained action-only HTML page **only**
from the blinded, already selected synthetic packets prepared in DATA-V2-04.
No model training, no source editing, no private-player data and no reviewer
answers added to the repository.

## Coordinator workflow

1. Use the fixed source bytes and owner Round 3 private action-only ledger in a
   trusted private environment. Generate the next blinded priority-based packet
   file and the **separate private** coordinator crosswalk with
   `tools/data_v2/targeted_blind_review.py`. Only the packet file goes into
   this generator; the coordinator crosswalk must stay secret.
2. Render a new offline HTML page at a new path **outside the Git checkout**:

```sh
python -m tools.data_v2.owner_quick_review_html \
  --packet-input /private/reviewer/new-priority-packets.jsonl \
  --html-out /private/reviewer/Enthusia-Targeted-Review-4.html \
  --round-label "Targeted Round 4"
```

3. Privately provide that HTML page to the owner. They type their reviewer
   alias, evaluate one target-time conversation at a time, choose
   ALLOW/REVIEW/BLOCK, optionally add a short explanation, and click
   **Copy answers** after answering every case. They paste results in the
   coordinator chat, just like Round 3. Keyboard 1/2/3 selects action; arrow
   keys move. There is no internet submission, remote JavaScript, external
   library, web tracking, automatic punishment or training-label output.
4. Validate copied responses against the same **private** packet ID
   crosswalk and frozen source metadata, preserving the action-only decision
   separately. Never fill in semantic labels, containment, mutes or strikes
   from this one-page review. Candidate actions stay unadmitted.

## Security design

The page generator only accepts exact validated packet fields (opaque packet
ID, platform, channel, messages available at target time, target_index).
`review_assignments._check_packet` rejects post-target content, unexpected
metadata, malformed timestamp types and nonchronological context. The builder
rejects duplicate packet IDs and more than 120 cases per HTML page. Each
synthetic speaker/message is **HTML escaped**; reviewer packets never contain
the original synthetic case ID, candidate answer, source category, family
reason or selection tier. Coordinator-only crosswalk remains a different file
from the HTML.

The output uses exclusive creation with mode 0600. It contains inline CSS/JS
for navigation and assembling a copyable text response. Answer state is kept
only in the page's in-memory form until copied. Refreshing the page loses
unsaved answers. Users should paste into the coordinator chat after
completion. Any local browser's clipboard permissions may require manually
copying from the read-only output box.

This is **not** a browser-reviewed production system or a security isolation
boundary against a compromised client. Do not open untrusted externally edited
packet files or put the generated HTML/crosswalk on public GitHub. A blind
page helps independent owner judgment, but cannot cryptographically prove
identity or training-label truth.

## What remains

The reviewed cohort is biased toward selected candidate risks. This cannot
be used to claim unbiased model action accuracy or a verified 9k training set.
Unresolved owner-policy questions, source rights/privacy, family-aware
train/dev/test splits, individual severe-safety adjudication, independent
review of complete semantic/punishment fields, upstream Codacy findings,
sealed holdouts and explicit training approval remain separate blockers.

This PR adds only the **generator and tests**. Generating and distributing
the actual owner-facing HTML requires a private coordinator execution with
the pinned source files and private ledger/crosswalk, not GitHub Actions.
