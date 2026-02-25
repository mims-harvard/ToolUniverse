"""
Cell Painting Tool

Provides access to the IDR (Image Data Resource) public API for querying
Cell Painting high-content microscopy datasets, including screens, plates,
and well-level metadata.

API: https://idr.openmicroscopy.org/api/v0/
No authentication required (public data).
"""

import requests
from typing import Dict, Any, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

IDR_BASE_URL = "https://idr.openmicroscopy.org/api/v0/m"

# Keywords used to identify Cell Painting / morphological profiling screens
_CELLPAINTING_KEYWORDS = ["paint", "jump", "phenotypic", "morphological"]


@register_tool("CellPaintingTool")
class CellPaintingTool(BaseTool):
    """
    Tool for querying Cell Painting datasets hosted on the Image Data Resource (IDR).

    Provides access to:
    - Available Cell Painting screens (studies)
    - Plates within a screen
    - Well-level metadata and image links for a plate
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Cell Painting IDR tool with given arguments."""
        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        operation_handlers = {
            "search_screens": self._search_screens,
            "get_screen_plates": self._get_screen_plates,
            "get_well_data": self._get_well_data,
        }

        handler = operation_handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}",
                "available_operations": list(operation_handlers.keys()),
            }

        try:
            return handler(arguments)
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "IDR API request timed out"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to IDR API"}
        except Exception as e:
            return {"status": "error", "error": f"Operation failed: {str(e)}"}

    def _make_request(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a GET request to the IDR API."""
        url = f"{IDR_BASE_URL}/{path}"
        response = requests.get(url, params=params or {}, timeout=30)
        if response.status_code == 200:
            return {"ok": True, "data": response.json()}
        else:
            return {
                "ok": False,
                "error": f"API request failed with status {response.status_code}",
                "detail": response.text[:500],
            }

    def _search_screens(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List available Cell Painting screens in IDR, optionally filtered by keyword."""
        query: Optional[str] = arguments.get("query")

        result = self._make_request("screens/", {"limit": 500})
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        screens_raw = result["data"].get("data", [])

        cp_screens = []
        for screen in screens_raw:
            name = screen.get("Name", "")
            description = screen.get("Description", "")
            combined = (name + " " + description).lower()
            if any(kw in combined for kw in _CELLPAINTING_KEYWORDS):
                cp_screens.append(screen)

        if query:
            q_lower = query.lower()
            cp_screens = [
                s
                for s in cp_screens
                if q_lower
                in (s.get("Name", "") + " " + s.get("Description", "")).lower()
            ]

        output = [
            {
                "screen_id": screen.get("@id"),
                "name": screen.get("Name", ""),
                "description": screen.get("Description", ""),
                "url": screen.get("url:screen", ""),
            }
            for screen in cp_screens
        ]

        return {
            "status": "success",
            "data": output,
            "num_results": len(output),
        }

    def _get_screen_plates(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get plates belonging to a given screen."""
        screen_id = arguments.get("screen_id")
        if screen_id is None:
            return {"status": "error", "error": "Missing required parameter: screen_id"}

        result = self._make_request(f"screens/{screen_id}/plates/", {"limit": 1000})
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        plates_raw = result["data"].get("data", [])
        plates = [
            {"plate_id": p.get("@id"), "name": p.get("Name", "")} for p in plates_raw
        ]

        return {
            "status": "success",
            "data": {
                "screen_id": screen_id,
                "plates": plates,
                "n_plates": len(plates),
            },
        }

    def _get_well_data(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get well-level metadata and image links for a plate."""
        plate_id = arguments.get("plate_id")
        if plate_id is None:
            return {"status": "error", "error": "Missing required parameter: plate_id"}

        limit = arguments.get("limit", 20)

        result = self._make_request(f"plates/{plate_id}/wells/", {"limit": limit})
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        wells_raw = result["data"].get("data", [])
        output = []
        for well in wells_raw:
            well_samples = well.get("WellSamples", [])
            image_url = None
            if well_samples:
                image_url = well_samples[0].get("Image", {}).get("url:image")

            output.append(
                {
                    "well_id": well.get("@id"),
                    "column": well.get("Column"),
                    "row": well.get("Row"),
                    "url": well.get("url:well", ""),
                    "image_url": image_url,
                }
            )

        return {
            "status": "success",
            "data": output,
            "num_results": len(output),
        }
