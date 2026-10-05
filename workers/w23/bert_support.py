"""BERT Mini prediction and train-only OOF generation for W23."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from sklearn.model_selection import StratifiedKFold
from torch.utils.data import DataLoader

from workers.w12.dataset import LABEL_TO_ID, ModerationExample, load_partition
from workers.w12.train_encoder import (
    CANDIDATES,
    HEADS,
    ModerationDataset,
    MultiTaskBert,
    load_candidate_tokenizer,
)
from workers.w23.config import (
    BERT_BATCH_SIZE,
    BERT_LR,
    BERT_OOF_EPOCHS,
    OOF_FOLDS,
    SEED,
)
from workers.w23.modeling import PredictionBundle

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts" / "oof"


def bert_fold_indices(examples: list[ModerationExample]) -> list[tuple[np.ndarray, np.ndarray]]:
    labels = [LABEL_TO_ID[item.label] for item in examples]
    splitter = StratifiedKFold(n_splits=OOF_FOLDS, shuffle=True, random_state=SEED)
    indices = np.arange(len(examples))
    return list(splitter.split(indices, labels))


def _new_bert_model() -> tuple[MultiTaskBert, object]:
    cfg = CANDIDATES["bert-mini"]
    local_dir = cfg["local_dir"]
    usable_local = local_dir if (local_dir / "config.json").exists() else None
    tokenizer = load_candidate_tokenizer("bert-mini")
    model = MultiTaskBert(cfg["hf_id"], usable_local, cfg["revision"])
    return model, tokenizer


def _make_loader(
    examples: list[ModerationExample],
    tokenizer: object,
    *,
    batch_size: int,
    shuffle: bool,
) -> DataLoader:
    dataset = ModerationDataset(examples, tokenizer, 128)
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle)


def _train_fixed_epochs(
    model: MultiTaskBert,
    loader: DataLoader,
    *,
    epochs: int,
    lr: float,
) -> None:
    model.train()
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr)
    criterion = torch.nn.CrossEntropyLoss()
    for _ in range(epochs):
        for batch in loader:
            optimizer.zero_grad()
            logits = model(batch["input_ids"], batch["attention_mask"])
            losses = [criterion(logits[name], batch[name]) for name in HEADS]
            torch.stack(losses).sum().backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()


def _predict_probabilities(
    model: MultiTaskBert,
    loader: DataLoader,
) -> dict[str, np.ndarray]:
    model.eval()
    rows: dict[str, list[np.ndarray]] = {name: [] for name in HEADS}
    with torch.no_grad():
        for batch in loader:
            logits = model(batch["input_ids"], batch["attention_mask"])
            for name in HEADS:
                rows[name].append(torch.softmax(logits[name], dim=-1).cpu().numpy())
    return {name: np.concatenate(parts, axis=0) for name, parts in rows.items()}


def predict_bert_checkpoint(
    examples: list[ModerationExample],
    checkpoint_path: Path,
    *,
    batch_size: int = 32,
) -> PredictionBundle:
    model, tokenizer = _new_bert_model()
    state = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    model.load_state_dict(state)
    probabilities = _predict_probabilities(
        model,
        _make_loader(examples, tokenizer, batch_size=batch_size, shuffle=False),
    )
    predictions = {
        name: matrix.argmax(axis=1).astype(int).tolist() for name, matrix in probabilities.items()
    }
    return PredictionBundle(predictions=predictions, probabilities=probabilities)


def train_bert_oof_fold(
    fold: int,
    *,
    epochs: int = BERT_OOF_EPOCHS,
    batch_size: int = BERT_BATCH_SIZE,
    lr: float = BERT_LR,
) -> Path:
    train = load_partition("train")
    folds = bert_fold_indices(train)
    if fold < 0 or fold >= len(folds):
        raise ValueError(f"fold must be between 0 and {len(folds) - 1}")
    fit_indices, hold_indices = folds[fold]
    torch.manual_seed(SEED + fold)
    model, tokenizer = _new_bert_model()
    fit = [train[int(index)] for index in fit_indices]
    hold = [train[int(index)] for index in hold_indices]
    _train_fixed_epochs(
        model,
        _make_loader(fit, tokenizer, batch_size=batch_size, shuffle=True),
        epochs=epochs,
        lr=lr,
    )
    probabilities = _predict_probabilities(
        model,
        _make_loader(hold, tokenizer, batch_size=batch_size * 2, shuffle=False),
    )
    return _write_fold_artifact(fold, fit_indices, hold_indices, probabilities, epochs)


def _write_fold_artifact(
    fold: int,
    fit_indices: np.ndarray,
    hold_indices: np.ndarray,
    probabilities: dict[str, np.ndarray],
    epochs: int,
) -> Path:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    path = ARTIFACT_DIR / f"bert-mini-oof-fold-{fold}.json"
    payload = {
        "fold": fold,
        "folds": OOF_FOLDS,
        "seed": SEED + fold,
        "epochs": epochs,
        "selection_partition": "W11 train only; fixed epochs; no W11 validation",
        "fit_count": len(fit_indices),
        "hold_indices": hold_indices.astype(int).tolist(),
        "probabilities": {name: matrix.tolist() for name, matrix in probabilities.items()},
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def load_bert_oof(directory: Path, train_count: int) -> PredictionBundle:
    probabilities = {
        name: np.zeros((train_count, class_count), dtype=np.float64)
        for name, class_count in HEADS.items()
    }
    seen = np.zeros(train_count, dtype=np.int8)
    for path in sorted(directory.glob("bert-mini-oof-fold-*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        indices = np.asarray(payload["hold_indices"], dtype=int)
        seen[indices] += 1
        for name in HEADS:
            matrix = np.asarray(payload["probabilities"][name], dtype=np.float64)
            probabilities[name][indices] = matrix
    if not np.all(seen == 1):
        missing = np.flatnonzero(seen != 1).tolist()[:20]
        raise RuntimeError(f"BERT OOF coverage is incomplete or duplicated: {missing}")
    predictions = {
        name: matrix.argmax(axis=1).astype(int).tolist() for name, matrix in probabilities.items()
    }
    return PredictionBundle(predictions=predictions, probabilities=probabilities)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, required=True)
    args = parser.parse_args()
    path = train_bert_oof_fold(args.fold)
    print(path, flush=True)


if __name__ == "__main__":
    main()
