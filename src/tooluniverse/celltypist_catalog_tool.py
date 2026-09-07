# celltypist_tool.py
"""
CellTypist model catalog tool for ToolUniverse.

CellTypist provides pre-trained logistic-regression models for automated
cell type annotation of single-cell transcriptomes, spanning immune
compartments, developmental atlases, and individual tissues.

This tool exposes the model *catalog* — which models exist, what they were
trained on, how many cell types each resolves, and where to download the
serialized model. It does not run inference. To annotate cells, use the remote tool
`run_celltypist_annotate` (src/tooluniverse/remote/celltypist/), which runs a
chosen model against an expression matrix.

Note on overlap: PanglaoDB_* and CellMarker_* return literature-curated
marker genes for a named cell type. This tool answers a different question —
which trained classifier is appropriate for annotating a given tissue or
compartment.

API: https://celltypist.cog.sanger.ac.uk/models/models.json
No authentication required.
"""

import requests
from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool

CELLTYPIST_MODELS_URL = "https://celltypist.cog.sanger.ac.uk/models/models.json"


def _summarize_model(model: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a raw CellTypist model record."""
    n_celltypes = model.get("No_celltypes")
    try:
        n_celltypes = int(n_celltypes)
    except (TypeError, ValueError):
        pass

    default_flag = str(model.get("default", "")).lower() == "true"

    return {
        "filename": model.get("filename"),
        "description": model.get("details"),
        "n_celltypes": n_celltypes,
        "version": model.get("version"),
        "date": model.get("date"),
        "source_doi": model.get("source"),
        "download_url": model.get("url"),
        "is_default": default_flag,
    }


@register_tool("CellTypistCatalogTool")
class CellTypistCatalogTool(BaseTool):
    """
    Tool for browsing the CellTypist pre-trained model catalog.

    Supports listing all models, keyword search over model descriptions,
    and retrieving one model's metadata by filename.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        self.operation = tool_config.get("fields", {}).get("operation", "search_models")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the CellTypist catalog call."""
        try:
            if self.operation == "search_models":
                return self._search_models(arguments)
            elif self.operation == "get_model":
                return self._get_model(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"CellTypist catalog request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to the CellTypist catalog. Check network.",
            }
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            return {
                "status": "error",
                "error": f"CellTypist catalog returned HTTP {status}",
            }
        except ValueError:
            return {
                "status": "error",
                "error": "CellTypist catalog returned a non-JSON response",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Error querying CellTypist catalog: {str(e)}",
            }

    def _fetch_catalog(self) -> Dict[str, Any]:
        """Fetch the model catalog document."""
        response = requests.get(CELLTYPIST_MODELS_URL, timeout=self.timeout)
        response.raise_for_status()
        raw = response.json()
        return raw if isinstance(raw, dict) else {}

    def _models(self, raw: Dict[str, Any]) -> List[Dict[str, Any]]:
        models = raw.get("models")
        return models if isinstance(models, list) else []

    def _search_models(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List models, optionally filtered by keyword or cell type count."""
        raw = self._fetch_catalog()
        models = self._models(raw)
        total_available = len(models)

        keyword = arguments.get("keyword")
        if keyword:
            kw = keyword.lower()
            models = [
                m
                for m in models
                if kw in (m.get("details") or "").lower()
                or kw in (m.get("filename") or "").lower()
            ]

        min_celltypes = arguments.get("min_celltypes")
        if isinstance(min_celltypes, int):

            def _n(model: Dict[str, Any]) -> int:
                try:
                    return int(model.get("No_celltypes") or 0)
                except (TypeError, ValueError):
                    return 0

            models = [m for m in models if _n(m) >= min_celltypes]

        total_matching = len(models)
        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 25
        limit = min(limit, 100)

        results = [_summarize_model(m) for m in models[:limit]]

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "total_available": total_available,
                "total_matching": total_matching,
                "returned": len(results),
                "keyword": keyword,
                "catalog_last_update": raw.get("last_update"),
                "source": "CellTypist (Teichmann Lab, Wellcome Sanger Institute)",
            },
        }

    def _get_model(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve one model's metadata by filename."""
        filename = arguments.get("filename")
        if not filename:
            return {
                "status": "error",
                "error": "filename is required (e.g., 'Immune_All_Low.pkl'). "
                "Use CellTypist_search_models to find available model filenames.",
            }

        filename = filename.strip()
        raw = self._fetch_catalog()
        models = self._models(raw)
        match = next(
            (
                m
                for m in models
                if (m.get("filename") or "").lower() == filename.lower()
            ),
            None,
        )

        if match is None:
            available = [m.get("filename") for m in models[:10]]
            return {
                "status": "error",
                "error": f"No CellTypist model named '{filename}'. "
                f"Examples of valid filenames: {', '.join(str(a) for a in available)}.",
            }

        return {
            "status": "success",
            "data": _summarize_model(match),
            "metadata": {
                "catalog_last_update": raw.get("last_update"),
                "source": "CellTypist (Teichmann Lab, Wellcome Sanger Institute)",
            },
        }
