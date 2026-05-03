# neuromorpho_tool.py
"""
NeuroMorpho.Org REST API tool for ToolUniverse.

NeuroMorpho.Org is the largest collection of publicly accessible 3D neuronal
reconstructions, containing over 270,000 digitally reconstructed neurons from
hundreds of species, brain regions, and cell types.

API Documentation: https://neuromorpho.org/apiReference.html
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

NEUROMORPHO_BASE_URL = "https://neuromorpho.org/api"


@register_tool("NeuroMorphoTool")
class NeuroMorphoTool(BaseTool):
    """
    Tool for querying NeuroMorpho.Org neuron morphology database.

    Provides access to:
    - Neuron metadata (species, brain region, cell type, etc.)
    - Morphometric measurements (surface area, volume, branch count)
    - Associated literature
    - Search/filtering by multiple neuron attributes

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "neuron"
        )
        self.query_mode = tool_config.get("fields", {}).get("query_mode", "id")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the NeuroMorpho API call."""
        try:
            endpoint = self.endpoint_type
            mode = self.query_mode

            if endpoint == "neuron" and mode == "id":
                return self._get_neuron_by_id(arguments)
            elif endpoint == "neuron" and mode == "search":
                return self._search_neurons(arguments)
            elif endpoint == "morphometry":
                return self._get_morphometry(arguments)
            elif endpoint == "neuron" and mode == "fields":
                return self._get_field_values(arguments)
            else:
                return {
                    "status": "error",
                    "error": f"Unknown endpoint/mode: {endpoint}/{mode}",
                }

        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"NeuroMorpho API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to NeuroMorpho API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else "unknown"
            return {"status": "error", "error": f"NeuroMorpho API HTTP error: {status}"}
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying NeuroMorpho: {str(e)}",
            }

    def _get_neuron_by_id(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get a neuron by its numeric ID or name."""
        neuron_id = arguments.get("neuron_id")
        neuron_name = arguments.get("neuron_name")

        if neuron_id is not None:
            url = f"{NEUROMORPHO_BASE_URL}/neuron/id/{neuron_id}"
        elif neuron_name:
            url = f"{NEUROMORPHO_BASE_URL}/neuron/name/{neuron_name}"
        else:
            return {
                "status": "error",
                "error": "Either neuron_id or neuron_name is required",
            }

        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        return {
            "status": "success",
            "data": data,
            "metadata": {"total_results": 1},
        }

    def _search_neurons(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search neurons by field criteria."""
        query_field = arguments.get("query_field", "species")
        query_value = arguments.get("query_value", "")
        filter_field = arguments.get("filter_field")
        filter_value = arguments.get("filter_value")
        page = arguments.get("page", 0)
        size = arguments.get("size", 20)

        if not query_value:
            return {"status": "error", "error": "query_value parameter is required"}

        # Clamp size to API max
        size = min(size, 500)

        url = f"{NEUROMORPHO_BASE_URL}/neuron/select"
        params = {
            "q": f"{query_field}:{query_value}",
            "page": page,
            "size": size,
        }

        # Add filter query if specified
        if filter_field and filter_value:
            params["fq"] = f"{filter_field}:{filter_value}"

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        neurons = data.get("_embedded", {}).get("neuronResources", [])
        page_info = data.get("page", {})

        return {
            "status": "success",
            "data": neurons,
            "metadata": {
                "total_results": page_info.get("totalElements", len(neurons)),
                "total_pages": page_info.get("totalPages", 1),
                "current_page": page_info.get("number", page),
                "page_size": page_info.get("size", size),
            },
        }

    def _get_morphometry(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get morphometric measurements for a neuron."""
        neuron_id = arguments.get("neuron_id")
        neuron_name = arguments.get("neuron_name")

        if neuron_id is not None:
            url = f"{NEUROMORPHO_BASE_URL}/morphometry/id/{neuron_id}"
        elif neuron_name:
            url = f"{NEUROMORPHO_BASE_URL}/morphometry/name/{neuron_name}"
        else:
            return {
                "status": "error",
                "error": "Either neuron_id or neuron_name is required",
            }

        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        return {
            "status": "success",
            "data": data,
            "metadata": {"total_results": 1},
        }

    def _get_field_values(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get available values for a neuron metadata field."""
        field_name = arguments.get("field_name", "species")
        page = arguments.get("page", 0)
        size = arguments.get("size", 500)

        url = f"{NEUROMORPHO_BASE_URL}/neuron/fields/{field_name}"
        params = {"page": page, "size": size}

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        fields = data.get("fields", [])
        page_info = data.get("page", {})

        return {
            "status": "success",
            "data": fields,
            "metadata": {
                "field_name": field_name,
                "total_results": page_info.get("totalElements", len(fields)),
                "total_pages": page_info.get("totalPages", 1),
                "current_page": page_info.get("number", page),
            },
        }
