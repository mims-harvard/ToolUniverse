"""COMPASS immune-checkpoint-response prediction MCP server.

The official release checkpoint is a pickled ``FineTuner``. Providers convert
one reviewed, digest-pinned checkpoint offline with ``convert_checkpoint.py``.
This live module only reads safetensors, JSON, and an ``allow_pickle=False``
NumPy archive, then reconstructs the reviewed COMPASS architecture in code.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
from pathlib import Path
import threading
from typing import Any, List, Optional, Tuple

from fastmcp import FastMCP
import numpy as np
import pandas as pd

from tooluniverse.remote_data_path import resolve_remote_data_path
from tooluniverse.server_security import (
    get_fastmcp_token_auth,
    run_fastmcp_server,
)


server = FastMCP("COMPASS Prediction SMCP Server", auth=get_fastmcp_token_auth())

_MAX_EXPRESSION_FILE_BYTES = 50_000_000
_MAX_GENES = 100_000
_MAX_WEIGHTS_BYTES = 256_000_000
_MAX_PREPROCESSING_BYTES = 32_000_000
_MODEL_LOCK = threading.Lock()
_COMPASS_TOOL: Optional["CompassTool"] = None

# The public provider artifact is deliberately narrower than the general
# upstream training factory. Expanding this set requires a new code review.
_EXPECTED_MODEL_ARGS = {
    "input_dim": 15672,
    "task_dim": 2,
    "task_type": "c",
    "proj_level": "cellpathway",
    "proj_pid": False,
    "proj_cancer_type": True,
    "proj_disentangled": True,
    "embed_dim": 44,
    "num_cancer_types": 33,
    "encoder": "performer",
    "encoder_dropout": 0.2,
    "transformer_dim": 32,
    "transformer_nhead": 2,
    "transformer_num_layers": 1,
    "transformer_pos_emb": "learnable",
    "task_batch_norms": True,
    "task_dense_layer": [16],
    "seed": 42,
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError:
        raise ValueError("the configured safe COMPASS artifact is unavailable") from None
    return digest.hexdigest()


def _digest(value: Any, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise ValueError(f"the safe COMPASS artifact has an invalid {name}")
    return value


def _artifact_dir(configured: Optional[str] = None) -> Path:
    value = (
        configured
        if configured is not None
        else os.environ.get("COMPASS_SAFE_MODEL_DIR", "")
    )
    if not isinstance(value, str):
        raise ValueError("the provider must configure COMPASS_SAFE_MODEL_DIR")
    if not value.strip():
        raise ValueError("the provider must configure COMPASS_SAFE_MODEL_DIR")
    try:
        root = Path(value).expanduser().resolve(strict=True)
    except (OSError, RuntimeError):
        raise ValueError("the configured safe COMPASS artifact is unavailable") from None
    if not root.is_dir():
        raise ValueError("the configured safe COMPASS artifact is unavailable")
    return root


class _SafeMinMaxScaler:
    def __init__(self, feature_names: np.ndarray, scale: np.ndarray, minimum: np.ndarray):
        self.feature_names = feature_names
        self.scale = scale
        self.minimum = minimum

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        metadata = frame[[frame.columns[0]]]
        values = np.log2(frame[self.feature_names].to_numpy(dtype=np.float64) + 1.0)
        scaled = values * self.scale + self.minimum
        return metadata.join(
            pd.DataFrame(scaled, columns=self.feature_names, index=frame.index)
        )


class _SafeCompassRunner:
    def __init__(self, model: Any, scaler: _SafeMinMaxScaler, feature_names: np.ndarray, device: str):
        self.model = model
        self.scaler = scaler
        self.feature_names = feature_names
        self.device = device

    def _select(self, frame: pd.DataFrame) -> pd.DataFrame:
        return frame[[frame.columns[0], *self.feature_names.tolist()]]

    def predict(self, frame: pd.DataFrame):
        from compass.model.tune import Predictor

        return Predictor(
            self._select(frame),
            self.model,
            self.scaler,
            device=self.device,
            batch_size=1,
            num_workers=0,
        )

    def extract(self, frame: pd.DataFrame):
        from compass.model.tune import Extractor

        return Extractor(
            self._select(frame),
            self.model,
            self.scaler,
            device=self.device,
            batch_size=1,
            num_workers=0,
            with_gene_level=True,
        )


def _load_safe_runner(root: Path, device: str) -> tuple[_SafeCompassRunner, dict[str, Any]]:
    metadata_path = root / "metadata.json"
    preprocessing_path = root / "preprocessing.npz"
    weights_path = root / "model.safetensors"
    if not metadata_path.is_file() or not preprocessing_path.is_file() or not weights_path.is_file():
        raise ValueError("the configured safe COMPASS artifact is incomplete")
    if (
        metadata_path.stat().st_size > 100_000
        or preprocessing_path.stat().st_size > _MAX_PREPROCESSING_BYTES
        or weights_path.stat().st_size > _MAX_WEIGHTS_BYTES
    ):
        raise ValueError("the configured safe COMPASS artifact exceeds its size limit")
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ValueError("the safe COMPASS metadata is invalid") from None
    required = {
        "format",
        "source_sha256",
        "upstream_revision",
        "model_args",
        "scale_method",
        "weights_sha256",
        "preprocessing_sha256",
    }
    if not isinstance(metadata, dict) or set(metadata) != required:
        raise ValueError("the safe COMPASS metadata is invalid")
    if metadata["format"] != "compass-safe-v1" or metadata["scale_method"] != "minmax":
        raise ValueError("the safe COMPASS artifact format is unsupported")
    _digest(metadata["source_sha256"], "source digest")
    _digest(metadata["weights_sha256"], "weights digest")
    _digest(metadata["preprocessing_sha256"], "preprocessing digest")
    revision = metadata["upstream_revision"]
    if (
        not isinstance(revision, str)
        or len(revision) != 40
        or any(ch not in "0123456789abcdef" for ch in revision)
    ):
        raise ValueError("the safe COMPASS artifact has an invalid upstream revision")
    if metadata["model_args"] != _EXPECTED_MODEL_ARGS:
        raise ValueError("the safe COMPASS model architecture is not provider-approved")
    if _sha256(weights_path) != metadata["weights_sha256"]:
        raise ValueError("the safe COMPASS weights digest does not match")
    if _sha256(preprocessing_path) != metadata["preprocessing_sha256"]:
        raise ValueError("the safe COMPASS preprocessing digest does not match")

    try:
        with np.load(preprocessing_path, allow_pickle=False) as archive:
            if set(archive.files) != {"feature_names", "min", "scale"}:
                raise ValueError("unexpected preprocessing fields")
            feature_names = archive["feature_names"].copy()
            minimum = np.asarray(archive["min"], dtype=np.float64)
            scale = np.asarray(archive["scale"], dtype=np.float64)
    except (OSError, ValueError):
        raise ValueError("the safe COMPASS preprocessing archive is invalid") from None
    expected_shape = (_EXPECTED_MODEL_ARGS["input_dim"],)
    if (
        feature_names.shape != expected_shape
        or feature_names.dtype.kind not in "US"
        or minimum.shape != expected_shape
        or scale.shape != expected_shape
        or np.unique(feature_names).size != feature_names.size
        or any(not name or len(name) > 64 for name in feature_names.astype(str).tolist())
        or not np.isfinite(minimum).all()
        or not np.isfinite(scale).all()
        or np.any(scale <= 0)
    ):
        raise ValueError("the safe COMPASS preprocessing arrays are invalid")
    feature_names = feature_names.astype(str)

    try:
        import torch
        from safetensors.torch import load_file
        from compass.model.model import Compass

        if device == "cuda" and not torch.cuda.is_available():
            raise ValueError("COMPASS_DEVICE requests CUDA, but CUDA is unavailable")
        state = load_file(weights_path, device="cpu")
        model = Compass(**_EXPECTED_MODEL_ARGS)
        model.load_state_dict(state, strict=True)
        model = model.to(device)
        model.eval()
    except ValueError:
        raise
    except Exception:
        raise RuntimeError("the safe COMPASS model could not be constructed") from None
    scaler = _SafeMinMaxScaler(feature_names, scale, minimum)
    return _SafeCompassRunner(model, scaler, feature_names, device), metadata


class CompassTool:
    """Provider-configured COMPASS inference over a safe converted artifact."""

    def __init__(self, safe_model_dir: Optional[str] = None, device: Optional[str] = None):
        selected_device = device or os.environ.get("COMPASS_DEVICE", "cpu")
        if selected_device not in {"cpu", "cuda"}:
            raise ValueError("COMPASS_DEVICE must be either 'cpu' or 'cuda'")
        self.runner, self.metadata = _load_safe_runner(
            _artifact_dir(safe_model_dir), selected_device
        )
        self.feature_names = self.runner.feature_names
        self.num_cancer_types = int(_EXPECTED_MODEL_ARGS["num_cancer_types"])
        self._inference_lock = threading.Lock()

    @staticmethod
    def _get_top_columns_per_row(
        frame: pd.DataFrame,
        top_n: int = 44,
        exclude: Optional[List[str]] = None,
    ) -> List[List[Tuple[str, float]]]:
        excluded = set(exclude or ["CANCER", "Reference"])
        results: List[List[Tuple[str, float]]] = []
        for _, row in frame.iterrows():
            ranked = row.sort_values(ascending=False)
            results.append(
                [
                    (str(name), float(value))
                    for name, value in ranked.items()
                    if name not in excluded
                ][:top_n]
            )
        return results

    def _load_expression(self, requested_path: str) -> pd.DataFrame:
        path = resolve_remote_data_path(
            requested_path, allowed_suffixes={".csv", ".tsv", ".txt"}
        )
        if path.stat().st_size > _MAX_EXPRESSION_FILE_BYTES:
            raise ValueError("the TPM expression table exceeds the 50 MB limit")
        separator = "," if path.suffix.lower() == ".csv" else "\t"
        try:
            frame = pd.read_csv(path, sep=separator)
        except Exception:
            raise ValueError("the requested TPM expression table could not be read") from None
        if frame.shape[0] != 1:
            raise ValueError("the TPM expression table must contain exactly one sample")
        if not 3 <= frame.shape[1] <= _MAX_GENES + 2:
            raise ValueError(f"the TPM table may contain at most {_MAX_GENES} genes")
        if frame.columns[0] != "Index" or frame.columns[1] != "cancer_code":
            raise ValueError("the TPM table must begin with Index and cancer_code columns")
        if frame.columns.duplicated().any():
            raise ValueError("the TPM table contains duplicate columns")
        sample_id = str(frame.iloc[0, 0])
        if not sample_id or len(sample_id) > 256:
            raise ValueError("the TPM table has an invalid sample identifier")
        try:
            cancer_code = float(frame.iloc[0, 1])
        except (TypeError, ValueError):
            raise ValueError("cancer_code must be an integer model category") from None
        if (
            not math.isfinite(cancer_code)
            or not cancer_code.is_integer()
            or not 0 <= cancer_code < self.num_cancer_types
        ):
            raise ValueError("cancer_code must be an integer model category from 0 through 32")
        genes = frame.columns[2:].tolist()
        if any(not isinstance(gene, str) or not gene or len(gene) > 64 for gene in genes):
            raise ValueError("the TPM table contains an invalid gene name")
        missing = sorted(set(self.feature_names) - set(genes))
        if missing:
            raise ValueError(
                f"the TPM table is missing {len(missing)} required COMPASS genes"
            )
        try:
            numeric = frame.iloc[:, 2:].apply(pd.to_numeric, errors="raise")
        except Exception:
            raise ValueError("the TPM expression values must be numeric") from None
        values = numeric.to_numpy(dtype=np.float64)
        if not np.isfinite(values).all() or np.any(values < 0):
            raise ValueError("the TPM expression values must be finite and non-negative")
        result = pd.concat(
            [
                pd.Series([int(cancer_code)], name="cancer_code"),
                numeric.reset_index(drop=True),
            ],
            axis=1,
        )
        result.index = pd.Index([sample_id], name="Index")
        return result

    def predict(self, requested_path: str, threshold: float) -> dict[str, Any]:
        frame = self._load_expression(requested_path)
        with self._inference_lock:
            _, prediction = self.runner.predict(frame)
            _, _, concepts = self.runner.extract(frame)
        if prediction.shape != (1, 2) or concepts.shape[0] != 1:
            raise RuntimeError("COMPASS returned an invalid prediction shape")
        probability = float(prediction.iloc[0, 1])
        concept_values = concepts.to_numpy(dtype=np.float64)
        if not math.isfinite(probability) or not np.isfinite(concept_values).all():
            raise RuntimeError("COMPASS returned non-finite prediction values")
        ranked = self._get_top_columns_per_row(concepts)[0]
        return {
            "prediction": {
                "is_responder": probability >= threshold,
                "responder_probability": probability,
                "threshold": float(threshold),
                "top_concepts": [
                    {"concept": name, "score": score} for name, score in ranked
                ],
            },
            "model": {
                "artifact_format": self.metadata["format"],
                "source_sha256": self.metadata["source_sha256"],
                "upstream_revision": self.metadata["upstream_revision"],
                "device": self.runner.device,
            },
            "context_info": [
                "COMPASS inference completed with the provider-approved model artifact."
            ],
        }


def _get_compass_tool() -> CompassTool:
    global _COMPASS_TOOL
    if _COMPASS_TOOL is None:
        with _MODEL_LOCK:
            if _COMPASS_TOOL is None:
                _COMPASS_TOOL = CompassTool()
    return _COMPASS_TOOL


@server.tool()
async def run_compass_prediction(
    gene_expression_data_path: str,
    threshold: float = 0.5,
):
    """Predict ICI response for one provider-rooted COMPASS TPM table."""
    if not isinstance(gene_expression_data_path, str) or not gene_expression_data_path:
        return {
            "error": "gene_expression_data_path must be a non-empty string.",
            "context_info": ["Please select a provider-approved TPM table."],
        }
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not math.isfinite(threshold)
        or not 0.0 <= threshold <= 1.0
    ):
        return {
            "error": "threshold must be a finite number between 0.0 and 1.0.",
            "context_info": ["Please check the prediction threshold."],
        }
    try:
        return await asyncio.to_thread(
            _get_compass_tool().predict,
            gene_expression_data_path,
            float(threshold),
        )
    except (ValueError, RuntimeError) as exc:
        return {
            "error": str(exc),
            "context_info": ["COMPASS inference did not complete."],
        }
    except Exception:
        return {
            "error": "COMPASS inference failed on the provider.",
            "context_info": ["COMPASS inference did not complete."],
        }


if __name__ == "__main__":
    run_fastmcp_server(
        server,
        host=os.getenv("TOOLUNIVERSE_MCP_HOST", "127.0.0.1"),
        port=7003,
        stateless_http=True,
    )
