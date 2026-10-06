"""Adapters that expose W12 baselines through the W25 common contract."""

from __future__ import annotations

from pathlib import Path

from workers.w12.baseline import train_baseline
from workers.w12.dataset import ModerationExample, load_partition
from workers.w25.contract import HEAD_NAMES, PredictionBundle


def predict_w12_word_baseline(
    examples: list[ModerationExample],
    *,
    seed: int = 42,
) -> PredictionBundle:
    """Recreate the current W12 word-only baseline from W11 train."""
    model = train_baseline(load_partition("train"), seed=seed)
    texts = [item.serialized for item in examples]
    predictions = model.predict_all(texts)
    probabilities = model.predict_proba_all(texts)
    bundle = PredictionBundle(
        predictions=predictions,
        probabilities=probabilities,
        uncertainty=[1.0 - max(row) for row in probabilities["action"]],
    )
    bundle.validate()
    return bundle


def predict_w12_bert_mini(
    examples: list[ModerationExample],
    checkpoint: Path,
    *,
    batch_size: int = 32,
) -> PredictionBundle:
    """Evaluate an explicitly pinned W12 BERT Mini checkpoint."""
    import torch  # pyright: ignore[reportMissingImports]
    from torch.utils.data import DataLoader  # pyright: ignore[reportMissingImports]

    from workers.w12.train_encoder import (
        CANDIDATES,
        ModerationDataset,
        MultiTaskBert,
        load_candidate_tokenizer,
    )

    config = CANDIDATES["bert-mini"]
    local_dir = config["local_dir"]
    usable_local = local_dir if (local_dir / "config.json").exists() else None
    tokenizer = load_candidate_tokenizer("bert-mini")
    model = MultiTaskBert(config["hf_id"], usable_local, config["revision"])
    state = torch.load(checkpoint, map_location="cpu", weights_only=True)
    model.load_state_dict(state)
    model.eval()
    loader = DataLoader(
        ModerationDataset(examples, tokenizer, 128),
        batch_size=batch_size,
    )
    return _predict_bert_batches(model, loader)


def _predict_bert_batches(model, loader) -> PredictionBundle:
    import torch  # pyright: ignore[reportMissingImports]

    probabilities: dict[str, list[list[float]]] = {name: [] for name in HEAD_NAMES}
    with torch.no_grad():
        for batch in loader:
            logits = model(batch["input_ids"], batch["attention_mask"])
            for name in HEAD_NAMES:
                probabilities[name].extend(torch.softmax(logits[name], dim=-1).tolist())
    predictions = {
        name: [max(range(len(row)), key=row.__getitem__) for row in rows]
        for name, rows in probabilities.items()
    }
    bundle = PredictionBundle(
        predictions=predictions,
        probabilities=probabilities,
        uncertainty=[1.0 - max(row) for row in probabilities["action"]],
    )
    bundle.validate()
    return bundle
