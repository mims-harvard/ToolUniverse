"""Cellpose tool — local deep-learning cell/nucleus segmentation.

Wraps the `cellpose <https://github.com/MouseLand/cellpose>`_ Python package to
segment cells or nuclei from a single microscopy image *locally* (no API, no key).
Given an image file path it returns the number of segmented objects, per-object
areas and centroids, and (optionally) the path to a saved label-mask image.

This is a true local-compute tool and a genuine capability gap in ToolUniverse:
no existing tool performs instance segmentation of microscopy images. (The
"segment"/"segmentation" hits in other tool configs refer to genomic segments or
to remote BioImage-Archive/CryoET dataset metadata, not local image segmentation.)

Cellpose API note
-----------------
Cellpose 3.x exposed ``models.Cellpose(model_type='cyto3'|'nuclei'|'cyto')`` and a
zoo of named models. Cellpose 4.x removed that class and replaced the zoo with a
single unified model (CPSAM); there, ``model_type`` is accepted but **ignored**.
This tool supports both generations: it uses ``models.Cellpose`` when available
(3.x, honoring ``model_type``) and otherwise falls back to ``models.CellposeModel``
(4.x). The model actually used is reported back in the result so callers are never
misled about whether ``model_type`` took effect.

Runtime / dependency notes
--------------------------
- ``pip install cellpose`` (torch is a dependency). Declared as an optional
  ``required_packages`` entry; ``run()`` returns a clean error if unavailable.
- On first use, cellpose downloads model weights (small in 3.x; ~1 GB CPSAM in
  4.x) and caches them. The first call is therefore slow; later calls reuse the
  cached weights and a per-process cached model instance. CPU inference on a
  256x256 image takes on the order of a minute or two; GPU is much faster.
"""

import os

from .base_tool import BaseTool
from .tool_registry import register_tool

# Optional dependency import at module load so a missing package becomes a clean
# error rather than an exception (framework optional-dependency pattern).
CELLPOSE_AVAILABLE = False
_IMPORT_ERROR = None
try:
    import numpy as np  # noqa: E402
    from cellpose import models as _cp_models  # noqa: E402

    CELLPOSE_AVAILABLE = True
except Exception as exc:  # ImportError, or a downstream import failure
    np = None
    _cp_models = None
    _IMPORT_ERROR = str(exc)

# Legacy cellpose-3.x model types accepted from the caller. In 4.x these are
# ignored by the unified model but still accepted so callers/tests are stable.
_LEGACY_MODEL_TYPES = ("cyto3", "cyto2", "cyto", "nuclei")

# Image extensions we know how to load.
_TIFF_EXTS = (".tif", ".tiff")
_PIL_EXTS = (".png", ".jpg", ".jpeg", ".bmp")


