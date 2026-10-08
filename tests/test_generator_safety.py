"""Generator source must not use nonportable machine-specific destinations."""
from __future__ import annotations

import ast
from pathlib import Path

GENERATOR = Path("tools/gen_g15.py")


def test_g15_output_is_repo_relative() -> None:
    source = GENERATOR.read_text(encoding="utf-8")
    assert "OUT = 'data/synthetic/G15-evasion-advanced.jsonl'" in source
    assert "/home/hatch/" not in source


def test_g15_main_is_only_called_under_module_guard() -> None:
    tree = ast.parse(GENERATOR.read_text(encoding="utf-8"))
    direct_calls = [
        node for node in tree.body
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name) and node.value.func.id == "main"
    ]
    assert not direct_calls
    assert isinstance(tree.body[-1], ast.If)
