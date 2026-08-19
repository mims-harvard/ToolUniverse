"""CellTypist automated single-cell annotation — MCP server.

The upstream project distributes pickle-serialized scikit-learn objects.  This
provider never deserializes those files.  An administrator converts a reviewed,
digest-pinned upstream model once into a data-only NumPy archive; the live
service loads that archive with ``allow_pickle=False`` and reconstructs the
known logistic-regression/scaler factory in code.
"""

from __future__ import annotations

from collections import Counter
import os
from pathlib import Path
import threading
from typing import Any, Dict

import celltypist
from celltypist.models import Model
import numpy as np
import scanpy as sc
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server
from tooluniverse.remote_data_path import load_remote_h5ad


_DEFAULT_ALLOWED_MODELS = {
    "Adult_Mouse_Gut.pkl",
    "Human_Lung_Atlas.pkl",
    "Immune_All_High.pkl",
    "Immune_All_Low.pkl",
}
_MAX_MODEL_BYTES = 1_000_000_000
_MAX_FEATURES = 100_000
_MAX_CLASSES = 2_000
_MAX_INLINE_CELLS = 50_000
_MODEL_CACHE: dict[str, dict[str, Any]] = {}
_MODEL_LOCK = threading.Lock()


def _allowed_models() -> set[str]:
    configured = os.environ.get("TOOLUNIVERSE_CELLTYPIST_MODELS", "")
    if not configured.strip():
        return _DEFAULT_ALLOWED_MODELS
    return {name.strip() for name in configured.split(",") if name.strip()}


def _safe_model_path(model_name: str) -> Path:
    root_value = os.environ.get("CELLTYPIST_SAFE_MODEL_DIR", "").strip()
    if not root_value:
        raise ValueError("the provider must configure CELLTYPIST_SAFE_MODEL_DIR")
    try:
        root = Path(root_value).expanduser().resolve(strict=True)
        path = (root / f"{Path(model_name).stem}.npz").resolve(strict=True)
        path.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        raise ValueError("the configured safe CellTypist model is unavailable") from None
    if not root.is_dir() or not path.is_file() or path.suffix.lower() != ".npz":
        raise ValueError("the configured safe CellTypist model is unavailable")
    if path.stat().st_size > _MAX_MODEL_BYTES:
        raise ValueError("the configured safe CellTypist model exceeds the size limit")
    return path


def _strings(value: np.ndarray, name: str, maximum: int) -> np.ndarray:
    if value.ndim != 1 or not 1 <= value.size <= maximum or value.dtype.kind not in "US":
        raise ValueError(f"the safe CellTypist model has invalid {name}")
    result = value.astype(str)
    if any(not item or len(item) > 256 for item in result.tolist()):
        raise ValueError(f"the safe CellTypist model has invalid {name}")
    return result


def _load_safe_arrays(path: Path) -> dict[str, Any]:
    cache_key = str(path)
    with _MODEL_LOCK:
        cached = _MODEL_CACHE.get(cache_key)
        if cached is not None:
            return cached
        try:
            with np.load(path, allow_pickle=False) as archive:
                required = {
                    "coef", "intercept", "classes", "features", "scaler_mean",
                    "scaler_scale", "scaler_var", "with_mean", "source_sha256",
                }
                if set(archive.files) != required:
                    raise ValueError("unexpected fields")
                arrays = {name: archive[name].copy() for name in archive.files}
        except (OSError, ValueError):
            # Keep the public failure independent of parser/library details.
            raise ValueError("the safe CellTypist model archive is invalid") from None

        coef = np.asarray(arrays["coef"], dtype=np.float64)
        intercept = np.asarray(arrays["intercept"], dtype=np.float64)
        mean = np.asarray(arrays["scaler_mean"], dtype=np.float64)
        scale = np.asarray(arrays["scaler_scale"], dtype=np.float64)
        variance = np.asarray(arrays["scaler_var"], dtype=np.float64)
        features = _strings(arrays["features"], "features", _MAX_FEATURES)
        classes = _strings(arrays["classes"], "classes", _MAX_CLASSES)
        with_mean_raw = np.asarray(arrays["with_mean"])
        source_hash = _strings(
            np.asarray(arrays["source_sha256"]).reshape(-1), "source digest", 1
        )[0]
        expected_rows = {classes.size}
        if classes.size == 2:
            expected_rows.add(1)
        if len(source_hash) != 64 or any(ch not in "0123456789abcdef" for ch in source_hash):
            raise ValueError("the safe CellTypist model has an invalid source digest")
        if (
            coef.ndim != 2
            or intercept.ndim != 1
            or mean.shape != (features.size,)
            or scale.shape != (features.size,)
            or variance.shape != (features.size,)
            or coef.shape[1] != features.size
            or coef.shape[0] not in expected_rows
            or intercept.shape != (coef.shape[0],)
            or with_mean_raw.shape != (1,)
            or with_mean_raw.dtype.kind != "b"
            or np.unique(features).size != features.size
            or np.unique(classes).size != classes.size
            or not np.isfinite(coef).all()
            or not np.isfinite(intercept).all()
            or not np.isfinite(mean).all()
            or not np.isfinite(scale).all()
            or not np.isfinite(variance).all()
            or np.any(scale <= 0)
            or np.any(variance < 0)
        ):
            raise ValueError("the safe CellTypist model arrays are invalid")
        cached = {
            "coef": coef,
            "intercept": intercept,
            "classes": classes,
            "features": features,
            "mean": mean,
            "scale": scale,
            "variance": variance,
            "with_mean": bool(with_mean_raw.reshape(-1)[0]),
            "source_sha256": source_hash,
        }
        _MODEL_CACHE[cache_key] = cached
        return cached


