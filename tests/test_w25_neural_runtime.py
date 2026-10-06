from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")

from workers.w12.dataset import ModerationExample  # noqa: E402 - skip torch first
from workers.w25.contract import HEAD_NAMES  # noqa: E402 - skip torch before neural import
from workers.w25.neural import (  # noqa: E402 - optional evidence dependency
    LengthBucketBatchSampler,
    ModerationDataset,
    _collate_batch,
)


class _Tokenizer:
    pad_token_id = 0

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, _text, *, truncation, max_length, padding, return_tensors):
        self.calls += 1
        assert truncation is True
        assert max_length > 0
        assert padding is False
        assert return_tensors == "pt"
        return {
            "input_ids": torch.tensor([[1, 2]], dtype=torch.long),
            "attention_mask": torch.ones((1, 2), dtype=torch.long),
        }

    def pad(self, inputs, *, padding, return_tensors):
        assert padding is True
        assert return_tensors == "pt"
        width = max(len(row["input_ids"]) for row in inputs)
        input_ids = []
        attention_mask = []
        for row in inputs:
            missing = width - len(row["input_ids"])
            input_ids.append(torch.cat([row["input_ids"], torch.zeros(missing, dtype=torch.long)]))
            attention_mask.append(
                torch.cat([row["attention_mask"], torch.zeros(missing, dtype=torch.long)])
            )
        return {
            "input_ids": torch.stack(input_ids),
            "attention_mask": torch.stack(attention_mask),
        }


def _row(tokens: list[int], target: int) -> dict[str, torch.Tensor]:
    row = {
        "input_ids": torch.tensor(tokens, dtype=torch.long),
        "attention_mask": torch.ones(len(tokens), dtype=torch.long),
    }
    row.update({name: torch.tensor(target, dtype=torch.long) for name in HEAD_NAMES})
    return row


def _example() -> ModerationExample:
    return ModerationExample(
        example_id="runtime-1",
        serialized="[0ms] A: test",
        label="SAFE",
        action="ALLOW",
        review_priority="NONE",
        strike=False,
        containment="NONE",
        containment_duration_seconds=None,
        support_flow="NONE",
        channel_profile="minecraft_public",
        platform_hint="minecraft",
        domain="gameplay",
        difficulty="normal",
        reason_codes=(),
        family_id=None,
    )


def test_dataset_caches_tokenization_across_epochs() -> None:
    tokenizer = _Tokenizer()
    dataset = ModerationDataset([_example()], tokenizer, 1024, "raw")
    first = dataset[0]
    second = dataset[0]
    assert tokenizer.calls == 1
    assert first.keys() == second.keys()
    for key in first:
        assert torch.equal(first[key], second[key])


def test_dynamic_collation_pads_only_to_longest_batch_member() -> None:
    rows = [_row([1, 2, 3], 0), _row([4, 5], 1)]
    batch = _collate_batch(_Tokenizer(), rows)
    assert tuple(batch["input_ids"].shape) == (2, 3)
    assert batch["input_ids"][1].tolist() == [4, 5, 0]
    assert batch["attention_mask"][1].tolist() == [1, 1, 0]
    for name in HEAD_NAMES:
        assert batch[name].tolist() == [0, 1]


def test_length_bucket_sampler_groups_similar_lengths_deterministically() -> None:
    dataset = object.__new__(ModerationDataset)
    dataset.encoded = [
        {"input_ids": torch.ones((1, width), dtype=torch.long)}
        for width in (1, 100, 2, 90, 3, 80)
    ]
    first = list(LengthBucketBatchSampler(dataset, 2, 42))
    second = list(LengthBucketBatchSampler(dataset, 2, 42))
    assert first == second
    assert {frozenset(batch) for batch in first} == {
        frozenset((0, 2)),
        frozenset((4, 5)),
        frozenset((3, 1)),
    }


class _FakeModel:
    def __init__(self) -> None:
        self.loaded = None

    def state_dict(self):
        return {"weight": torch.tensor([1.0])}

    def load_state_dict(self, state) -> None:
        self.loaded = state


def test_fit_runs_all_requested_epochs_and_keeps_best_state(monkeypatch) -> None:
    from workers.w25 import neural

    losses = iter([1.0, 1.2, 1.4, 0.8, 0.9])
    monkeypatch.setattr(neural, "_train_epoch", lambda *args: 0.5)
    monkeypatch.setattr(neural, "_dev_loss", lambda *args: next(losses))
    model = _FakeModel()
    result = neural._fit(
        model,
        object(),
        (object(), object()),
        object(),
        torch.device("cpu"),
        epochs=5,
    )
    assert result.best_dev_loss == 0.8
    assert len(result.history) == 5
    assert model.loaded is not None
