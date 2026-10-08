"""W12 prediction wrappers: uniform interface for baseline and encoder models."""

from __future__ import annotations

from pathlib import Path

import torch
from torch.utils.data import DataLoader

from workers.w12.baseline import train_baseline
from workers.w12.dataset import ModerationExample, load_partition
from workers.w12.train_encoder import CANDIDATES, ModerationDataset, MultiTaskBert, load_candidate_tokenizer

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
HEAD_NAMES = ("label", "action", "review_priority", "strike", "containment", "support_flow")


def predict_baseline(
    examples: list[ModerationExample],
) -> tuple[dict[str, list[int]], list[float]]:
    """Retrain the deterministic baseline from W11 train, then predict."""
    model = train_baseline(load_partition("train"), seed=42)
    texts = [example.serialized for example in examples]
    predictions = model.predict_all(texts)
    probabilities = model.predict_proba_all(texts)
    block_probabilities = [row[1] for row in probabilities["action"]]
    return predictions, block_probabilities


def predict_encoder(
    candidate: str,
    seed: int,
    examples: list[ModerationExample],
    batch_size: int = 32,
) -> tuple[dict[str, list[int]], list[float]]:
    cfg = CANDIDATES[candidate]
    local_dir = cfg["local_dir"]
    tokenizer = load_candidate_tokenizer(candidate)
    device = torch.device("cpu")
    model = MultiTaskBert(cfg["hf_id"], local_dir, cfg["revision"]).to(device)
    checkpoint = torch.load(
        ARTIFACT_DIR / f"{candidate}-seed{seed}.pt",
        map_location=device,
        weights_only=True,
    )
    model.load_state_dict(checkpoint)
    model.eval()

    loader = DataLoader(
        ModerationDataset(examples, tokenizer, 128),
        batch_size=batch_size,
    )
    predictions: dict[str, list[int]] = {name: [] for name in HEAD_NAMES}
    block_probabilities: list[float] = []
    with torch.no_grad():
        for batch in loader:
            logits = model(
                batch["input_ids"].to(device),
                batch["attention_mask"].to(device),
            )
            for name in predictions:
                predictions[name].extend(logits[name].argmax(dim=-1).cpu().tolist())
            probabilities = torch.softmax(logits["action"], dim=-1)[:, 1]
            block_probabilities.extend(probabilities.cpu().tolist())
    return predictions, block_probabilities
