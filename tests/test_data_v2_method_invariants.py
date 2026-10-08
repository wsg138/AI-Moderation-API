"""Collect the synthetic-only Data/Model v2 method invariants in project CI.

The authoritative fixture definitions remain in tools/data_v2. They do not
scan private chat or authorize any training/deployment actions.
"""

from __future__ import annotations

import unittest

import pytest

from tools.data_v2.test_method_invariants import DataV2FixtureTests


@pytest.mark.parametrize(
    "case_name",
    unittest.defaultTestLoader.getTestCaseNames(DataV2FixtureTests),
)
def test_data_v2_method_fixture(case_name: str) -> None:
    DataV2FixtureTests(case_name).debug()
