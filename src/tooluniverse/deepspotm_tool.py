"""DeepSpot-M: predict spatial gene expression from an H&E histology tile.

Wraps the ``deepspotm`` package (https://github.com/ratschlab/DeepSpotM), a
multimodal foundation model that maps a 224x224 H&E tile to spatial gene
expression. Genes are represented as queryable embeddings rather than fixed
outputs, so a single model covers the protein-coding transcriptome.

Neither the package nor its weights are vendored here. ``deepspotm`` is an
optional dependency and the weights are gated on the Hugging Face Hub, so the
tool reports an actionable error instead of failing obscurely when either is
missing. Unlike some other model-backed tools, the model is loaded lazily on
first use rather than in ``__init__``, so merely constructing the tool never
reaches for the network.

Paper: https://doi.org/10.64898/2026.06.19.26356060
Weights are CC-BY-NC-SA-4.0 and the code is PolyForm Noncommercial 1.0.0:
non-commercial research use only, not for clinical or diagnostic use.
"""

import os
import threading
from typing import Any, Dict, Optional

from .base_tool import BaseTool
from .tool_registry import register_tool

# The gene-embedding sources the released checkpoint ships with.
SOURCES = ("evo2", "orthrus", "prott5", "scgpt", "apertus")

DEFAULT_REPO = "ratschlab/DeepSpotM"

# The model was trained on 224x224 tiles cut at roughly 20x (~0.5 microns per
# pixel). There is no way to recover the magnification from a bare image file,
# so the tool cannot verify it -- it is stated in the schema and enforced only
# to the extent that the pixel dimensions must match.
TILE_SIZE = 224

INSTALL_HINT = (
    "DeepSpot-M needs the 'deepspotm' package and access to its gated "
    "weights. Install with 'pip install deepspotm', request access at "
    "https://huggingface.co/ratschlab/DeepSpotM, then authenticate with "
    "'huggingface-cli login'."
)


def _error(message: str, **extra: Any) -> Dict[str, Any]:
    """Build the {status, error} shape the other model-backed tools return."""
    return {"status": "error", "error": message, **extra}


@register_tool("DeepSpotMTool")
class DeepSpotMTool(BaseTool):
    """Predict spatial gene expression for a 224x224 H&E tile.

    Takes a local image path and a list of gene symbols and returns the
    predicted expression of those genes for that tile. Asking for specific
    genes is much cheaper than the full ~19k panel, because only the requested
    gene queries run through the cross-attention decoder.
    """

    def __init__(self, tool_config: Optional[dict] = None, **kwargs: Any) -> None:
        super().__init__(tool_config or kwargs.pop("tool_config", {}), **kwargs)
        # Cache one loaded model per (repo, source, device); loading is
        # expensive and agents typically ask for many tiles in a row.
        self._models: Dict[tuple, tuple] = {}
        self._lock = threading.Lock()

    # -- model loading ---------------------------------------------------

    def _load(self, repo: str, source: str, device: str) -> tuple:
        """Return (model, image_processor), loading and caching on first use."""
        key = (repo, source, device)
        with self._lock:
            if key in self._models:
                return self._models[key]

            try:
                from deepspotm import DeepSpotM
            except ImportError as exc:  # package not installed
                raise ImportError(INSTALL_HINT) from exc

            model, image_processor = DeepSpotM.from_pretrained(repo, source=source)
            model = model.to(device).eval()
            self._models[key] = (model, image_processor)
            return self._models[key]

    @staticmethod
    def _resolve_device(requested: Optional[str]) -> str:
        if requested and requested != "auto":
            return requested
        try:
            import torch

            return "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            return "cpu"

    # -- execution -------------------------------------------------------

    def run(self, arguments: Optional[dict] = None) -> Dict[str, Any]:
        """Predict expression of the requested genes for one H&E tile."""
        arguments = arguments or {}

        image_path = arguments.get("image_path")
        if not image_path:
            return _error("'image_path' is required.")
        if not os.path.isfile(image_path):
            return _error(f"No such image file: {image_path}")

        genes = arguments.get("genes")
        if isinstance(genes, str):
            genes = [genes]
        if not genes:
            return _error(
                "'genes' is required: pass one or more HGNC gene symbols, "
                "for example ['EPCAM', 'CD3D', 'PTPRC']. The full ~19k-gene "
                "panel is deliberately not returned in one call."
            )

        source = arguments.get("source", "scgpt")
        if source not in SOURCES:
            return _error(
                f"Unknown source {source!r}. Choose one of: {', '.join(SOURCES)}."
            )

        repo = arguments.get("model_repo", DEFAULT_REPO)
        device = self._resolve_device(arguments.get("device"))

        try:
            from PIL import Image
        except ImportError as exc:
            return _error(f"Pillow is required to read the tile: {exc}")

        try:
            with Image.open(image_path) as handle:
                tile = handle.convert("RGB")
        except Exception as exc:
            return _error(f"Could not read {image_path} as an image: {exc}")

        if tile.size != (TILE_SIZE, TILE_SIZE):
            return _error(
                f"Tile is {tile.size[0]}x{tile.size[1]} px; DeepSpot-M expects "
                f"exactly {TILE_SIZE}x{TILE_SIZE}. Cut tiles on a "
                f"{TILE_SIZE}-px grid at roughly 20x (~0.5 microns per pixel), "
                "the magnification the model was trained on. Feeding tiles at "
                "another scale silently degrades the predictions."
            )

        try:
            model, image_processor = self._load(repo, source, device)
        except ImportError as exc:
            return _error(str(exc), retriable=False)
        except Exception as exc:
            return _error(
                f"Could not load DeepSpot-M from {repo!r}: {exc}. {INSTALL_HINT}"
            )

        known = set(getattr(model, "gene_names", ()) or ())
        unknown = [g for g in genes if g not in known] if known else []
        if unknown:
            return _error(
                f"These genes are not in the model's panel: "
                f"{', '.join(unknown)}. Predicting genes outside the released "
                "panel would require regenerating the source gene embeddings.",
                unknown_genes=unknown,
            )

        try:
            import torch

            pixel_values = image_processor(tile).unsqueeze(0).to(device)
            with torch.no_grad():
                values = model.predict_genes(pixel_values, list(genes))
            flat = values.float().cpu().numpy().reshape(-1).tolist()
        except Exception as exc:
            return _error(f"Prediction failed: {exc}")

        return {
            "genes": dict(zip(genes, flat)),
            "units": "log1p-CPM",
            "source": source,
            "device": device,
            "model_repo": repo,
            "note": (
                "Predicted, not measured, expression for a single "
                f"{TILE_SIZE}x{TILE_SIZE} H&E tile. Non-commercial research "
                "use only; not for clinical or diagnostic use."
            ),
        }
