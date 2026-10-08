# W22 real-chat hard-negative mining

W22 is a local-only, privacy-conscious pipeline for turning large Minecraft/Paper and optional Discord relay exports into **human review candidates**. Model predictions are evidence for prioritization only; they are never treated as labels.

## Privacy boundary

Raw logs, the SQLite work database, identity maps, score files, review queues, and unreviewed exports stay local. Never commit them. The ingest path pseudonymizes player identities and channel names before persistence, redacts email/phone/IP/token-like values, and excludes Discord staff/ticket channels by default. An optional local identity map may map Minecraft and Discord names to one local identity so mirrored relay copies deduplicate; that map is never written to the database.

The repository should contain only the tooling, documentation, tests, and synthetic fixture logs. A production-derived record may enter `data/curated/` only after explicit human Policy-v1 adjudication and the `export-reviewed` redaction/schema gate.

## Supported inputs

The parser accepts common Paper/Minecraft chat lines such as:

```text
[12:00:01] [Server thread/INFO]: <Steve> hello
[12:00:01 INFO]: <Steve> hello
```

It also accepts Discord relay text lines and JSONL exports with sender/author, content/message/text, optional channel, and optional timestamp fields. The finalized Enthusia scanner JSONL is supported directly via its `player`, `message`, `source_platform`, `channel`, `recipient`, and separate `date` + `time` fields. JSON records whose author metadata explicitly marks the sender as a bot are ignored so relay bots are not treated as players. Lines that do not match a chat record are ignored, which excludes startup/plugin/system noise.

For the finalized scanner export, Minecraft private-message context is keyed to the pseudonymized participant pair so unrelated DMs are never mixed. Minecraft staff chat is excluded. The export does not currently carry an authoritative guild identifier or originating Discord relay channel, so guild and `discord_relay` context is conservatively sender-scoped rather than inventing cross-player context.

## Workflow

Use a private work directory outside the repository, for example `/srv/private/moderation-mining/`.

```bash
python -m tools.chat_mining ingest \
  --db /srv/private/moderation-mining/w22.sqlite \
  --identity-map /srv/private/moderation-mining/identities.json \
  /exports/latest.log /exports/discord.jsonl

python -m tools.chat_mining split \
  --db /srv/private/moderation-mining/w22.sqlite \
  --seed enthusia-real-v1 \
  --manifest /srv/private/moderation-mining/split-manifest.json
```

**Freeze the split before loading model scores.** The split uses disk-backed union/find to keep adjacent conversation sessions and repeated surface-variant families in one connected group. Activity sessions close after a two-minute idle gap and are capped at 15 minutes so a continuously busy public channel cannot collapse into one giant split component. The deterministic 80/10/10 partitions are `development`, `validation`, and protected `holdout`. The manifest records the seed, algorithm version, partition counts, and SHA-256 of assignments. Once a split is created, its seed/algorithm and corpus are immutable in that work database; ingesting more messages or changing the split requires a fresh database. Holdout score ingestion is rejected.

External model predictions use JSONL:

```json
{"message_id":"msg_...","model":"baseline-tfidf","action":"BLOCK","block_confidence":0.93}
```

Load predictions and mine only the development partition:

```bash
python -m tools.chat_mining load-scores \
  --db /srv/private/moderation-mining/w22.sqlite \
  /srv/private/moderation-mining/model-scores.jsonl

python -m tools.chat_mining mine \
  --db /srv/private/moderation-mining/w22.sqlite \
  --seed ordinary-sample-v1 \
  --ordinary-sample 500 \
  --slang-file /srv/private/moderation-mining/enthusia-slang.txt
```

Candidate buckets include named TF-IDF/BERT disagreements when model names identify them, generic model disagreements, both-block cases, suspicious BLOCK predictions, near-threshold predictions, ALLOW-vs-lexical-rule disagreements, repeated reformulations, Minecraft gameplay violence/TNT hard negatives, optional owner-supplied server slang terms, and a deterministic bounded random sample of otherwise ordinary chat.

After a first human review pass, a completed review/adjudication JSONL can be supplied to `mine --adjudications ...`; ALLOW adjudications with a model BLOCK confidence of at least 0.90 are added as `reviewed_high_confidence_false_positive` candidates. Human review remains the source of truth.

Create the review queue:

```bash
python -m tools.chat_mining review-queue \
  --db /srv/private/moderation-mining/w22.sqlite \
  --output /srv/private/moderation-mining/review.jsonl
```

Each record contains only redacted/pseudonymous context, the target message, candidate buckets, current model decisions/confidences, and explicit blank Policy-v1 adjudication fields. It also records the frozen partition, a privacy-safe `group_id` for the actual session/family split component, target-relative time, and a coarse relative-day chronology bucket. These fields support private leakage audits and later context-suite construction without exposing account identity or raw channel names. Fill the adjudication fields manually. The review queue is private and must not be committed.

Export only completed reviews:

```bash
python -m tools.chat_mining export-reviewed \
  --reviews /srv/private/moderation-mining/review-complete.jsonl \
  --output /srv/private/moderation-mining/curated-candidates.jsonl
```

The export command uses an explicit output allowlist, re-redacts message text, requires pseudonymous speakers, validates Policy-v1 enum/reason-code values against `tools/dataset_qa/config.json`, and permits `containment_duration_seconds: null` where the dataset schema permits it. The curated `family_id` is derived from the frozen split component rather than the individual target message, so adjacent conversation and repeated surface families remain grouped after export. Reviews created before this group metadata existed must be regenerated from the frozen private database before export. The command does not copy model scores, source paths/lines, raw channel names, chronology metadata, or original identities into the curated record.

## Streaming and resume behavior

Input files are read one line at a time. The work database is SQLite/WAL, and ingest commits a checkpoint every `--progress-every` lines (default 50,000) while printing progress counters to stderr. Candidate random sampling is bounded by `--ordinary-sample`; review output streams records. Split grouping uses SQLite-backed union/find rather than loading the corpus into memory.

Checkpoints are keyed to the local source path hash. W22 is intended for stable exports; replacing/truncating a source file at the same path after partial ingestion should use a fresh work database. Plain UTF-8/text logs and JSONL are supported in this revision; compressed `.gz` archives should be expanded locally before ingestion.

## Redaction rules and limitations

The redactor covers IPv4, validated compressed/full IPv6 candidates, obvious email addresses, North-American-style phone numbers, bearer values, Discord-token-like strings, and common `api_key`/`token`/`password`/`secret` assignments. It is deliberately conservative and cannot guarantee removal of every possible piece of free-form personal information. Human reviewers must still remove any residual identifying/private content before export.

Near-spam deduplication is sender-local and time-bounded. Cross-platform mirror deduplication is reliable only when the optional identity map links the two account names. The finalized scanner export lacks authoritative originating Discord channel metadata, so W22 cannot safely reconstruct a canonical-vs-mirror flag for every historical relay record; those cases must remain a documented runtime/integration limitation rather than invented metadata. Surface-family grouping catches case/punctuation/spacing/repeated-character variants; it is not a semantic paraphrase detector. Model files are not bundled or invoked by W22: score JSONL is the integration boundary so current or future TF-IDF/BERT candidates can be run independently. Score loading is transactional: if a batch contains a protected-holdout record or another invalid row, no earlier rows from that batch are retained.