def _build_model(arrays: dict[str, Any]) -> Model:
    classifier = LogisticRegression()
    classifier.coef_ = arrays["coef"].copy()
    classifier.intercept_ = arrays["intercept"].copy()
    classifier.classes_ = arrays["classes"].copy()
    classifier.features = arrays["features"].copy()
    classifier.n_features_in_ = int(arrays["features"].size)

    scaler = StandardScaler(with_mean=arrays["with_mean"])
    scaler.mean_ = arrays["mean"].copy()
    scaler.scale_ = arrays["scale"].copy()
    scaler.var_ = arrays["variance"].copy()
    scaler.n_features_in_ = int(arrays["features"].size)
    return Model(classifier, scaler, {"source_sha256": arrays["source_sha256"]})


@register_mcp_tool(
    tool_type_name="run_celltypist_annotate",
    config={
        "description": (
            "Annotate single-cell expression with CellTypist using a provider-"
            "converted data-only model archive. The live service never downloads "
            "or deserializes upstream pickle files."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "adata_path": {
                    "type": "string",
                    "description": "An .h5ad file inside the provider data directory containing log1p-normalized expression to 10,000 counts per cell.",
                },
                "model": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 128,
                    "default": "Immune_All_Low.pkl",
                    "description": "Provider-approved CellTypist model identity; the server maps it to a safe .npz archive.",
                },
                "majority_voting": {
                    "type": "boolean",
                    "default": True,
                    "description": "Refine predictions by CellTypist over-clustering when the dataset has more than 50 cells.",
                },
            },
            "required": ["adata_path"],
        },
    },
    mcp_config={
        "server_name": "CellTypist MCP Server",
        "host": "127.0.0.1",
        "port": 8014,
        "transport": "http",
    },
)
class CelltypistAnnotateTool:
    """Run CellTypist from a data-only provider artifact."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}
        adata_path = arguments.get("adata_path")
        if not adata_path:
            return {"error": "Missing required parameter: adata_path"}
        model_name = arguments.get("model") or "Immune_All_Low.pkl"
        if not isinstance(model_name, str) or model_name not in _allowed_models():
            return {"error": "The requested CellTypist model is not provider-approved."}
        majority_voting = arguments.get("majority_voting")
        majority_voting = True if majority_voting is None else majority_voting
        if not isinstance(majority_voting, bool):
            return {"error": "majority_voting must be a boolean."}
        try:
            model_path = _safe_model_path(model_name)
            arrays = _load_safe_arrays(model_path)
            adata = load_remote_h5ad(adata_path, sc.read_h5ad)
        except ValueError as exc:
            return {"error": str(exc)}
        if not 1 <= adata.n_obs <= _MAX_INLINE_CELLS:
            return {"error": f"CellTypist input must contain between 1 and {_MAX_INLINE_CELLS} cells."}

        try:
            result = celltypist.annotate(
                adata,
                model=_build_model(arrays),
                majority_voting=majority_voting,
            )
            label_column = (
                "majority_voting"
                if majority_voting and "majority_voting" in result.predicted_labels
                else "predicted_labels"
            )
            labels = result.predicted_labels[label_column].astype(str).tolist()
            cell_ids = [str(cell) for cell in adata.obs_names]
        except Exception:
            return {"error": "CellTypist annotation failed on the provider."}
        if (
            len(labels) != adata.n_obs
            or len(cell_ids) != adata.n_obs
            or any(not label or len(label) > 256 for label in labels)
            or any(not cell or len(cell) > 256 for cell in cell_ids)
        ):
            return {"error": "CellTypist returned invalid aligned labels."}
        return {
            "model": model_name,
            "artifact_format": "celltypist-safe-npz-v1",
            "source_sha256": arrays["source_sha256"],
            "majority_voting": label_column == "majority_voting",
            "n_cells": int(adata.n_obs),
            "cell_ids": cell_ids,
            "predicted_labels": labels,
            "label_counts": dict(Counter(labels)),
        }


if __name__ == "__main__":
    start_mcp_server()
