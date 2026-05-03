# nextstrain_tool.py
"""
Nextstrain REST API tool for ToolUniverse.

Nextstrain is an open-source project to harness the scientific and
public health potential of pathogen genome data. It provides real-time
tracking of evolving pathogens through phylogenetic analysis.

API: https://nextstrain.org/charon
No authentication required. Free for all use.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

NEXTSTRAIN_BASE_URL = "https://nextstrain.org/charon"


@register_tool("NextstrainTool")
class NextstrainTool(BaseTool):
    """
    Tool for querying Nextstrain, the pathogen evolution tracker.

    Provides access to phylogenetic datasets for various pathogens
    including influenza, SARS-CoV-2, Zika, Ebola, Dengue, and more.
    Returns metadata and phylogenetic tree data.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 45)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "list_datasets"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Nextstrain API call."""
        try:
            return self._dispatch(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Nextstrain API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to Nextstrain API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"Nextstrain API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying Nextstrain: {str(e)}",
            }

    def _dispatch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint based on config."""
        if self.endpoint_type == "list_datasets":
            return self._list_datasets(arguments)
        elif self.endpoint_type == "get_dataset":
            return self._get_dataset(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown endpoint_type: {self.endpoint_type}",
            }

    def _list_datasets(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List available Nextstrain pathogen datasets."""
        pathogen_filter = arguments.get("pathogen", "").lower()

        url = f"{NEXTSTRAIN_BASE_URL}/getAvailable"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        raw = response.json()

        all_datasets = raw.get("datasets", [])

        # Group by pathogen (first segment of the request path)
        pathogen_groups = {}
        for ds in all_datasets:
            request_path = ds.get("request", "")
            if not request_path:
                continue
            pathogen = request_path.split("/")[0]
            pathogen_groups.setdefault(pathogen, []).append(request_path)

        # Filter by pathogen if specified
        if pathogen_filter:
            filtered = {}
            for p, paths in pathogen_groups.items():
                if pathogen_filter in p.lower():
                    filtered[p] = paths
            pathogen_groups = filtered

        # Build response
        results = []
        for pathogen, paths in sorted(pathogen_groups.items()):
            results.append(
                {
                    "pathogen": pathogen,
                    "dataset_count": len(paths),
                    "datasets": sorted(paths)[:10],
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "Nextstrain",
                "total_pathogens": len(results),
                "total_datasets": sum(len(r["datasets"]) for r in results),
                "filter": pathogen_filter or "(none)",
                "endpoint": "list_datasets",
            },
        }

    def _get_dataset(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get metadata and tree summary for a Nextstrain dataset."""
        dataset = arguments.get("dataset", "")
        if not dataset:
            return {
                "status": "error",
                "error": "dataset parameter is required (e.g., 'zika', 'ebola', 'flu/seasonal/h3n2/ha/2y')",
            }

        url = f"{NEXTSTRAIN_BASE_URL}/getDataset"
        params = {"prefix": dataset}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        raw = response.json()

        meta = raw.get("meta", {})
        tree = raw.get("tree", {})

        # Count sequences (leaves in tree)
        def count_leaves(node):
            if not isinstance(node, dict):
                return 0
            children = node.get("children", [])
            if not children:
                return 1
            return sum(count_leaves(c) for c in children)

        num_sequences = count_leaves(tree)

        # Extract tree root attributes
        root_attrs = tree.get("node_attrs", {})
        root_info = {}
        for key, val in root_attrs.items():
            if isinstance(val, dict) and "value" in val:
                root_info[key] = val["value"]
            elif not isinstance(val, dict):
                root_info[key] = val

        # Data provenance
        provenance = meta.get("data_provenance", [])
        prov_names = []
        for p in provenance:
            if isinstance(p, dict):
                prov_names.append(p.get("name", ""))

        # Maintainers
        maintainers = []
        for m in meta.get("maintainers", []):
            if isinstance(m, dict):
                maintainers.append(m.get("name", ""))

        result = {
            "dataset": dataset,
            "title": meta.get("title", ""),
            "updated": meta.get("updated", ""),
            "build_url": meta.get("build_url", ""),
            "num_sequences": num_sequences,
            "data_provenance": prov_names,
            "maintainers": maintainers,
            "root_attributes": root_info,
        }

        # Color-by options
        colorings = meta.get("colorings", [])
        if colorings:
            result["available_colorings"] = [
                c.get("key", "") for c in colorings if isinstance(c, dict)
            ][:15]

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "Nextstrain",
                "query": dataset,
                "version": raw.get("version", ""),
                "endpoint": "get_dataset",
            },
        }
