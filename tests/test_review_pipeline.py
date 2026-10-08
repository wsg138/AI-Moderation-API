"""Whole public synthetic review path stays blind and non-admitting."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.dataset_qa.freshness import ROOT, batch_files
from tools.dataset_qa.review_assignments import assign_reviewers
from tools.dataset_qa.review_intake import intake
from tools.dataset_qa.review_sampling import build_sample

KEY = b"complete-path-test-secret-only"


def test_candidate_cohort_to_two_reviewer_pending_queue() -> None:
    if not batch_files(ROOT):
        pytest.skip("candidate-only test does not run on main")
    packets, crosswalk = build_sample(ROOT, KEY)
    assigned, manifest = assign_reviewers(packets, ["reviewerA", "reviewerB"], KEY)
    statuses = intake(packets, manifest, [])
    assert len(packets) == len(manifest) == len(statuses)
    assert len(assigned["reviewerA"]) == len(assigned["reviewerB"]) == len(packets)
    assert all(row["status"] == "awaiting_first_review" for row in statuses)
    assert all(row["training_eligible"] is False for row in statuses)
    assert all("selection_reasons" not in json.dumps(packet) for packet in packets)
    assert all("source_sha256" in record for record in crosswalk)


def test_no_real_data_directory_is_needed() -> None:
    assert Path("data/synthetic") == ROOT
