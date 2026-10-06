"""Safe data-only artifact export for W25 lexical/fusion components."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np  # pyright: ignore[reportMissingImports]

if TYPE_CHECKING:
    from workers.w25.lexical import LexicalFusionModel


def export_lexical_artifact(
    model: LexicalFusionModel,
    output_dir: Path,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    word = _write_vectorizer(model.word, output_dir / "word-vectorizer.json")
    char = _write_vectorizer(model.char, output_dir / "char-vectorizer.json")
    heads = _write_heads(model.heads, output_dir / "heads.npz")
    metadata = {
        "schema_version": 1,
        "format": "w25-safe-data-only-v1",
        "production_safe_data_format": True,
        "runtime_adapter_required": True,
        "use_embeddings": model.use_embeddings,
        "serialization_variant": model.serialization_variant,
        "word_vectorizer": word,
        "char_vectorizer": char,
        "heads": heads,
    }
    metadata_path = output_dir / "metadata.json"
    _write_json(metadata_path, metadata)
    metadata["metadata"] = _file_record(metadata_path)
    metadata["total_bytes"] = sum(
        int(item["bytes"]) for item in (word, char, heads, metadata["metadata"])
    )
    return metadata


def _write_vectorizer(vectorizer, path: Path) -> dict[str, object]:
    payload = {
        "terms": vectorizer.get_feature_names_out().tolist(),
        "idf": np.asarray(vectorizer.idf_, dtype=np.float32).tolist(),
        "analyzer": vectorizer.analyzer,
        "ngram_range": list(vectorizer.ngram_range),
        "lowercase": bool(vectorizer.lowercase),
        "sublinear_tf": bool(vectorizer.sublinear_tf),
        "norm": vectorizer.norm,
        "token_pattern": vectorizer.token_pattern,
    }
    _write_json(path, payload)
    record = _file_record(path)
    record["feature_count"] = len(payload["terms"])
    return record


def _write_heads(heads: dict[str, object], path: Path) -> dict[str, object]:
    arrays = {}
    for name, head in heads.items():
        arrays[f"{name}__coef"] = np.asarray(head.coef_, dtype=np.float32)
        arrays[f"{name}__intercept"] = np.asarray(head.intercept_, dtype=np.float32)
        arrays[f"{name}__classes"] = np.asarray(head.classes_, dtype=np.int64)
    np.savez_compressed(path, **arrays)
    record = _file_record(path)
    record["head_count"] = len(heads)
    return record


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def _file_record(path: Path) -> dict[str, object]:
    return {
        "path": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
    }
