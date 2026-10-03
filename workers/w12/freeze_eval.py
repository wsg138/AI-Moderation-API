"""W12 freeze and held-out evaluation.

RUN ONCE. This script:
1. Records the immutable freeze record (candidate, config, thresholds).
2. Runs the frozen W11 test partition.
3. Runs the frozen adversarial partition.
4. Runs the owner golden acceptance set.

Do NOT run this, observe the results, then modify the model and run again
while claiming unbiased acceptance. If you change anything after seeing
these results, record the contamination explicitly.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from .dataset import (
    _record_to_example,
    is_fully_labeled,
    load_adversarial_manifest,
    load_owner_golden,
    load_partition,
    load_records_by_id,
)
from .evaluate import evaluate_heldout
from .predict import predict_baseline, predict_encoder

REPORTS_DIR = Path(__file__).resolve().parent / "reports"


def run_heldout_evaluation(candidate: str, seed: int, freeze_record: dict) -> dict:
    """Run all frozen held-out partitions exactly once."""
    print(f"FREEZE RECORD: {json.dumps(freeze_record, indent=2)}", flush=True)
    with open(REPORTS_DIR / "freeze-record.json", "w") as f:
        json.dump(freeze_record, f, indent=2)

    results: dict = {"freeze_record": freeze_record, "partitions": {}}

    # 1. Frozen W11 test
    print("Evaluating frozen test...", flush=True)
    test_ex = load_partition("test")
    if candidate == "baseline":
        preds, proba = predict_baseline(test_ex)
    else:
        preds, proba = predict_encoder(candidate, seed, test_ex)
    results["partitions"]["test"] = evaluate_heldout("test", test_ex, preds, proba)

    # 2. Frozen adversarial
    print("Evaluating frozen adversarial...", flush=True)
    adv_manifest = load_adversarial_manifest()
    adv_ids = adv_manifest.get("example_ids", adv_manifest.get("frozen_adversarial", []))
    records_by_id = load_records_by_id()
    adv_ex = [_record_to_example(records_by_id[i]) for i in adv_ids]
    if candidate == "baseline":
        preds, proba = predict_baseline(adv_ex)
    else:
        preds, proba = predict_encoder(candidate, seed, adv_ex)
    results["partitions"]["frozen_adversarial"] = evaluate_heldout(
        "frozen_adversarial", adv_ex, preds, proba
    )

    # 3. Owner golden (acceptance only)
    # Golden fixtures have partial labels (null = owner did not specify that
    # dimension). For classifier metrics, use only fully-labeled fixtures.
    print("Evaluating owner golden...", flush=True)
    golden_records = load_owner_golden()
    complete = [r for r in golden_records if is_fully_labeled(r)]
    partial = [r for r in golden_records if not is_fully_labeled(r)]
    print(
        f"  ({len(complete)} fully-labeled classifier fixtures, "
        f"{len(partial)} partial/policy fixtures excluded from classifier metrics)",
        flush=True,
    )
    golden_ex = [_record_to_example(r) for r in complete]
    if candidate == "baseline":
        preds, proba = predict_baseline(golden_ex)
    else:
        preds, proba = predict_encoder(candidate, seed, golden_ex)
    results["partitions"]["owner_golden"] = evaluate_heldout(
        "owner_golden", golden_ex, preds, proba
    )

    # Summary
    summary = {
        "candidate": candidate,
        "seed": seed,
        "evaluated_at": time.time(),
        "test_label_macro_f1": results["partitions"]["test"]["semantic_label"]["macro_f1"],
        "test_block_recall": results["partitions"]["test"]["runtime_visibility_binary"][
            "block_recall"
        ],
        "adversarial_label_macro_f1": results["partitions"]["frozen_adversarial"]["semantic_label"][
            "macro_f1"
        ],
        "golden_n": results["partitions"]["owner_golden"]["n"],
        "golden_label_accuracy": results["partitions"]["owner_golden"]["semantic_label"][
            "accuracy"
        ],
    }
    results["summary"] = summary
    with open(REPORTS_DIR / "heldout-summary.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"HELD-OUT SUMMARY: {json.dumps(summary, indent=2)}", flush=True)
    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True, help="baseline, bert-tiny, or bert-mini")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--freeze-record", required=True, help="path to freeze record JSON")
    args = parser.parse_args()

    with open(args.freeze_record) as f:
        freeze_record = json.load(f)
    run_heldout_evaluation(args.candidate, args.seed, freeze_record)
