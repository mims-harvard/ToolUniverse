"""Read a Jupyter notebook the user has handed over for review.

Legitimate use: the user names a notebook (their own analysis, a colleague's,
a published method's) and asks the agent to explain it, review it, debug it,
or port it. The tool returns the cells' source and printed outputs as
structured data, and flags cells that drop samples or filter rows, since those
are the steps a reviewer most needs to check.

Not a source of answers. A pre-run notebook that happens to sit next to the
data of an analysis the agent was asked to perform is not something to read
the result from: the agent computes that result from the raw data itself. For
that reason the tool takes only an explicit ``notebook_path`` and never goes
looking for notebooks in a data folder.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List

from .base_tool import BaseTool
from .tool_registry import register_tool


def _cell_text(cell: dict) -> str:
    src = cell.get("source", "")
    if isinstance(src, list):
        src = "".join(src)
    return src


# Phrases that signal a sample/row exclusion or filtering step. These are the
# steps that most change a notebook's results and are easiest to miss when
# reading it, so a review surfaces them separately.
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
    """Read a Jupyter notebook the user asked to have reviewed.

    Use it to explain, review, debug or port a notebook the user names. Do
    not use it to read the answer to an analysis you were asked to perform:
    compute that from the raw data.
    """

    def __init__(self, tool_config: Dict[str, Any], **kwargs):
        super().__init__(tool_config)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        notebook = arguments.get("notebook_path")
        search = arguments.get("search", "")
        max_chars = int(arguments.get("max_output_chars", 400))
        include_source = bool(arguments.get("include_source", True))
        regex = bool(arguments.get("regex", False))

        if not notebook:
            return {
                "status": "error",
                "error": "provide notebook_path: the notebook the user asked you to review",
            }
        nb_path = Path(notebook)
        if not nb_path.exists():
            return {
                "status": "error",
                "error": f"notebook_path does not exist: {notebook}",
            }

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
                "These cells drop samples or filter rows. When reviewing the "
                "notebook, check that each exclusion is justified and documented."
            )
        if search:
            data["search"] = search
            data["matching_cells"] = matching
            data["n_matches"] = len(matching)
        return {"status": "success", "data": data}
