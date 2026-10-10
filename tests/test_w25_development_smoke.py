"""Only synthetic/temporary artifacts; no private chat or holdout access."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from workers.w25 import development_smoke as smoke
from workers.w25.open_baselines import training_recipe_digest


def test_private_key_is_stable_and_never_recreated(tmp_path: Path) -> None:
    folder, secret_path = smoke._private_paths(tmp_path)
    assert folder.is_dir()
    first = smoke._key(secret_path)
    second = smoke._key(secret_path)
    assert first == second
    assert len(first) == 64
    assert secret_path.read_text(encoding="ascii") == first
    with pytest.raises(ValueError, match="Invalid existing"):
        secret_path.write_text("bad-key", encoding="ascii")
        smoke._key(secret_path)


def test_private_root_guards_repo_and_relative_paths(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Existing absolute"):
        smoke._private_paths(Path("relative"))
    with pytest.raises(ValueError, match="not live in Git"):
        smoke._private_paths(smoke.REPO)
    root, secret = smoke._private_paths(tmp_path)
    assert root.parent == tmp_path.resolve()
    assert not secret.exists()


def test_admitted_development_selects_only_w26_development(monkeypatch) -> None:
    seen: list[str] = []
    synthetic = [SimpleNamespace(example_id=f"fake-{n}") for n in range(3)]
    monkeypatch.setattr(smoke, "verify_all_admissions", lambda: seen.append("verify"))
    monkeypatch.setattr(
        smoke, "load_development_data",
        lambda **kwargs: (synthetic, [SimpleNamespace(example_id="w11")]),
    )

    def fake_partition(name: str, partition: str):
        seen.append(name + ":" + partition)
        return synthetic

    monkeypatch.setattr(smoke, "load_source_partition", fake_partition)
    train, dev = smoke._development_examples(True, 2)
    assert train is synthetic
    assert len(dev) == 2
    assert seen == [
        "verify",
        "W26_real_chat_curated_training_PRIVATE_v2.jsonl:development",
    ]


def test_recipe_digest_is_stable_and_depends_on_model_and_seed() -> None:
    first = training_recipe_digest("word", 42)
    assert len(first) == 64
    assert first == training_recipe_digest("word", 42)
    assert first != training_recipe_digest("character", 42)
    assert first != training_recipe_digest("word", 138)
