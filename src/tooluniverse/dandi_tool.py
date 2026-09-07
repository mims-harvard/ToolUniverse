# dandi_tool.py
"""
DANDI Archive tool for ToolUniverse.

DANDI (Distributed Archives for Neurophysiology Data Integration) holds
neurophysiology datasets in the Neurodata Without Borders (NWB) standard:
electrophysiology, optical physiology, and behavior recordings, mostly from
the Allen Institute and BRAIN Initiative-funded labs.

ToolUniverse already reaches OpenNeuro (human MRI/EEG); DANDI is the
neurophysiology-recording counterpart with no overlap in data type.

API: https://api.dandiarchive.org/api
No authentication required for public dandisets.
"""

from typing import Dict, Any

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

DANDI_BASE_URL = "https://api.dandiarchive.org/api"


@register_tool("DANDITool")
class DANDITool(BaseTool):
    """
    Tool for querying the DANDI neurophysiology data archive.

    Supports searching dandisets by keyword, fetching one dandiset's full
    metadata (species, data standard, subject and file counts), and listing
    its data files.

    No authentication required for public dandisets.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 45)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "search_datasets"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the DANDI lookup."""
        try:
            if self.operation == "search_datasets":
                return self._search_datasets(arguments)
            if self.operation == "get_dataset":
                return self._get_dataset(arguments)
            if self.operation == "list_assets":
                return self._list_assets(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"DANDI request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to DANDI. Check network.",
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {"status": "error", "error": f"DANDI returned HTTP {code}"}
        except ValueError:
            return {"status": "error", "error": "DANDI returned a non-JSON response"}
        except Exception as e:
            return {"status": "error", "error": f"Error querying DANDI: {str(e)}"}

    def _search_datasets(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search dandisets by keyword."""
        query = (arguments.get("query") or "").strip()
        if not query:
            return {
                "status": "error",
                "error": "query is required, e.g. 'mouse visual cortex' or "
                "'patch-seq'.",
            }

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 25
        limit = min(limit, 100)

        response = requests.get(
            f"{DANDI_BASE_URL}/dandisets/",
            params={"search": query, "page_size": limit},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results") or []

        rows = []
        for item in results:
            version = item.get("most_recent_published_version") or item.get(
                "draft_version"
            ) or {}
            rows.append(
                {
                    "dandiset_id": item.get("identifier"),
                    "name": version.get("name"),
                    "asset_count": version.get("asset_count"),
                    "size_bytes": version.get("size"),
                    "status": version.get("status"),
                    "contact_person": item.get("contact_person"),
                    "star_count": item.get("star_count"),
                }
            )

        if not rows:
            return {
                "status": "error",
                "error": f"No DANDI dandisets matching '{query}'.",
            }

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "query": query,
                "total_matching": payload.get("count"),
                "returned": len(rows),
                "note": "dandiset_id is what get_dataset and list_assets "
                "expect, e.g. '000020'.",
                "source": "DANDI Archive",
            },
        }

    def _get_dataset(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch one dandiset's full metadata."""
        dandiset_id = (arguments.get("dandiset_id") or "").strip()
        if not dandiset_id:
            return {
                "status": "error",
                "error": "dandiset_id is required, e.g. '000020'. Use "
                "DANDI_search_datasets to find one.",
            }

        response = requests.get(
            f"{DANDI_BASE_URL}/dandisets/{dandiset_id}/versions/draft/",
            timeout=self.timeout,
        )
        if response.status_code == 404:
            return {
                "status": "error",
                "error": f"No DANDI dandiset with id '{dandiset_id}'.",
            }
        response.raise_for_status()
        payload = response.json()
        assets_summary = payload.get("assetsSummary") or {}

        return {
            "status": "success",
            "data": {
                "dandiset_id": dandiset_id,
                "name": payload.get("name"),
                "description": payload.get("description"),
                "license": payload.get("license") or [],
                "keywords": payload.get("keywords") or [],
                "species": [
                    s.get("name") for s in assets_summary.get("species") or []
                ],
                "data_standard": [
                    s.get("name") for s in assets_summary.get("dataStandard") or []
                ],
                "number_of_subjects": assets_summary.get("numberOfSubjects"),
                "number_of_files": assets_summary.get("numberOfFiles"),
                "size_bytes": assets_summary.get("numberOfBytes"),
                "date_created": payload.get("dateCreated"),
                "citation": payload.get("citation"),
            },
            "metadata": {
                "dandiset_id": dandiset_id,
                "note": "Reflects the draft version's metadata; use "
                "list_assets with the same dandiset_id for individual files.",
                "source": "DANDI Archive",
            },
        }

    def _list_assets(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List one dandiset's data files."""
        dandiset_id = (arguments.get("dandiset_id") or "").strip()
        if not dandiset_id:
            return {
                "status": "error",
                "error": "dandiset_id is required, e.g. '000020'. Use "
                "DANDI_search_datasets to find one.",
            }

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 50
        limit = min(limit, 200)

        response = requests.get(
            f"{DANDI_BASE_URL}/dandisets/{dandiset_id}/versions/draft/assets/",
            params={"page_size": limit},
            timeout=self.timeout,
        )
        if response.status_code == 404:
            return {
                "status": "error",
                "error": f"No DANDI dandiset with id '{dandiset_id}'.",
            }
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results") or []

        rows = [
            {
                "path": a.get("path"),
                "size_bytes": a.get("size"),
                "asset_id": a.get("asset_id"),
                "created": a.get("created"),
            }
            for a in results
        ]

        if not rows:
            return {
                "status": "error",
                "error": f"No assets found for DANDI dandiset '{dandiset_id}'.",
            }

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "dandiset_id": dandiset_id,
                "total_assets": payload.get("count"),
                "returned": len(rows),
                "source": "DANDI Archive",
            },
        }
