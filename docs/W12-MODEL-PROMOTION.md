# W12 model artifact promotion and rollback

Status: **prepared only — no production model is accepted or deployed yet.**

This runbook defines how an accepted W12 model moves from reproducible CI evidence
into persistent runtime storage without retraining, silently changing files, or
coupling the model to the virtual environment.

Final promotion is blocked on the fresh W20 acceptance gate.

## Immutable identity

A promoted model release is identified by all of:

- model version;
- W12 model/evidence source SHA;
- W20 acceptance-set version and SHA-256;
- W20 acceptance report SHA-256;
- selected metadata SHA-256;
- vectorizer SHA-256;
- every ONNX-head SHA-256;
- outer bundle/archive SHA-256.

A model with any different value is a different release even if the filename is
the same.

## Persistent layout

Use a versioned immutable directory under the existing persistent runtime area:

```text
runtime-data/
└── models/
    ├── releases/
    │   └── w12-baseline-tfidf-v2-<metadata-sha-prefix>/
    │       ├── baseline-tfidf-metadata.json
    │       ├── baseline-tfidf-vectorizer.json
    │       └── baseline-tfidf-*.onnx
    └── acceptance/
        └── <release-id>/
            ├── acceptance-manifest.json
            ├── acceptance-report.json
            └── RELEASE.json
```

Do not put the accepted model only inside `.venv`, a temporary Actions
artifact directory, or another release-cleanup path.

## Promotion prerequisites

All are required:

1. W12 candidate/preprocessing/threshold contract is frozen.
2. W20 was built independently and reviewed/frozen before W12 saw its results.
3. W20 passes every pre-registered gate in
   `docs/W12-V2-ACCEPTANCE-GATES.md`.
4. The exact selected ONNX bundle used for W20 is the bundle being promoted.
5. Final service CI is green.
6. No unresolved valid static-analysis/review blocker remains.
7. Promotion is explicitly authorized; this document alone is not authorization.

## Installation procedure

Do not retrain during installation.

1. Obtain the exact accepted bundle recorded by the W20 acceptance report.
2. Verify the outer archive SHA-256 before extracting.
3. Extract into a **new** versioned release directory.
4. Verify the metadata file SHA-256.
5. Verify the vectorizer and every ONNX head against hashes inside metadata.
6. Verify metadata requires:
   - `schema_version=2`;
   - `candidate=baseline-tfidf`;
   - `serialization_version=w12-v2`;
   - the accepted model version.
7. Make the release directory read-only to ordinary runtime maintenance where
   operationally practical.
8. Set runtime environment:
   - `AI_MOD_ONNX_METADATA_PATH=<absolute accepted metadata path>`
   - `AI_MOD_ONNX_METADATA_SHA256=<accepted metadata sha256>`
9. Restart **only** the optional AI moderation process through the approved
   supervisor/container procedure.
10. Require `/health/ready` to report:
    - HTTP 200;
    - `ready=true`;
    - `classifier_ready=true`;
    - `classifier_mode=onnx-baseline-tfidf`;
    - the expected local model version.
11. Exercise a bounded synthetic smoke set. Do not use exempt/private staff or
    ticket content as smoke input.
12. Verify Ticket Bot and Minecraft chat remain healthy throughout.

## No mutable "latest" artifact

Do not configure production against a CI URL, an expiring artifact ID, or a
directory whose contents are overwritten in place.

A future model is installed into a new release directory with a new manifest
hash. Promotion changes the configured metadata path/checksum; it does not
replace bytes underneath the active release.

## Rollback

Keep the prior accepted model release intact.

Rollback consists of:

1. stop/restart only the optional moderation process as required;
2. restore the prior `AI_MOD_ONNX_METADATA_PATH` and metadata SHA;
3. start the prior release;
4. verify `/health/ready`;
5. leave `moderation.sqlite3` untouched;
6. preserve the failed/new release directory and evidence for diagnosis.

If no accepted model can load, remove/unset the model configuration so the
service returns to explicit not-ready/fail-open behavior. Never substitute an
unreviewed artifact simply to make readiness green.

## Release record

For every accepted model create a `RELEASE.json` containing at least:

- release ID;
- model version;
- source commit;
- W12 evidence workflow/run;
- selected candidate;
- metadata SHA-256;
- bundle SHA-256;
- W20 acceptance-set version/SHA;
- W20 report SHA;
- acceptance gate result;
- approver/time;
- previous release ID;
- rollback reason if later retired.

The record is provenance, not a place for secrets or raw production messages.
