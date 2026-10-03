"""W12 prediction wrappers: uniform interface for baseline and encoder models."""

from __future__ import annotations

from pathlib import Path

import torch
from torch.utils.data import DataLoader

from .baseline import load_baseline
from .dataset import ModerationExample
from .train_encoder import CANDIDATES, ModerationDataset, MultiTaskBert, load_candidate_tokenizer

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"


def predict_baseline(examples: list[ModerationExample]) -> tuple[dict[str, list[int]], list[float]]:
    model = load_baseline(ARTIFACT_DIR / "baseline-tfidf.pkl")
    texts = [e.serialized for e in examples]
    preds = model.predict_all(texts)
    probas = model.predict_proba_all(texts)
    # proba of BLOCK for the 3-way action head (index 1 = BLOCK)
    proba_block = [row[1] for row in probas["action"]]
    return preds, proba_block


def predict_encoder(
    candidate: str, seed: int, examples: list[ModerationExample], batch_size: int = 32
) -> tuple[dict[str, list[int]], list[float]]:
    cfg = CANDIDATES[candidate]
    local_dir = cfg["local_dir"]
    tokenizer = load_candidate_tokenizer(candidate)
    device = torch.device("cpu")
    model = MultiTaskBert(cfg["hf_id"], local_dir, cfg["revision"]).to(device)
    ckpt = torch.load(ARTIFACT_DIR / f"{candidate}-seed{seed}.pt", map_location=device)
    model.load_state_dict(ckpt)
    model.eval()
    loader = DataLoader(ModerationDataset(examples, tokenizer, 128), batch_size=batch_size)
    all_preds: dict[str, list[int]] = {name: [] for name in
                                       ["label", "action", "review_priority", "strike",
                                        "containment", "support_flow"]}
    all_proba_block: list[float] = []
    with torch.no_grad():
        for batch in loader:
            logits = model(batch["input_ids"].to(device), batch["attention_mask"].to(device))
            for name in all_preds:
                all_preds[name].extend(logits[name].argmax(dim=-1).cpu().tolist())
            # softmax proba of BLOCK (action index 1)
            probs = torch.softmax(logits["action"], dim=-1)[:, 1]
            all_proba_block.extend(probs.cpu().tolist())
    return all_preds, all_proba_block
