"""Generic W25 multi-task encoder training and inference.

This module is experiment-only. It supports ModernBERT, DeBERTa-v3, and
CANINE-S through the same six-head contract.
"""

from __future__ import annotations

import copy
import random
from collections.abc import Iterator
from contextlib import nullcontext
from dataclasses import dataclass

import numpy as np  # pyright: ignore[reportMissingImports]
import torch  # pyright: ignore[reportMissingImports]
import torch.nn as nn  # pyright: ignore[reportMissingImports]
from torch.utils.data import DataLoader, Dataset, Sampler  # pyright: ignore[reportMissingImports]
from transformers import AutoModel, AutoTokenizer  # pyright: ignore[reportMissingImports]

from workers.w12.dataset import (
    ACTION_TO_ID,
    CONTAINMENT_TO_ID,
    LABEL_TO_ID,
    REVIEW_TO_ID,
    SUPPORT_TO_ID,
    ModerationExample,
)
from workers.w25.config import MODEL_SPECS
from workers.w25.contract import HEAD_NAMES, HEAD_VALUES, PredictionBundle
from workers.w25.data import serialize_variant

HEAD_SIZES = {name: len(values) for name, values in HEAD_VALUES.items()}


class ModerationDataset(Dataset):
    def __init__(
        self,
        examples: list[ModerationExample],
        tokenizer,
        max_length: int,
        serialization_variant: str,
    ) -> None:
        self.examples = examples
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.serialization_variant = serialization_variant
        self.encoded = [self._encode(example) for example in examples]

    def __len__(self) -> int:
        return len(self.examples)

    def _encode(self, example: ModerationExample):
        text = serialize_variant(example.serialized, self.serialization_variant)
        return self.tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            padding=False,
            return_tensors="pt",
        )

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        example = self.examples[index]
        encoded = self.encoded[index]
        row = {
            "input_ids": encoded["input_ids"].squeeze(0),
            "attention_mask": encoded["attention_mask"].squeeze(0),
        }
        row.update(_target_tensors(example))
        return row


class LengthBucketBatchSampler(Sampler[list[int]]):
    def __init__(
        self,
        dataset: ModerationDataset,
        batch_size: int,
        seed: int,
    ) -> None:
        self.lengths = [int(row["input_ids"].shape[-1]) for row in dataset.encoded]
        self.batch_size = batch_size
        self.seed = seed
        self.epoch = 0

    def __len__(self) -> int:
        return (len(self.lengths) + self.batch_size - 1) // self.batch_size

    def __iter__(self) -> Iterator[list[int]]:
        ordered = sorted(range(len(self.lengths)), key=self.lengths.__getitem__)
        batches = [
            ordered[start : start + self.batch_size]
            for start in range(0, len(ordered), self.batch_size)
        ]
        random.Random(self.seed + self.epoch).shuffle(batches)  # nosec B311
        self.epoch += 1
        yield from batches


class MultiTaskEncoder(nn.Module):
    def __init__(self, model_key: str) -> None:
        super().__init__()
        self.model_key = model_key
        spec = MODEL_SPECS[model_key]
        self.encoder = AutoModel.from_pretrained(
            spec.hf_id,
            revision=spec.revision,
            trust_remote_code=False,
        )
        hidden = int(self.encoder.config.hidden_size)
        self.dropout = nn.Dropout(0.1)
        self.heads = nn.ModuleDict(
            {name: nn.Linear(hidden, width) for name, width in HEAD_SIZES.items()}
        )

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
    ) -> tuple[dict[str, torch.Tensor], torch.Tensor]:
        output = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        pooled = self.dropout(output.last_hidden_state[:, 0])
        return {name: head(pooled) for name, head in self.heads.items()}, pooled


@dataclass(frozen=True)
class TrainingConfig:
    seed: int
    serialization_variant: str
    epochs: int = 5
    batch_size: int = 8
    learning_rate: float = 2e-5
    max_length: int | None = None


