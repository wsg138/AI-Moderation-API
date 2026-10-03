"""W12 encoder fine-tuning: multi-task BERT classifier.

Architecture: shared pretrained encoder + one linear head per policy dimension.
Trains ONLY on W11 train IDs. Validation is used for early stopping and
model selection only.

Candidates:
  - bert-tiny : prajjwal1/bert-tiny (MIT), 2 layers / 128 hidden
  - bert-mini : google/bert_uncased_L-4_H-256_A-4 (Apache-2.0), 4 layers / 256 hidden
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModel, BertTokenizer

from .dataset import (
    ACTION_TO_ID,
    ACTIONS,
    CONTAINMENT_TO_ID,
    CONTAINMENTS,
    LABEL_TO_ID,
    LABELS,
    REVIEW_PRIORITIES,
    REVIEW_TO_ID,
    SUPPORT_FLOWS,
    SUPPORT_TO_ID,
    ModerationExample,
    load_partition,
)

MODELS_DIR = Path(__file__).resolve().parent / "models"
ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"

CANDIDATES = {
    "bert-tiny": {
        "local_dir": MODELS_DIR / "bert-tiny",
        "hf_id": "prajjwal1/bert-tiny",
        "revision": "6f75de8b60a9f8a2fdf7b69cbd86d9e64bcb3837",
        "license": "MIT",
    },
    "bert-mini": {
        "local_dir": MODELS_DIR / "bert-mini",
        "hf_id": "google/bert_uncased_L-4_H-256_A-4",
        "revision": "387825ce42dbb39b87911cdf8e383ee3b25184f8",
        "license": "Apache-2.0",
    },
}

HEADS = {
    "label": len(LABELS),
    "action": len(ACTIONS),
    "review_priority": len(REVIEW_PRIORITIES),
    "strike": 2,
    "containment": len(CONTAINMENTS),
    "support_flow": len(SUPPORT_FLOWS),
}


class ModerationDataset(Dataset):
    def __init__(self, examples: list[ModerationExample], tokenizer, max_len: int):
        self.examples = examples
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, idx: int) -> dict:
        ex = self.examples[idx]
        enc = self.tokenizer(
            ex.serialized,
            max_length=self.max_len,
            truncation=True,
            padding="max_length",
            return_tensors="pt",
        )
        return {
            "input_ids": enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "label": torch.tensor(LABEL_TO_ID[ex.label], dtype=torch.long),
            "action": torch.tensor(ACTION_TO_ID[ex.action], dtype=torch.long),
            "review_priority": torch.tensor(REVIEW_TO_ID[ex.review_priority], dtype=torch.long),
            "strike": torch.tensor(1 if ex.strike else 0, dtype=torch.long),
            "containment": torch.tensor(CONTAINMENT_TO_ID[ex.containment], dtype=torch.long),
            "support_flow": torch.tensor(SUPPORT_TO_ID[ex.support_flow], dtype=torch.long),
        }


class MultiTaskBert(nn.Module):
    def __init__(
        self,
        encoder_name: str,
        local_dir: Path | None = None,
        revision: str | None = None,
    ):
        super().__init__()
        if local_dir and (local_dir / "config.json").exists():
            self.encoder = AutoModel.from_pretrained(str(local_dir), local_files_only=True)
        else:
            self.encoder = AutoModel.from_pretrained(encoder_name, revision=revision)
        hidden = self.encoder.config.hidden_size
        self.dropout = nn.Dropout(0.1)
        self.heads = nn.ModuleDict({name: nn.Linear(hidden, n) for name, n in HEADS.items()})

    def forward(self, input_ids, attention_mask):
        out = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        pooled = self.dropout(out.last_hidden_state[:, 0])
        return {name: head(pooled) for name, head in self.heads.items()}


def evaluate(model: nn.Module, loader: DataLoader, device: torch.device) -> dict:
    model.eval()
    correct: dict[str, int] = {name: 0 for name in HEADS}
    total = 0
    total_loss = 0.0
    criterion = nn.CrossEntropyLoss()
    with torch.no_grad():
        for batch in loader:
            input_ids = batch["input_ids"].to(device)
            mask = batch["attention_mask"].to(device)
            logits = model(input_ids, mask)
            loss = sum(criterion(logits[name], batch[name].to(device)) for name in HEADS)
            total_loss += loss.item()
            total += input_ids.size(0)
            for name in HEADS:
                pred = logits[name].argmax(dim=-1).cpu()
                correct[name] += (pred == batch[name]).sum().item()
    return {
        "loss": total_loss / max(total, 1),
        **{f"{name}_acc": correct[name] / max(total, 1) for name in HEADS},
    }


def load_candidate_tokenizer(candidate: str) -> BertTokenizer:
    cfg = CANDIDATES[candidate]
    local_dir = cfg["local_dir"]
    if (local_dir / "vocab.txt").exists():
        return BertTokenizer(str(local_dir / "vocab.txt"), do_lower_case=True)
    return BertTokenizer.from_pretrained(
        cfg["hf_id"],
        revision=cfg["revision"],
        do_lower_case=True,
    )


def train_candidate(
    candidate: str,
    seed: int = 42,
    epochs: int = 5,
    batch_size: int = 16,
    lr: float = 3e-5,
    max_len: int = 128,
) -> dict:
    torch.manual_seed(seed)
    device = torch.device("cpu")
    cfg = CANDIDATES[candidate]
    local_dir: Path | None = (
        cfg["local_dir"] if (cfg["local_dir"] / "config.json").exists() else None
    )

    tokenizer = load_candidate_tokenizer(candidate)
    train_ex = load_partition("train")
    val_ex = load_partition("validation")
    print(f"[{candidate}] train={len(train_ex)} val={len(val_ex)}", flush=True)

    train_loader = DataLoader(
        ModerationDataset(train_ex, tokenizer, max_len),
        batch_size=batch_size,
        shuffle=True,
    )
    val_loader = DataLoader(
        ModerationDataset(val_ex, tokenizer, max_len),
        batch_size=batch_size,
    )

    model = MultiTaskBert(cfg["hf_id"], local_dir, cfg["revision"]).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss()

    best_val = -1.0
    best_state = None
    history = []
    for epoch in range(epochs):
        model.train()
        epoch_loss = 0.0
        for batch in train_loader:
            optimizer.zero_grad()
            logits = model(batch["input_ids"].to(device), batch["attention_mask"].to(device))
            loss = sum(criterion(logits[name], batch[name].to(device)) for name in HEADS)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            epoch_loss += loss.item()
        metrics = evaluate(model, val_loader, device)
        metrics["epoch"] = epoch + 1
        metrics["train_loss"] = epoch_loss / len(train_loader)
        history.append(metrics)
        print(
            f"[{candidate}] epoch {epoch + 1}/{epochs} "
            + " ".join(f"{k}={v:.3f}" for k, v in metrics.items() if k not in ("epoch",)),
            flush=True,
        )
        # Select on label accuracy (primary) — final selection uses full slices
        if metrics["label_acc"] > best_val:
            best_val = metrics["label_acc"]
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

    assert best_state is not None
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    ckpt_path = ARTIFACT_DIR / f"{candidate}-seed{seed}.pt"
    torch.save(best_state, ckpt_path)
    with open(ARTIFACT_DIR / f"{candidate}-seed{seed}-history.json", "w") as f:
        json.dump(history, f, indent=2)
    return {
        "candidate": candidate,
        "seed": seed,
        "best_val_label_acc": best_val,
        "hf_id": cfg["hf_id"],
        "revision": cfg["revision"],
        "license": cfg["license"],
        "checkpoint": str(ckpt_path),
        "history": history,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", choices=list(CANDIDATES), required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=3e-5)
    args = parser.parse_args()
    t0 = time.time()
    result = train_candidate(
        args.candidate, seed=args.seed, epochs=args.epochs, batch_size=args.batch_size, lr=args.lr
    )
    print(f"done in {time.time() - t0:.1f}s: {json.dumps(result, indent=2)[:500]}")


if __name__ == "__main__":
    main()
