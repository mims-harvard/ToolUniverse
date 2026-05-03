# biosamples_tool.py
"""
EBI BioSamples REST API tool for ToolUniverse.

BioSamples is the EBI's central hub for sample metadata, containing
60+ million biological samples with standardized metadata including
organism, tissue type, disease, and experimental context. Samples are
cross-referenced to ENA, ArrayExpress, EVA, and other archives.

API: https://www.ebi.ac.uk/biosamples
No authentication required for reading. Free for all use.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

BIOSAMPLES_BASE_URL = "https://www.ebi.ac.uk/biosamples"


@register_tool("BioSamplesTool")
class BioSamplesTool(BaseTool):
    """
    Tool for querying EBI BioSamples database.

    Provides access to biological sample metadata including organism,
    tissue type, disease state, and links to associated data archives.

    No authentication required for read access.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "get_sample"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the BioSamples API call."""
        try:
            return self._dispatch(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"BioSamples API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to BioSamples API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"BioSamples API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying BioSamples: {str(e)}",
            }

    def _dispatch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint based on config."""
        if self.endpoint_type == "get_sample":
            return self._get_sample(arguments)
        elif self.endpoint_type == "search":
            return self._search(arguments)
        elif self.endpoint_type == "search_by_filter":
            return self._search_by_filter(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown endpoint_type: {self.endpoint_type}",
            }

    def _get_sample(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get a specific biological sample by accession."""
        accession = arguments.get("accession", "")
        if not accession:
            return {
                "status": "error",
                "error": "accession parameter is required (e.g., 'SAMEA104228123')",
            }

        url = f"{BIOSAMPLES_BASE_URL}/samples/{accession}"
        response = requests.get(
            url,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        raw = response.json()

        # Parse characteristics into a clean dict
        characteristics = {}
        for key, values in raw.get("characteristics", {}).items():
            if values and isinstance(values, list):
                chars = []
                for v in values:
                    text = v.get("text", "")
                    if text:
                        chars.append(text)
                if chars:
                    characteristics[key] = chars[0] if len(chars) == 1 else chars

        result = {
            "accession": raw.get("accession"),
            "name": raw.get("name"),
            "taxon_id": raw.get("taxId"),
            "status": raw.get("status"),
            "release_date": raw.get("release"),
            "update_date": raw.get("update"),
            "characteristics": characteristics,
        }

        # Add external references if present
        ext_refs = raw.get("externalReferences", [])
        if ext_refs:
            result["external_references"] = [
                {"url": ref.get("url"), "duo": ref.get("duo", [])}
                for ref in ext_refs[:10]
            ]

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "EBI BioSamples",
                "query": accession,
                "endpoint": "get_sample",
            },
        }

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search BioSamples by text query."""
        query = arguments.get("query", "")
        if not query:
            return {
                "status": "error",
                "error": "query parameter is required (e.g., 'breast cancer', 'liver tissue')",
            }

        size = min(arguments.get("limit", 10), 50)
        page = arguments.get("page", 0)

        params = {
            "text": query,
            "size": size,
            "page": page,
        }

        url = f"{BIOSAMPLES_BASE_URL}/samples"
        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        raw = response.json()

        results = []
        embedded = raw.get("_embedded", {})
        samples = embedded.get("samples", [])

        for sample in samples[:size]:
            # Extract key characteristics
            chars = {}
            for key, values in sample.get("characteristics", {}).items():
                if key in ("organism", "tissue", "disease", "cell type", "sex", "age"):
                    if values and isinstance(values, list):
                        chars[key] = values[0].get("text", "")

            results.append(
                {
                    "accession": sample.get("accession"),
                    "name": sample.get("name"),
                    "taxon_id": sample.get("taxId"),
                    "status": sample.get("status"),
                    "key_characteristics": chars,
                }
            )

        # Pagination info
        page_info = raw.get("page", {})

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "EBI BioSamples",
                "total_elements": page_info.get("totalElements"),
                "total_pages": page_info.get("totalPages"),
                "current_page": page_info.get("number"),
                "returned": len(results),
                "query": query,
                "endpoint": "search",
            },
        }

    def _search_by_filter(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search BioSamples with attribute filters."""
        attribute = arguments.get("attribute", "")
        value = arguments.get("value", "")
        if not attribute or not value:
            return {
                "status": "error",
                "error": "Both 'attribute' and 'value' parameters are required (e.g., attribute='organism', value='Homo sapiens')",
            }

        size = min(arguments.get("limit", 10), 50)

        # Build filter string
        filter_str = f"attr:{attribute}:{value}"

        params = {
            "filter": filter_str,
            "size": size,
        }

        url = f"{BIOSAMPLES_BASE_URL}/samples"
        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        raw = response.json()

        results = []
        embedded = raw.get("_embedded", {})
        samples = embedded.get("samples", [])

        for sample in samples[:size]:
            chars = {}
            for key, values in sample.get("characteristics", {}).items():
                if key in (
                    "organism",
                    "tissue",
                    "disease",
                    "cell type",
                    "sex",
                    "age",
                    "sample name",
                    "title",
                ):
                    if values and isinstance(values, list):
                        chars[key] = values[0].get("text", "")

            results.append(
                {
                    "accession": sample.get("accession"),
                    "name": sample.get("name"),
                    "taxon_id": sample.get("taxId"),
                    "key_characteristics": chars,
                }
            )

        page_info = raw.get("page", {})

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "EBI BioSamples",
                "total_elements": page_info.get("totalElements"),
                "returned": len(results),
                "filter": filter_str,
                "endpoint": "search_by_filter",
            },
        }