@register_tool("CellposeTool")
class CellposeTool(BaseTool):
    """Segment cells/nuclei in a microscopy image with Cellpose (local compute).

    Arguments (in ``arguments``)
    ----------------------------
    image_path : str
        Path to a local microscopy image (.tif/.tiff/.png/.jpg/.bmp).
    model_type : str, optional
        One of ``cyto3``, ``cyto``, ``cyto2``, ``nuclei`` (default ``cyto3``).
        Honored on cellpose 3.x; ignored by the unified model on 4.x (the
        ``model_used`` field reports what actually ran).
    diameter : float, optional
        Expected object diameter in pixels. ``None``/0 lets cellpose estimate it.
    channels : list[int], optional
        Two-element ``[cytoplasm, nucleus]`` channel spec, e.g. ``[0, 0]`` for a
        grayscale image (default). Used by cellpose 3.x; 4.x infers channels.
    save_mask : bool, optional
        If true, save the integer label mask next to the image (or to
        ``mask_output_path``) and return its path. Default false.
    mask_output_path : str, optional
        Where to write the mask image when ``save_mask`` is true. Defaults to
        ``<image_path>_cp_masks.png``.
    """

    # Cache loaded models per (class, key) — model construction (and the 4.x
    # weight load) is expensive, so reuse within a process.
    _model_cache: dict = {}

    @classmethod
    def _get_model(cls, model_type):
        """Return a cached/new cellpose model and the actual model identifier used."""
        # Prefer the 3.x unified ``Cellpose`` class (honors model_type); fall back
        # to 4.x ``CellposeModel`` (single CPSAM model, model_type ignored).
        if hasattr(_cp_models, "Cellpose"):
            cache_key = ("Cellpose", model_type)
            if cache_key not in cls._model_cache:
                cls._model_cache[cache_key] = (
                    _cp_models.Cellpose(gpu=False, model_type=model_type),
                    model_type,
                )
            return cls._model_cache[cache_key]

        cache_key = ("CellposeModel", None)
        if cache_key not in cls._model_cache:
            model = _cp_models.CellposeModel(gpu=False)
            model_used = getattr(model, "pretrained_model", "cellpose-default")
            if isinstance(model_used, (list, tuple)):
                model_used = model_used[0] if model_used else "cellpose-default"
            model_used = os.path.basename(str(model_used))
            cls._model_cache[cache_key] = (model, model_used)
        return cls._model_cache[cache_key]

    @staticmethod
    def _load_image(image_path):
        """Load an image into a 2D/3D numpy array. Returns (array, error_or_None)."""
        ext = os.path.splitext(image_path)[1].lower()
        try:
            if ext in _TIFF_EXTS:
                try:
                    import tifffile

                    arr = tifffile.imread(image_path)
                except Exception:
                    from PIL import Image

                    arr = np.array(Image.open(image_path))
            elif ext in _PIL_EXTS:
                from PIL import Image

                arr = np.array(Image.open(image_path))
            else:
                # Last-ditch attempt via PIL; report unsupported extension if it fails.
                try:
                    from PIL import Image

                    arr = np.array(Image.open(image_path))
                except Exception:
                    return None, (
                        f"Unsupported image extension '{ext}'. Supported: "
                        + ", ".join(_TIFF_EXTS + _PIL_EXTS)
                    )
        except Exception as exc:
            return None, f"Failed to read image '{image_path}': {exc}"

        if arr is None or getattr(arr, "size", 0) == 0:
            return None, f"Image '{image_path}' is empty or could not be decoded."
        return arr, None

    @staticmethod
    def _object_stats(masks):
        """Compute count and per-object area/centroid from an integer label mask."""
        labels = [int(v) for v in np.unique(masks) if int(v) != 0]
        objects = []
        for label in labels:
            ys, xs = np.where(masks == label)
            objects.append(
                {
                    "label": label,
                    "area": int(ys.size),
                    "centroid_y": float(ys.mean()),
                    "centroid_x": float(xs.mean()),
                }
            )
        return objects

    def _save_mask(self, masks, image_path, mask_output_path):
        """Write the label mask to disk. Returns (path_or_None, error_or_None)."""
        out_path = mask_output_path or (
            os.path.splitext(image_path)[0] + "_cp_masks.png"
        )
        try:
            from PIL import Image

            # 16-bit grayscale preserves up to 65535 distinct object labels.
            mask16 = masks.astype(np.uint16)
            Image.fromarray(mask16).save(out_path)
            return out_path, None
        except Exception as exc:
            return None, f"Failed to save mask to '{out_path}': {exc}"

    def run(self, arguments=None):
        arguments = arguments or {}

        if not CELLPOSE_AVAILABLE:
            return {
                "status": "error",
                "error": (
                    "The 'cellpose' package is not available. Install it with "
                    "'pip install cellpose' (requires torch). Underlying import "
                    f"error: {_IMPORT_ERROR}"
                ),
            }

        image_path = arguments.get("image_path")
        if not image_path or not isinstance(image_path, str):
            return {
                "status": "error",
                "error": "Parameter 'image_path' is required and must be a string.",
            }
        if not os.path.exists(image_path):
            return {
                "status": "error",
                "error": f"Image file not found: '{image_path}'.",
            }

        model_type = arguments.get("model_type") or "cyto3"
        if model_type not in _LEGACY_MODEL_TYPES:
            return {
                "status": "error",
                "error": (
                    f"Unsupported model_type '{model_type}'. One of: "
                    + ", ".join(_LEGACY_MODEL_TYPES)
                ),
            }

        diameter = arguments.get("diameter")
        if diameter in (0, 0.0):
            diameter = None
        channels = arguments.get("channels") or [0, 0]
        save_mask = bool(arguments.get("save_mask", False))
        mask_output_path = arguments.get("mask_output_path")

        img, load_err = self._load_image(image_path)
        if load_err is not None:
            return {"status": "error", "error": load_err}

        try:
            model, model_used = self._get_model(model_type)
        except Exception as exc:
            return {
                "status": "error",
                "error": f"Failed to load cellpose model '{model_type}': {exc}",
            }

        try:
            # eval returns (masks, flows, styles, diams) in 3.x and
            # (masks, flows, styles) in 4.x — only the first element is needed.
            masks = model.eval(img, diameter=diameter, channels=channels)[0]
        except Exception as exc:
            return {
                "status": "error",
                "error": f"Cellpose segmentation failed: {exc}",
            }

        objects = self._object_stats(masks)

        data = {
            "image_path": image_path,
            "model_type_requested": model_type,
            "model_used": model_used,
            "num_objects": len(objects),
            "image_shape": [int(d) for d in masks.shape],
            "objects": objects,
            "mask_path": None,
        }
        if model_used and not any(
            mt in str(model_used).lower() for mt in _LEGACY_MODEL_TYPES
        ):
            data["note"] = (
                "This cellpose build uses a single unified model; the requested "
                "'model_type' was not applied. Segmentation was produced by "
                f"'{model_used}'."
            )

        if save_mask:
            mask_path, save_err = self._save_mask(masks, image_path, mask_output_path)
            if save_err is not None:
                # Segmentation succeeded; surface the save failure non-fatally.
                data["mask_save_error"] = save_err
            else:
                data["mask_path"] = mask_path

        return {"status": "success", "data": data}
