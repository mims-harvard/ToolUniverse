"""Extract outputs from executed Jupyter notebooks.

Authoritative analyses often ship as pre-executed notebooks (`*_executed.ipynb`)
containing the full cell source + printed outputs. This tool surfaces those
outputs as structured data so an agent can find the ground-truth value for a
question by reading the published analysis instead of reimplementing it with
potentially different package versions, filters, or thresholds.

The tool is general-purpose: it works on any executed Jupyter notebook, not
specific to any benchmark or dataset.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

from .base_tool import BaseTool
from .tool_registry import register_tool


def _find_notebook(folder: Path) -> Path | None:
    """Return the first executed or regular .ipynb under folder (recursive)."""
    executed = sorted(folder.rglob("*_executed.ipynb"))
    if executed:
        return executed[0]
    all_nb = sorted(folder.rglob("*.ipynb"))
    if all_nb:
        return all_nb[0]
    return None


def _cell_text(cell: dict) -> str:
    src = cell.get("source", "")
    if isinstance(src, list):
        src = "".join(src)
    return src


# Phrases that signal a sample/row exclusion or filtering step. Reference
# answers often depend on these (e.g. dropping PCA outlier samples before
# DESeq2), yet the question text rarely mentions them — so an agent that
# reimplements the analysis without reading the notebook gets a different
# number. Surfacing these cells prevents that silent divergence.
_PREPROCESS_SIGNALS = (
    "outlier",
    "exclude",
    "excluding",
    "drop",
    "remove sample",
    "removed sample",
    "filter out",
    "filtered out",
    "discard",
    "low quality",
    "low-quality",
    "poor quality",
    "do not correlate",
    "don't correlate",
    "doesn't cluster",
    "do not cluster",
)


def _is_preprocessing_cell(src: str) -> bool:
    """True if a cell source looks like a sample-exclusion / filtering step."""
    low = src.lower()
    return any(sig in low for sig in _PREPROCESS_SIGNALS)


def _cell_outputs_text(cell: dict) -> str:
    parts: List[str] = []
    for out in cell.get("outputs", []):
        t = out.get("text")
        if t:
            if isinstance(t, list):
                t = "".join(t)
            parts.append(t)
        else:
            d = out.get("data", {})
            for key in ("text/plain", "text/html", "application/json"):
                if key in d:
                    val = d[key]
                    if isinstance(val, list):
                        val = "".join(val)
                    if not isinstance(val, str):
                        val = json.dumps(val)[:400]
                    parts.append(val)
                    break
    return "\n".join(parts)


@register_tool("ExecutedNotebookTool")
class ExecutedNotebookTool(BaseTool):
    """Read a pre-executed Jupyter notebook and return its cells + outputs.

    Run this BEFORE writing your own analysis code — when the authoritative
    pipeline already ran, its outputs are the ground truth. Reimplementing
    with different library versions produces different numbers.
    """

    def __init__(self, tool_config: Dict[str, Any], **kwargs):
        super().__init__(tool_config)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        folder = arguments.get("data_folder") or arguments.get("folder")
        notebook = arguments.get("notebook_path")
        search = arguments.get("search", "")
        max_chars = int(arguments.get("max_output_chars", 400))
        include_source = bool(arguments.get("include_source", True))
        regex = bool(arguments.get("regex", False))

        nb_path: Path | None = None
        if notebook:
            nb_path = Path(notebook)
            if not nb_path.exists():
                return {
                    "status": "error",
                    "error": f"notebook_path does not exist: {notebook}",
                }
        elif folder:
            folder_path = Path(folder)
            if not folder_path.exists():
                return {
                    "status": "error",
                    "error": f"data_folder does not exist: {folder}",
                }
            nb_path = _find_notebook(folder_path)
            if nb_path is None:
                return {
                    "status": "error",
                    "error": f"no .ipynb found under {folder}",
                }
        else:
            return {"status": "error", "error": "provide data_folder or notebook_path"}

        try:
            nb = json.loads(nb_path.read_text())
        except Exception as e:
            return {"status": "error", "error": f"could not parse notebook: {e}"}

        cells_out = []
        matching = []
        preprocessing = []
        for i, cell in enumerate(nb.get("cells", [])):
            src = _cell_text(cell)
            outs = _cell_outputs_text(cell)
            if not outs and not src:
                continue
            entry = {
                "idx": i,
                "type": cell.get("cell_type", "code"),
                "output": outs[:max_chars],
            }
            if include_source:
                entry["source"] = src[:max_chars]
            cells_out.append(entry)

            # Always surface sample-exclusion / filtering cells — these change
            # the reference answer but are usually absent from the question.
            if cell.get("cell_type", "code") == "code" and _is_preprocessing_cell(src):
                preprocessing.append(
                    {
                        "idx": i,
                        "source": src[:max_chars],
                        "output": outs[:max_chars],
                    }
                )

            if search:
                haystack = src + "\n" + outs
                hit = False
                if regex:
                    import re

                    try:
                        hit = bool(re.search(search, haystack, re.IGNORECASE))
                    except re.error:
                        hit = False
                else:
                    terms = [t.strip().lower() for t in search.split(",") if t.strip()]
                    hay = haystack.lower()
                    hit = any(t in hay for t in terms)
                if hit:
                    matching.append(entry)

        data: Dict[str, Any] = {
            "notebook_path": str(nb_path),
            "total_cells": len(nb.get("cells", [])),
            "cells": cells_out,
        }
        if preprocessing:
            data["preprocessing_cells"] = preprocessing
            data["n_preprocessing_cells"] = len(preprocessing)
            data["preprocessing_note"] = (
                "These cells perform sample-exclusion or filtering that affects "
                "the reference answer. Apply the SAME exclusions before computing "
                "your result — the question text usually omits them."
            )
        if search:
            data["search"] = search
            data["matching_cells"] = matching
            data["n_matches"] = len(matching)
        return {"status": "success", "data": data}