@dataclass(frozen=True)
class TrainResult:
    model: MultiTaskEncoder
    tokenizer: object
    best_dev_loss: float
    history: tuple[dict[str, float], ...]


def load_tokenizer(model_key: str):
    spec = MODEL_SPECS[model_key]
    return AutoTokenizer.from_pretrained(
        spec.hf_id,
        revision=spec.revision,
        trust_remote_code=False,
    )


def load_encoder_checkpoint(
    model_key: str,
    state_path,
) -> tuple[MultiTaskEncoder, object]:
    tokenizer = load_tokenizer(model_key)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = MultiTaskEncoder(model_key)
    state = torch.load(state_path, map_location="cpu", weights_only=True)
    model.load_state_dict(state)
    model.to(device)
    model.eval()
    return model, tokenizer


def train_encoder(
    model_key: str,
    train_examples: list[ModerationExample],
    dev_examples: list[ModerationExample],
    config: TrainingConfig,
) -> TrainResult:
    _set_seed(config.seed)
    spec = MODEL_SPECS[model_key]
    tokenizer = load_tokenizer(model_key)
    length = min(config.max_length or spec.max_length, spec.max_length)
    loaders = _build_loaders(
        train_examples,
        dev_examples,
        tokenizer,
        length,
        config.serialization_variant,
        config.batch_size,
        config.seed,
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = MultiTaskEncoder(model_key).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.learning_rate)
    return _fit(model, tokenizer, loaders, optimizer, device, config.epochs)


def _build_loaders(
    train_examples: list[ModerationExample],
    dev_examples: list[ModerationExample],
    tokenizer,
    max_length: int,
    variant: str,
    batch_size: int,
    seed: int,
) -> tuple[DataLoader, DataLoader]:
    train = ModerationDataset(train_examples, tokenizer, max_length, variant)
    dev = ModerationDataset(dev_examples, tokenizer, max_length, variant)

    def collate(rows):
        return _collate_batch(tokenizer, rows)

    return (
        DataLoader(
            train,
            batch_sampler=LengthBucketBatchSampler(train, batch_size, seed),
            collate_fn=collate,
            pin_memory=torch.cuda.is_available(),
        ),
        DataLoader(
            dev,
            batch_size=batch_size,
            collate_fn=collate,
            pin_memory=torch.cuda.is_available(),
        ),
    )


def _collate_batch(tokenizer, rows):
    inputs = [
        {"input_ids": row["input_ids"], "attention_mask": row["attention_mask"]}
        for row in rows
    ]
    batch = tokenizer.pad(inputs, padding=True, return_tensors="pt")
    for name in HEAD_NAMES:
        batch[name] = torch.stack([row[name] for row in rows])
    return batch


def _fit(
    model: MultiTaskEncoder,
    tokenizer,
    loaders: tuple[DataLoader, DataLoader],
    optimizer,
    device: torch.device,
    epochs: int,
) -> TrainResult:
    train_loader, dev_loader = loaders
    best_loss = float("inf")
    best_state = None
    history = []
    for epoch in range(epochs):
        train_loss = _train_epoch(model, train_loader, optimizer, device)
        dev_loss = _dev_loss(model, dev_loader, device)
        history.append({"epoch": float(epoch + 1), "train_loss": train_loss, "dev_loss": dev_loss})
        print(
            f"epoch {epoch + 1}/{epochs} train_loss={train_loss:.6f} dev_loss={dev_loss:.6f}",
            flush=True,
        )
        if dev_loss < best_loss:
            best_loss = dev_loss
            best_state = copy.deepcopy(model.state_dict())
    if best_state is None:
        raise RuntimeError("no neural checkpoint selected")
    model.load_state_dict(best_state)
    return TrainResult(model, tokenizer, best_loss, tuple(history))


