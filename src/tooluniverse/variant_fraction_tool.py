"""Coding variant fraction tool.

Wraps the skill script at
``skills/tooluniverse-variant-analysis/scripts/variant_fraction.py``.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any, Dict

from .base_tool import BaseTool
from .tool_registry import register_tool


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = (
    _REPO_ROOT
    / "skills"
    / "tooluniverse-variant-analysis"
    / "scripts"
    / "variant_fraction.py"
)


def _load_script_module():
    if not _SCRIPT_PATH.exists():
        return None
    spec = importlib.util.spec_from_file_location(
        "_variant_fraction_script", str(_SCRIPT_PATH)
    )
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    saved_argv = sys.argv
    sys.argv = [str(_SCRIPT_PATH)]
    try:
        spec.loader.exec_module(module)
    finally:
        sys.argv = saved_argv
    return module


@register_tool("CodingVariantFractionTool")
class CodingVariantFractionTool(BaseTool):
    """Compute fraction of coding variants matching a given SO annotation below a VAF threshold.

    CODING allowlist (denominator): synonymous_variant, missense_variant,
    splice_region_variant, stop_gained, stop_lost, start_lost,
    frameshift_variant, inframe_insertion, inframe_deletion. Intronic,
    UTR, intergenic, and up/downstream records are excluded.
    """

    def __init__(self, tool_config: Dict[str, Any], **kwargs):
        super().__init__(tool_config)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        file_path = arguments.get("file", "")
        vaf_threshold = float(arguments.get("vaf_threshold", 0.3))
        annotation = arguments.get("annotation", "synonymous_variant")
        header_rows = int(arguments.get("header_rows", 1))
        vaf_col = arguments.get("vaf_col", "") or ""
        so_col = arguments.get("so_col", "") or ""

        if not file_path or not os.path.exists(file_path):
            return {"status": "error", "error": f"File not found: {file_path}"}
        if header_rows not in (1, 2):
            return {
                "status": "error",
                "error": f"header_rows must be 1 or 2, got {header_rows}",
            }

        module = _load_script_module()
        if module is None:
            return {
                "status": "error",
                "error": f"Skill script not available at {_SCRIPT_PATH}",
            }

        try:
            result = module.compute_variant_fraction(
                file_path=file_path,
                vaf_threshold=vaf_threshold,
                annotation=annotation,
                header_rows=header_rows,
                vaf_col=vaf_col,
                so_col=so_col,
            )
        except ValueError as exc:
            return {"status": "error", "error": str(exc)}
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "error": f"Variant fraction failed: {exc}"}

        return {"status": "success", "data": result}
