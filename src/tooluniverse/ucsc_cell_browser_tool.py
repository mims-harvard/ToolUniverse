# ucsc_cell_browser_tool.py
"""
UCSC Cell Browser REST/JSON tool for ToolUniverse.

The UCSC Cell Browser hosts 300+ curated, consistently annotated single-cell
datasets, each tagged with organism, body part, and disease. It complements
CELLxGENE Discover (CxGDisc_* tools), the EBI Single Cell Expression Atlas
(SCXA_* tools), and the Broad Single Cell Portal (SCP_* tools), which index
largely different dataset sets.

API: https://cells.ucsc.edu/dataset.json (catalog)
     https://cells.ucsc.edu/{name}/dataset.json (per-dataset detail)
No authentication required.
"""

import requests
from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool

UCSC_CB_BASE_URL = "https://cells.ucsc.edu"


def _summarize_dataset(dataset: Dict[str, Any]) -> Dict[str, Any]:
    """Trim a raw Cell Browser catalog entry to the useful fields."""
    name = dataset.get("name")
    return {
        "name": name,
        "label": dataset.get("shortLabel"),
        "organisms": dataset.get("organisms") or [],
        "body_parts": dataset.get("body_parts") or [],
        "diseases": dataset.get("diseases") or [],
        "is_collection": bool(dataset.get("isCollection")),
        "dataset_count": dataset.get("datasetCount"),
        "browser_url": f"{UCSC_CB_BASE_URL}/?ds={name}" if name else None,
    }


def _matches(dataset: Dict[str, Any], field: str, value: str) -> bool:
    """Case-insensitive substring match against a list-valued catalog field."""
    needle = value.lower()
    return any(needle in str(item).lower() for item in (dataset.get(field) or []))


def _normalize_parents(parents: Any) -> List[Dict[str, Any]]:
    """Normalize the raw `parents` field into {name, label} objects.

    The Cell Browser returns parents as [name, label] pairs, e.g.
    [["", "All Datasets"]], where an empty name denotes the catalog root.
    """
    normalized = []
    for parent in parents or []:
        if isinstance(parent, (list, tuple)):
            name = parent[0] if len(parent) > 0 else None
            label = parent[1] if len(parent) > 1 else None
        else:
            name, label = parent, None
        normalized.append({"name": name or None, "label": label})
    return normalized


@register_tool("UCSCCellBrowserTool")
class UCSCCellBrowserTool(BaseTool):
    """
    Tool for querying the UCSC Cell Browser dataset catalog.

    Supports listing and filtering datasets by organism, body part, and
    disease, and retrieving detail for a single dataset (including the
    child datasets of a collection).

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "search_datasets"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the UCSC Cell Browser call."""
        try:
            if self.operation == "search_datasets":
                return self._search_datasets(arguments)
            elif self.operation == "get_dataset":
                return self._get_dataset(arguments)
            elif self.operation == "list_facets":
                return self._list_facets(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"UCSC Cell Browser request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to UCSC Cell Browser. Check network.",
            }
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            return {
                "status": "error",
                "error": f"UCSC Cell Browser returned HTTP {status}",
            }
        except ValueError:
            return {
                "status": "error",
                "error": "UCSC Cell Browser returned a non-JSON response",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Error querying UCSC Cell Browser: {str(e)}",
            }

    def _fetch_catalog(self) -> List[Dict[str, Any]]:
        """Fetch the top-level dataset catalog."""
        url = f"{UCSC_CB_BASE_URL}/dataset.json"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        raw = response.json()
        datasets = raw.get("datasets")
        return datasets if isinstance(datasets, list) else []

    def _search_datasets(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Filter the catalog by organism, body part, disease, or keyword."""
        datasets = self._fetch_catalog()
        total_available = len(datasets)

        organism = arguments.get("organism")
        if organism:
            datasets = [d for d in datasets if _matches(d, "organisms", organism)]

        body_part = arguments.get("body_part")
        if body_part:
            datasets = [d for d in datasets if _matches(d, "body_parts", body_part)]

        disease = arguments.get("disease")
        if disease:
            datasets = [d for d in datasets if _matches(d, "diseases", disease)]

        keyword = arguments.get("keyword")
        if keyword:
            kw = keyword.lower()
            datasets = [
                d
                for d in datasets
                if kw in (d.get("shortLabel") or "").lower()
                or kw in (d.get("name") or "").lower()
            ]

        total_matching = len(datasets)
        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 25
        limit = min(limit, 100)

        results = [_summarize_dataset(d) for d in datasets[:limit]]

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "total_available": total_available,
                "total_matching": total_matching,
                "returned": len(results),
                "filters": {
                    "organism": organism,
                    "body_part": body_part,
                    "disease": disease,
                    "keyword": keyword,
                },
                "source": "UCSC Cell Browser",
            },
        }

    def _get_dataset(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch detail for one dataset, including collection children."""
        name = arguments.get("name")
        if not name:
            return {
                "status": "error",
                "error": "name is required (e.g., 'organoid-22q11'). "
                "Use UCSCCellBrowser_search_datasets to find dataset names.",
            }

        url = f"{UCSC_CB_BASE_URL}/{name.strip()}/dataset.json"
        response = requests.get(url, timeout=self.timeout)
        if response.status_code == 404:
            return {
                "status": "error",
                "error": f"No UCSC Cell Browser dataset named '{name}'. "
                "Use UCSCCellBrowser_search_datasets to find valid names.",
            }
        response.raise_for_status()
        raw = response.json()

        children = [_summarize_dataset(d) for d in (raw.get("datasets") or [])]

        return {
            "status": "success",
            "data": {
                "name": raw.get("name"),
                "label": raw.get("shortLabel"),
                "abstract": raw.get("abstract"),
                "organisms": raw.get("organisms") or [],
                "body_parts": raw.get("body_parts") or [],
                "diseases": raw.get("diseases") or [],
                "parents": _normalize_parents(raw.get("parents")),
                "child_datasets": children,
                "browser_url": f"{UCSC_CB_BASE_URL}/?ds={raw.get('name')}",
            },
            "metadata": {
                "child_dataset_count": len(children),
                "source": "UCSC Cell Browser",
            },
        }

    def _list_facets(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List the distinct organism / body part / disease values available.

        Useful for discovering valid filter values before calling
        UCSCCellBrowser_search_datasets.
        """
        datasets = self._fetch_catalog()

        facet = arguments.get("facet", "body_parts")
        field_map = {
            "organisms": "organisms",
            "body_parts": "body_parts",
            "diseases": "diseases",
        }
        field = field_map.get(facet)
        if field is None:
            return {
                "status": "error",
                "error": f"Unknown facet '{facet}'. "
                f"Valid values: {', '.join(sorted(field_map))}.",
            }

        counts: Dict[str, int] = {}
        for dataset in datasets:
            for value in dataset.get(field) or []:
                key = str(value)
                counts[key] = counts.get(key, 0) + 1

        ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))

        return {
            "status": "success",
            "data": [{"value": v, "dataset_count": c} for v, c in ordered],
            "metadata": {
                "facet": facet,
                "distinct_values": len(ordered),
                "datasets_scanned": len(datasets),
                "source": "UCSC Cell Browser",
            },
        }
