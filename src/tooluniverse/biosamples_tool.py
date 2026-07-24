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
        elif self.endpoint_type == "get_relationships":
            return self._get_relationships(arguments)
        elif self.endpoint_type == "get_facets":
            return self._get_facets(arguments)
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

    def _get_relationships(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get the relationship/provenance graph for a BioSample.

        The raw sample JSON already carries a 'relationships' array (e.g.
        'derived from', 'has member', 'child of', 'same as', 'recurated into')
        that the standard get_sample parser drops. This exposes that lineage so
        sample-to-sample provenance (processed sample -> source tissue,
        sample-group -> member samples) is reachable.
        """
        accession = arguments.get("accession", "")
        if not accession:
            return {
                "status": "error",
                "error": "accession parameter is required (e.g., 'SAMEA4451312')",
            }

        url = f"{BIOSAMPLES_BASE_URL}/samples/{accession}"
        response = requests.get(
            url,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        raw = response.json()

        relationships = []
        for rel in raw.get("relationships", []) or []:
            source = rel.get("source")
            rel_type = rel.get("type")
            target = rel.get("target")
            # Indicate which side of the edge this sample is on so the
            # direction of the lineage is unambiguous to consumers.
            if source == accession:
                direction = "outgoing"
                related = target
            elif target == accession:
                direction = "incoming"
                related = source
            else:
                direction = "other"
                related = target
            relationships.append(
                {
                    "source": source,
                    "type": rel_type,
                    "target": target,
                    "direction": direction,
                    "related_accession": related,
                }
            )

        return {
            "status": "success",
            "data": {
                "accession": raw.get("accession", accession),
                "name": raw.get("name"),
                "relationships": relationships,
                "relationship_count": len(relationships),
            },
            "metadata": {
                "source": "EBI BioSamples",
                "query": accession,
                "endpoint": "get_relationships",
            },
        }

    def _get_facets(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Discover the available attribute facets for a text query.

        Returns the facet vocabulary (organism, status, SRA accession, external
        reference, release date range, ...) with sample counts plus the top
        values per facet, so a scientist learns which filterable attribute
        keys/values exist before running a structured filter search.
        """
        query = arguments.get("text") or arguments.get("query") or ""
        if not query:
            return {
                "status": "error",
                "error": "text parameter is required (e.g., 'cancer', 'liver')",
            }

        max_values = min(int(arguments.get("max_values", 10)), 50)

        url = f"{BIOSAMPLES_BASE_URL}/samples/facets"
        response = requests.get(
            url,
            params={"text": query},
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        raw = response.json()

        embedded = raw.get("_embedded", {})

        def _format_facets(facet_list: Any) -> list:
            formatted = []
            for facet in facet_list or []:
                values = [
                    {"label": v.get("label"), "count": v.get("count")}
                    for v in (facet.get("content") or [])[:max_values]
                ]
                formatted.append(
                    {
                        "attribute": facet.get("label"),
                        "type": facet.get("type"),
                        "count": facet.get("count"),
                        "top_values": values,
                    }
                )
            return formatted

        facets = _format_facets(embedded.get("facets", []))
        external_facets = _format_facets(
            embedded.get("externalReferenceDataFacets", [])
        )

        return {
            "status": "success",
            "data": {
                "facets": facets,
                "external_reference_data_facets": external_facets,
            },
            "metadata": {
                "source": "EBI BioSamples",
                "query": query,
                "facet_count": len(facets),
                "endpoint": "get_facets",
            },
        }
