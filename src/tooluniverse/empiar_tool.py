"""
EMPIAR (Electron Microscopy Public Image Archive) Tool

Provides access to EMPIAR for searching and retrieving electron microscopy
image datasets. Uses EBI Search API for keyword search and EMPIAR REST API
for detailed entry retrieval.
"""

import requests
from typing import Any, Dict
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("EMPIARTool")
class EMPIARTool(BaseTool):
    """Tool for accessing the EMPIAR database of raw electron microscopy images."""

    EMPIAR_API_BASE = "https://www.ebi.ac.uk/empiar/api"
    EBI_SEARCH_BASE = "https://www.ebi.ac.uk/ebisearch/ws/rest/empiar"

    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/json", "User-Agent": "ToolUniverse/1.0"}
        )
        self.timeout = 30

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = self.tool_config.get("name", "")
        try:
            if tool_name == "EMPIAR_search_entries":
                return self._search_entries(arguments)
            elif tool_name == "EMPIAR_get_entry":
                return self._get_entry(arguments)
            else:
                return {"status": "error", "error": f"Unknown tool: {tool_name}"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"EMPIAR API error: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _search_entries(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Search EMPIAR entries via EBI Search API."""
        query = args.get("query", "")
        page_size = args.get("page_size", 10)
        start = args.get("start", 0)

        params = {
            "query": query,
            "size": page_size,
            "start": start,
            "format": "json",
            "fields": "title,release_date",
        }

        resp = self.session.get(
            self.EBI_SEARCH_BASE, params=params, timeout=self.timeout
        )
        resp.raise_for_status()
        data = resp.json()

        entries = []
        for entry in data.get("entries", []):
            fields = entry.get("fields", {})
            entries.append(
                {
                    "empiar_id": entry.get("id", ""),
                    "title": (fields.get("title") or [""])[0],
                    "release_date": (fields.get("release_date") or [""])[0],
                }
            )

        return {
            "status": "success",
            "data": entries,
            "metadata": {
                "total_hits": data.get("hitCount", 0),
                "returned": len(entries),
                "start": start,
            },
        }

    def _get_entry(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed EMPIAR entry by ID."""
        empiar_id = args.get("empiar_id", "")

        # Normalize ID: accept both "EMPIAR-10028" and "10028"
        if not empiar_id.upper().startswith("EMPIAR-"):
            empiar_id = f"EMPIAR-{empiar_id}"
        empiar_id = empiar_id.upper()

        url = f"{self.EMPIAR_API_BASE}/entry/{empiar_id}/"
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        raw = resp.json()

        # Response is keyed by EMPIAR ID
        entry_data = raw.get(empiar_id, {})
        if not entry_data:
            # Try original casing from response
            for key in raw:
                entry_data = raw[key]
                break

        # Extract key fields
        result = {
            "empiar_id": empiar_id,
            "title": entry_data.get("title", ""),
            "status": entry_data.get("status", ""),
            "deposition_date": entry_data.get("deposition_date"),
            "release_date": entry_data.get("release_date"),
            "update_date": entry_data.get("update_date"),
            "dataset_size": entry_data.get("dataset_size", ""),
            "experiment_type": entry_data.get("experiment_type", ""),
            "scale": entry_data.get("scale", ""),
            "entry_doi": entry_data.get("entry_doi", ""),
            "cross_references": entry_data.get("cross_references", []),
            "related_pdb_entries": entry_data.get("related_pdb_entries", []),
            "imagesets": [
                {
                    "name": img.get("name", ""),
                    "category": img.get("category", ""),
                    "data_format": img.get("data_format", ""),
                    "num_images_or_tilt_series": img.get("num_images_or_tilt_series"),
                    "pixel_width": img.get("pixel_width"),
                    "pixel_height": img.get("pixel_height"),
                    "image_width": img.get("image_width"),
                    "image_height": img.get("image_height"),
                    "details": img.get("details", ""),
                }
                for img in entry_data.get("imagesets", [])
            ],
            "citation": [
                {
                    "title": cit.get("title", ""),
                    "journal": cit.get("journal", ""),
                    "year": cit.get("year", ""),
                    "doi": cit.get("doi"),
                    "pubmedid": cit.get("pubmedid"),
                }
                for cit in entry_data.get("citation", [])
            ],
            "principal_investigator": [
                {
                    "first_name": pi.get("first_name", ""),
                    "last_name": pi.get("last_name", ""),
                    "organization": pi.get("organization", ""),
                }
                for pi in entry_data.get("principal_investigator", [])
            ],
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {"url": url},
        }
