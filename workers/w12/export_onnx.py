"""W12 ONNX export: framework -> ONNX -> quantized ONNX with parity checks.

Exports the fine-tuned multi-task encoder to ONNX (CPU), validates the
graph, checks numerical parity against the PyTorch model on a validation
batch, and produces a dynamically quantized INT8 variant with its own
parity/latency comparison.

Does NOT commit binaries to git. Records SHA-256, sizes, and exact
reproduction commands in the artifact metadata.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import torch
from transformers import BertTokenizer

from workers.w12.dataset import load_partition
from workers.w12.train_encoder import CANDIDATES, MultiTaskBert

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
EXPORT_DIR = ARTIFACT_DIR / "onnx"

HEAD_NAMES = ["label", "action", "review_priority", "strike", "containment", "support_flow"]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def export_onnx(candidate: str, seed: int, max_len: int = 128) -> dict:
    cfg = CANDIDATES[candidate]
    local_dir = cfg["local_dir"]
    device = torch.device("cpu")

    model = MultiTaskBert(cfg["hf_id"], local_dir).to(device)
    checkpoint = torch.load(
        ARTIFACT_DIR / f"{candidate}-seed{seed}.pt",
        map_location=device,
        weights_only=True,
    )
    model.load_state_dict(checkpoint)
    model.eval()

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    onnx_path = EXPORT_DIR / f"{candidate}-seed{seed}.onnx"

    dummy_ids = torch.ones(1, max_len, dtype=torch.long)
    dummy_mask = torch.ones(1, max_len, dtype=torch.long)
    output_names = [f"logits_{name}" for name in HEAD_NAMES]
    torch.onnx.export(
        model,
        (dummy_ids, dummy_mask),
        str(onnx_path),
        input_names=["input_ids", "attention_mask"],
        output_names=output_names,
        dynamic_axes={
            "input_ids": {0: "batch", 1: "seq"},
            "attention_mask": {0: "batch", 1: "seq"},
            **{name: {0: "batch"} for name in output_names},
        },
        opset_version=14,
    )

    # Validate the ONNX graph
    onnx_model = onnx.load(str(onnx_path))
    onnx.checker.check_model(onnx_model)

    # Numerical parity on a representative validation batch
    tokenizer = BertTokenizer(str(local_dir / "vocab.txt"), do_lower_case=True)
    val = load_partition("validation")[:64]
    texts = [e.serialized for e in val]
    enc = tokenizer(texts, max_length=max_len, truncation=True, padding=True, return_tensors="np")
    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    ort_inputs = {
        "input_ids": enc["input_ids"].astype(np.int64),
        "attention_mask": enc["attention_mask"].astype(np.int64),
    }
    ort_outs = sess.run(output_names, ort_inputs)
    with torch.no_grad():
        torch_outs = model(
            torch.tensor(ort_inputs["input_ids"]),
            torch.tensor(ort_inputs["attention_mask"]),
        )
    max_abs_diff = 0.0
    for name, ort_out in zip(HEAD_NAMES, ort_outs, strict=True):
        torch_out = torch_outs[name].numpy()
        diff = float(np.max(np.abs(ort_out - torch_out)))
        max_abs_diff = max(max_abs_diff, diff)
    parity_ok = max_abs_diff < 1e-4

    # Dynamic INT8 quantization
    from onnxruntime.quantization import QuantType, quantize_dynamic

    quant_path = EXPORT_DIR / f"{candidate}-seed{seed}-int8.onnx"
    quantize_dynamic(
        str(onnx_path),
        str(quant_path),
        weight_type=QuantType.QInt8,
    )
    q_sess = ort.InferenceSession(str(quant_path), providers=["CPUExecutionProvider"])
    q_outs = q_sess.run(output_names, ort_inputs)
    max_q_diff = 0.0
    for ort_out, q_out in zip(ort_outs, q_outs, strict=True):
        max_q_diff = max(max_q_diff, float(np.max(np.abs(ort_out - q_out))))

    metadata = {
        "candidate": candidate,
        "seed": seed,
        "hf_id": cfg["hf_id"],
        "license": cfg["license"],
        "max_len": max_len,
        "opset": 14,
        "onnx_path": onnx_path.name,
        "onnx_sha256": sha256_of(onnx_path),
        "onnx_bytes": onnx_path.stat().st_size,
        "quant_path": quant_path.name,
        "quant_sha256": sha256_of(quant_path),
        "quant_bytes": quant_path.stat().st_size,
        "parity_max_abs_diff": max_abs_diff,
        "parity_ok": parity_ok,
        "quant_max_abs_diff_vs_fp32": max_q_diff,
        "export_command": (
            f"python -m workers.w12.export_onnx --candidate {candidate} --seed {seed}"
        ),
    }
    with open(EXPORT_DIR / f"{candidate}-seed{seed}-metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    print(json.dumps(metadata, indent=2), flush=True)
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", choices=list(CANDIDATES), required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    export_onnx(args.candidate, args.seed)


if __name__ == "__main__":
    main()