def _train_epoch(model, loader, optimizer, device: torch.device) -> float:
    model.train()
    total = 0.0
    for batch in loader:
        optimizer.zero_grad(set_to_none=True)
        with _autocast(device, model):
            logits, _ = model(
                batch["input_ids"].to(device, non_blocking=True),
                batch["attention_mask"].to(device, non_blocking=True),
            )
            loss = _multihead_loss(logits, batch, device)
        if not torch.isfinite(loss):
            raise FloatingPointError(
                f"non-finite training loss for {model.model_key}"
            )
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        total += float(loss.detach().cpu())
    return total / max(len(loader), 1)


def _dev_loss(model, loader, device: torch.device) -> float:
    model.eval()
    total = 0.0
    with torch.no_grad():
        for batch in loader:
            with _autocast(device, model):
                logits, _ = model(
                    batch["input_ids"].to(device), batch["attention_mask"].to(device)
                )
                loss = _multihead_loss(logits, batch, device)
            if not torch.isfinite(loss):
                raise FloatingPointError(
                    f"non-finite development loss for {model.model_key}"
                )
            total += float(loss.detach().cpu())
    return total / max(len(loader), 1)


def _autocast(
    device: torch.device,
    model: MultiTaskEncoder | None = None,
):
    if (
        device.type != "cuda"
        or model is None
        or model.model_key.startswith("deberta-v3-")
    ):
        return nullcontext()
    return torch.autocast(device_type="cuda", dtype=torch.bfloat16)


def _multihead_loss(logits, batch, device: torch.device) -> torch.Tensor:
    criterion = nn.CrossEntropyLoss()
    losses = [criterion(logits[name], batch[name].to(device)) for name in HEAD_NAMES]
    return torch.stack(losses).sum()


def predict(
    model: MultiTaskEncoder,
    tokenizer,
    examples: list[ModerationExample],
    *,
    serialization_variant: str,
    max_length: int,
    batch_size: int = 8,
) -> tuple[PredictionBundle, dict[str, list[list[float]]], np.ndarray]:
    dataset = ModerationDataset(examples, tokenizer, max_length, serialization_variant)
    def collate(rows):
        return _collate_batch(tokenizer, rows)
    loader = DataLoader(dataset, batch_size=batch_size, collate_fn=collate)
    return _predict_loader(model, loader)


def _predict_loader(
    model: MultiTaskEncoder,
    loader: DataLoader,
) -> tuple[PredictionBundle, dict[str, list[list[float]]], np.ndarray]:
    device = next(model.parameters()).device
    raw = {name: [] for name in HEAD_NAMES}
    embeddings = []
    model.eval()
    with torch.no_grad():
        for batch in loader:
            with _autocast(device):
                logits, pooled = model(
                    batch["input_ids"].to(device), batch["attention_mask"].to(device)
                )
            embeddings.append(pooled.detach().cpu().numpy())
            for name in HEAD_NAMES:
                raw[name].extend(logits[name].detach().cpu().tolist())
    bundle = _bundle_from_logits(raw)
    matrix = np.concatenate(embeddings, axis=0) if embeddings else np.empty((0, 0))
    return bundle, raw, matrix


def _bundle_from_logits(raw: dict[str, list[list[float]]]) -> PredictionBundle:
    probabilities = {
        name: torch.softmax(torch.tensor(rows), dim=-1).tolist() for name, rows in raw.items()
    }
    predictions = {
        name: [max(range(len(row)), key=row.__getitem__) for row in rows]
        for name, rows in probabilities.items()
    }
    uncertainty = [1.0 - max(row) for row in probabilities["action"]]
    bundle = PredictionBundle(predictions, probabilities, uncertainty)
    bundle.validate()
    return bundle


def _target_tensors(example: ModerationExample) -> dict[str, torch.Tensor]:
    ids = {
        "label": LABEL_TO_ID[example.label],
        "action": ACTION_TO_ID[example.action],
        "review_priority": REVIEW_TO_ID[example.review_priority],
        "strike": 1 if example.strike else 0,
        "containment": CONTAINMENT_TO_ID[example.containment],
        "support_flow": SUPPORT_TO_ID[example.support_flow],
    }
    return {name: torch.tensor(value, dtype=torch.long) for name, value in ids.items()}


def _set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
