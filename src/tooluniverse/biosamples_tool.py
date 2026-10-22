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
from urllib.parse import parse_qs, urlparse
from .base_tool import BaseTool
from .tool_registry import register_tool

BIOSAMPLES_BASE_URL = "https://www.ebi.ac.uk/biosamples"


def _integer_argument(
    value: Any, *, name: str, minimum: int, maximum: int
) -> tuple[int | None, str | None]:
    """Validate pagination integers without silently clamping them."""
    if isinstance(value, bool):
        return None, f"{name} must be an integer from {minimum} to {maximum}"
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None, f"{name} must be an integer from {minimum} to {maximum}"
    if isinstance(value, float) and not value.is_integer():
        return None, f"{name} must be an integer from {minimum} to {maximum}"
    if parsed < minimum or parsed > maximum:
        return None, f"{name} must be an integer from {minimum} to {maximum}"
    return parsed, None


def _cursor_from_link(link: Any) -> str | None:
    """Extract an opaque cursor token from a HAL link object."""
    href = link.get("href") if isinstance(link, dict) else link
    if not isinstance(href, str):
        return None
    values = parse_qs(urlparse(href).query).get("cursor")
    return values[0] if values else None


def _pagination_arguments(
    arguments: Dict[str, Any]
) -> tuple[int | None, int | None, str | None, str | None]:
    limit_value = arguments.get("limit")
    limit, error = _integer_argument(
        10 if limit_value is None else limit_value,
        name="limit",
        minimum=1,
        maximum=200,
    )
    if error:
        return None, None, None, error

    cursor_value = arguments.get("cursor")
    if cursor_value is not None:
        if "page" in arguments and arguments.get("page") is not None:
            return None, None, None, "page and cursor are mutually exclusive"
        if not isinstance(cursor_value, str) or not cursor_value:
            return None, None, None, "cursor must be '*' or an opaque cursor token"
        return limit, None, cursor_value, None

    page_value = arguments.get("page")
    page, error = _integer_argument(
        0 if page_value is None else page_value,
        name="page",
        minimum=0,
        maximum=500,
    )
    return limit, page, None, error


def _pagination_metadata(
    raw: Dict[str, Any],
    *,
    requested_page: int | None,
    requested_cursor: str | None,
    limit: int,
    returned: int,
) -> Dict[str, Any]:
    links = raw.get("_links", {}) if isinstance(raw, dict) else {}
    next_link = links.get("next")
    next_url = next_link.get("href") if isinstance(next_link, dict) else next_link
    page_info = raw.get("page", {}) if isinstance(raw, dict) else {}
    page_info = page_info if isinstance(page_info, dict) else {}

    if requested_cursor is not None:
        has_more = bool(next_url)
        return {
            "pagination_mode": "cursor",
            "cursor": requested_cursor,
            "next_cursor": _cursor_from_link(next_link),
            "next_url": next_url,
            "current_page": None,
            "next_page": None,
            "total_elements": None,
            "total_pages": None,
            "returned": returned,
            "limit": limit,
            "has_more": has_more,
            "truncated": has_more,
            "cursor_required_for_complete_retrieval": False,
        }

    current_page = page_info.get("number", requested_page)
    total_pages = page_info.get("totalPages")
    has_more = (
        current_page + 1 < total_pages
        if isinstance(current_page, int) and isinstance(total_pages, int)
        else bool(next_url)
    )
    page_limit_reached = bool(has_more and current_page == 500)
    cursor_required = bool(isinstance(total_pages, int) and total_pages > 501)
    return {
        "pagination_mode": "page",
        "total_elements": page_info.get("totalElements"),
        "total_pages": total_pages,
        "current_page": current_page,
        "returned": returned,
        "limit": limit,
        "has_more": has_more,
        "truncated": has_more,
        "next_page": current_page + 1
        if has_more and not page_limit_reached and isinstance(current_page, int)
        else None,
        "cursor_start": _cursor_from_link(links.get("cursor")),
        "cursor_required_for_complete_retrieval": cursor_required,
        "page_limit_reached": page_limit_reached,
        "warning": (
            "BioSamples page navigation is capped at page 500; restart with "
            "cursor='*' and follow next_cursor for complete retrieval."
            if cursor_required
            else None
        ),
    }


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

        size, page, cursor, pagination_error = _pagination_arguments(arguments)
        if pagination_error:
            return {"status": "error", "error": pagination_error}
        assert size is not None

        params = {
            "text": query,
            "size": size,
        }
        if cursor is not None:
            params["cursor"] = cursor
        else:
            params["page"] = page

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

        pagination = _pagination_metadata(
            raw,
            requested_page=page,
            requested_cursor=cursor,
            limit=size,
            returned=len(results),
        )
        pagination.update(
            {
                "source": "EBI BioSamples",
                "query": query,
                "endpoint": "search",
            }
        )

        return {
            "status": "success",
            "data": results,
            "metadata": pagination,
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

        size, page, cursor, pagination_error = _pagination_arguments(arguments)
        if pagination_error:
            return {"status": "error", "error": pagination_error}
        assert size is not None

        # Build filter string
        filter_str = f"attr:{attribute}:{value}"

        params = {
            "filter": filter_str,
            "size": size,
        }
        if cursor is not None:
            params["cursor"] = cursor
        else:
            params["page"] = page

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

        pagination = _pagination_metadata(
            raw,
            requested_page=page,
            requested_cursor=cursor,
            limit=size,
            returned=len(results),
        )
        pagination.update(
            {
                "source": "EBI BioSamples",
                "filter": filter_str,
                "endpoint": "search_by_filter",
            }
        )

        return {
            "status": "success",
            "data": results,
            "metadata": pagination,
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
