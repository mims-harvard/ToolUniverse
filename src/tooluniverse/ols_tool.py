"""OLS API tool for ToolUniverse.

This module exposes the Ontology Lookup Service (OLS) endpoints that were
previously available through the dedicated MCP server. The MCP tooling has been
adapted into a synchronous local tool that fits the ToolUniverse runtime.
"""

from __future__ import annotations

import urllib.parse
from typing import Any, Dict, List, Optional

import requests
from pydantic import BaseModel, Field, HttpUrl, ValidationError

from .base_tool import BaseTool
from .tool_registry import register_tool

OLS_BASE_URL = "https://www.ebi.ac.uk/ols4"
REQUEST_TIMEOUT = 30.0  # 30 second timeout to prevent hanging on slow API responses


def url_encode_iri(iri: str) -> str:
    """Double URL encode an IRI as required by the OLS API."""

    return urllib.parse.quote(urllib.parse.quote(iri, safe=""), safe="")


def _expand_short_term_id(term_id: str) -> str:
    """Convert short ontology IDs (e.g. GO:0006338) to full OBO IRIs.

    Handles standard OBO ontologies (GO, HP, MONDO, CHEBI, etc.).
    EFO and other non-OBO ontologies keep their original form.
    """
    if not term_id or term_id.startswith("http"):
        return term_id
    if ":" in term_id:
        prefix, local = term_id.split(":", 1)
        return f"http://purl.obolibrary.org/obo/{prefix}_{local}"
    return term_id


def _infer_ontology_from_term_id(term_id: str) -> str:
    """Infer OLS ontology identifier from a CURIE prefix (e.g. 'HP:0001234' → 'hp')."""
    if term_id and ":" in term_id and not term_id.startswith("http"):
        return term_id.split(":", 1)[0].lower()
    return ""


class OntologyInfo(BaseModel):
    """Description of a single ontology entry in OLS."""

    id: str = Field(
        ..., description="Unique identifier for the ontology", alias="ontologyId"
    )
    title: str = Field(..., description="Name of the ontology")
    version: Optional[str] = Field(None, description="Version of the ontology")
    description: Optional[str] = Field(None, description="Description of the ontology")
    domain: Optional[str] = Field(None, description="Domain of the ontology")
    homepage: Optional[HttpUrl] = Field(None, description="URL for the ontology")
    preferred_prefix: Optional[str] = Field(
        None, description="Preferred prefix for the ontology", alias="preferredPrefix"
    )
    number_of_terms: Optional[int] = Field(
        None, description="Number of terms in the ontology"
    )
    number_of_classes: Optional[int] = Field(
        None, description="Number of classes in the ontology", alias="numberOfClasses"
    )
    repository: Optional[HttpUrl] = Field(
        None, description="Repository URL for the ontology"
    )


class PagedResponse(BaseModel):
    """Base structure for paginated responses returned by OLS."""

    total_elements: int = Field(
        0, description="Total number of items", alias="totalElements"
    )
    page: int = Field(0, description="Current page number")
    size: int = Field(
        20, description="Number of items in current page", alias="numElements"
    )
    total_pages: int = Field(0, description="Total number of pages", alias="totalPages")


class OntologySearchResponse(PagedResponse):
    """Paginated collection of ontologies returned by the search endpoint."""

    ontologies: List[OntologyInfo] = Field(
        ..., description="List of ontologies matching the search criteria"
    )


class TermInfo(BaseModel):
    """Basic term representation returned by OLS."""

    model_config = {"populate_by_name": True}

    iri: HttpUrl = Field(..., description="IRI of the term")
    ontology_name: str = Field(
        ...,
        description="Name of the ontology containing the term",
        alias="ontologyName",
    )
    short_form: str = Field(
        ..., description="Short form identifier for the term", alias="shortForm"
    )
    label: str = Field(..., description="Human-readable label for the term")
    obo_id: Optional[str] = Field(
        None, description="OBOLibrary ID for the term", alias="oboId"
    )
    is_obsolete: Optional[bool] = Field(
        False, description="Indicates if the term is obsolete", alias="isObsolete"
    )


class TermSearchResponse(PagedResponse):
    """Paginated set of OLS terms."""

    num_found: int = Field(
        0, description="Total number of terms found", alias="numFound"
    )
    terms: List[TermInfo] = Field(
        ..., description="List of terms matching the search criteria"
    )


class DetailedTermInfo(TermInfo):
    """Extended term details in OLS."""

    description: Optional[List[str]] = Field(None, description="Definition of the term")
    synonyms: Optional[List[str]] = Field(
        None, description="List of synonyms for the term"
    )


@register_tool("OLSTool")
class OLSTool(BaseTool):
    """Interact with the EMBL-EBI Ontology Lookup Service (OLS) REST API."""

    _OPERATIONS = {
        "search_terms": "_handle_search_terms",
        "get_ontology_info": "_handle_get_ontology_info",
        "search_ontologies": "_handle_search_ontologies",
        "get_term_info": "_handle_get_term_info",
        "get_term_children": "_handle_get_term_children",
        "get_term_ancestors": "_handle_get_term_ancestors",
        "find_similar_terms": "_handle_find_similar_terms",
    }

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.base_url = tool_config.get("base_url", OLS_BASE_URL).rstrip("/")
        self.timeout = tool_config.get("timeout", REQUEST_TIMEOUT)
        self.session = requests.Session()

    def __del__(self):
        try:
            self.session.close()
        except Exception:
            pass

    def run(self, arguments=None, **_: Any):
        """Dispatch the requested OLS operation."""

        arguments = arguments or {}
        operation = arguments.get("operation")
        # Auto-fill operation from tool config const if not provided by user
        if not operation:
            operation = self.get_schema_const_operation()
        if not operation:
            return {
                "status": "error",
                "error": "`operation` argument is required.",
                "available_operations": sorted(self._OPERATIONS.keys()),
            }

        handler_name = self._OPERATIONS.get(operation)
        if not handler_name:
            return {
                "status": "error",
                "error": f"Unsupported operation '{operation}'.",
                "available_operations": sorted(self._OPERATIONS.keys()),
            }

        handler = getattr(self, handler_name)
        try:
            result = handler(arguments)
            if isinstance(result, dict) and "status" not in result:
                return {"status": "success", **result}
            return result
        except requests.RequestException as exc:
            return {"status": "error", "error": str(exc)}
        except ValidationError as exc:
            return {
                "status": "error",
                "error": "Failed to validate OLS response.",
                "details": exc.errors(),
            }

    def _handle_search_terms(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get("query")
        if not query:
            return {
                "status": "error",
                "error": "`query` parameter is required for `search_terms`.",
            }

        rows = int(
            arguments.get("rows")
            or arguments.get("limit")
            or arguments.get("size")
            or 10
        )
        ontology = arguments.get("ontology")
        exact_match = bool(arguments.get("exact_match", False))
        include_obsolete = bool(arguments.get("include_obsolete", False))

        params = {
            "q": query,
            "rows": rows,
            "start": 0,
            "exact": exact_match,
            "obsoletes": include_obsolete,
        }
        if ontology:
            params["ontology"] = ontology

        data = self._get_json("/api/search", params=params)

        # OLS /api/search returns a Solr-style envelope: {"response": {"docs": [...], "numFound": N}, ...}
        # Extract docs and numFound directly to avoid returning noisy facet_counts.
        solr_response = data.get("response") if isinstance(data, dict) else None
        if isinstance(solr_response, dict) and "docs" in solr_response:
            docs = solr_response.get("docs", [])
            num_found = solr_response.get("numFound", len(docs))
            term_models = [self._build_term_model(item) for item in docs[:rows]]
            term_models = [m for m in term_models if m is not None]
            formatted: Dict[str, Any] = {
                "terms": [
                    m.model_dump(by_alias=True, mode="json") for m in term_models
                ],
                "total_items": num_found,
                "showing": len(term_models),
            }
        else:
            formatted = self._format_term_collection(data, rows)

        formatted["query"] = query
        formatted["filters"] = {
            "ontology": ontology,
            "exact_match": exact_match,
            "include_obsolete": include_obsolete,
        }
        return formatted

    def _handle_get_ontology_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        # Feature-120A-003: accept 'ontology' alias for consistency with other OLS tools
        ontology_id = arguments.get("ontology_id") or arguments.get("ontology")
        if not ontology_id:
            return {
                "status": "error",
                "error": "`ontology_id` (or `ontology`) is required. E.g. 'mondo', 'hp', 'go'.",
            }

        data = self._get_json(f"/api/v2/ontologies/{ontology_id}")
        ontology = OntologyInfo.model_validate(data)
        # Convert HttpUrl objects to strings for JSON compatibility
        result = ontology.model_dump(by_alias=True, mode="json")
        return result

    def _handle_search_ontologies(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        search = arguments.get("search")
        page = int(arguments.get("page", 0))
        size = int(arguments.get("size", 20))

        params: Dict[str, Any] = {"page": page, "size": size}
        if search:
            params["search"] = search

        data = self._get_json("/api/v2/ontologies", params=params)
        # Feature-120A-001: OLS v4 returns ontologies in top-level 'elements', not '_embedded'
        ontologies = data.get(
            "elements", data.get("_embedded", {}).get("ontologies", [])
        )

        validated: List[Dict[str, Any]] = []
        for item in ontologies:
            try:
                validated.append(
                    OntologyInfo.model_validate(item).model_dump(
                        by_alias=True, mode="json"
                    )
                )
            except ValidationError:
                continue

        return {
            "status": "success",
            "results": validated or ontologies,
            "pagination": {
                "page": page,
                "size": size,
                "total_pages": data.get("totalPages", 0),
                "total_items": data.get("totalElements", len(ontologies)),
            },
            "search": search,
        }

    def _handle_get_term_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        # Feature-111A-003: term_iri alias for id (consistent with sibling OLS tools)
        identifier = (
            arguments.get("id") or arguments.get("term_id") or arguments.get("term_iri")
        )
        if not identifier:
            return {
                "status": "error",
                "error": "`id` parameter is required for `get_term_info`. Use HP:0001903 style IDs.",
            }

        # Use ontology-specific endpoint when a CURIE prefix is known (e.g. GO:, HP:)
        # to avoid getting a term from an importing ontology (e.g. bcgo) instead of canonical source.
        ontology = arguments.get("ontology") or _infer_ontology_from_term_id(identifier)
        terms = None
        if ontology:
            data = self._get_json(
                f"/api/ontologies/{ontology}/terms", params={"obo_id": identifier}
            )
            embedded = data.get("_embedded", {})
            terms = embedded.get("terms") if isinstance(embedded, dict) else None
        if not terms:
            data = self._get_json("/api/terms", params={"id": identifier})
            embedded = data.get("_embedded", {})
            terms = embedded.get("terms") if isinstance(embedded, dict) else None
        if not terms:
            return {
                "status": "error",
                "error": f"Term with ID '{identifier}' was not found in OLS.",
            }

        # Normalize the term data before validation
        term_data = terms[0]
        if "ontologyId" in term_data and "ontologyName" not in term_data:
            term_data["ontologyName"] = term_data["ontologyId"]

        term = DetailedTermInfo.model_validate(term_data)
        # Convert HttpUrl objects to strings for JSON compatibility
        return term.model_dump(by_alias=True, mode="json")

    def _handle_get_term_children(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        raw_term_id = arguments.get("term_iri") or arguments.get("term_id", "")
        term_iri = _expand_short_term_id(raw_term_id)
        ontology = arguments.get("ontology") or _infer_ontology_from_term_id(
            raw_term_id
        )
        if not term_iri or not ontology:
            return {
                "status": "error",
                "error": "`term_iri` (or `term_id`) and `ontology` are required for `get_term_children`. Tip: if you pass `term_id` like 'HP:0001234', the ontology is inferred automatically.",
            }

        include_obsolete = bool(arguments.get("include_obsolete", False))
        size = int(arguments.get("size", 20))
        encoded = url_encode_iri(term_iri)

        params = {
            "page": 0,
            "size": size,
            "includeObsoleteEntities": include_obsolete,
        }

        data = self._get_json(
            f"/api/v2/ontologies/{ontology}/classes/{encoded}/children", params=params
        )
        formatted = self._format_term_collection(data, size)
        formatted["term_iri"] = term_iri
        formatted["ontology"] = ontology
        formatted["filters"] = {"include_obsolete": include_obsolete}
        return formatted

    def _handle_get_term_ancestors(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        raw_term_id = arguments.get("term_iri") or arguments.get("term_id", "")
        term_iri = _expand_short_term_id(raw_term_id)
        ontology = arguments.get("ontology") or _infer_ontology_from_term_id(
            raw_term_id
        )
        if not term_iri or not ontology:
            return {
                "status": "error",
                "error": "`term_iri` (or `term_id`) and `ontology` are required for `get_term_ancestors`. Tip: if you pass `term_id` like 'HP:0001234', the ontology is inferred automatically.",
            }

        include_obsolete = bool(arguments.get("include_obsolete", False))
        size = int(arguments.get("size", 20))
        encoded = url_encode_iri(term_iri)

        params = {
            "page": 0,
            "size": size,
            "includeObsoleteEntities": include_obsolete,
        }

        data = self._get_json(
            f"/api/v2/ontologies/{ontology}/classes/{encoded}/ancestors", params=params
        )
        formatted = self._format_term_collection(data, size)
        formatted["term_iri"] = term_iri
        formatted["ontology"] = ontology
        formatted["filters"] = {"include_obsolete": include_obsolete}
        return formatted

    def _handle_find_similar_terms(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        # Feature-120A-002: /llm_similar does not exist in OLS v4; use text search instead.
        # Resolve the term to get its label, then search within the ontology.
        term_iri = _expand_short_term_id(
            arguments.get("term_iri") or arguments.get("term_id", "")
        )
        ontology = arguments.get("ontology")
        if not term_iri or not ontology:
            return {
                "status": "error",
                "error": "`term_iri` (or `term_id`) and `ontology` are required for `find_similar_terms`.",
            }

        size = int(arguments.get("size", 10))

        # Step 1: get the term's label to use as search query
        label = ""
        try:
            encoded = url_encode_iri(term_iri)
            term_data = self._get_json(
                f"/api/v2/ontologies/{ontology}/classes/{encoded}"
            )
            label = term_data.get("label", "")
        except Exception:
            pass

        if not label:
            return {
                "status": "error",
                "error": f"Could not retrieve label for term '{term_iri}' in ontology '{ontology}'. Verify the term ID is correct.",
            }

        # Step 2: search within the ontology for terms with similar labels
        params = {"q": label, "ontology": ontology, "type": "class", "rows": size + 1}
        data = self._get_json("/api/search", params=params)
        docs = data.get("response", {}).get("docs", [])

        # Exclude the query term itself
        similar = [d for d in docs if d.get("iri") != term_iri][:size]

        return {
            "status": "success",
            "term_iri": term_iri,
            "source_label": label,
            "ontology": ontology,
            "similar_terms": similar,
            "total": len(similar),
            "note": "Results via text search (OLS v4 semantic similarity endpoint unavailable).",
        }

    def _get_json(
        self, path: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a GET request to the OLS API and return JSON response.

        Args:
            path: API endpoint path
            params: Optional query parameters

        Returns:
            JSON response as dictionary

        Raises:
            requests.RequestException: On network errors or timeouts
            requests.HTTPError: On HTTP errors (4xx, 5xx)
        """
        url = f"{self.base_url}{path}"
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            if response.status_code == 503:
                raise requests.RequestException(
                    "EBI OLS4 service is temporarily unavailable (HTTP 503). "
                    "Try again later. Alternatives: search HPO phenotypes via "
                    "Orphanet_get_phenotypes, or look up disease terms via "
                    "Orphanet_search_by_name or EuropePMC."
                )
            response.raise_for_status()
            return response.json()
        except requests.Timeout as e:
            raise requests.RequestException(
                f"OLS API request timed out after {self.timeout}s: {url}"
            ) from e
        except requests.RequestException as e:
            raise requests.RequestException(
                f"OLS API request failed for {url}: {str(e)}"
            ) from e

    def _format_term_collection(
        self, data: Dict[str, Any], size: int
    ) -> Dict[str, Any]:
        elements: Optional[List[Dict[str, Any]]] = None

        if isinstance(data, dict):
            if "elements" in data and isinstance(data["elements"], list):
                elements = data["elements"]
            else:
                embedded = data.get("_embedded")
                if isinstance(embedded, dict):
                    # OLS responses can use different embedded keys depending on endpoint/version.
                    # Keep this list conservative but inclusive for OLS4 v2 term hierarchy endpoints.
                    for key in ("terms", "children", "ancestors", "classes"):
                        if key in embedded and isinstance(embedded[key], list):
                            elements = embedded[key]
                            break
                    if elements is None:
                        candidates = [
                            value
                            for value in embedded.values()
                            if isinstance(value, list)
                        ]
                        if candidates:
                            elements = candidates[0]

        if not elements:
            return data if isinstance(data, dict) else {"items": data}

        limited = elements[:size]
        term_models = [self._build_term_model(item) for item in limited]
        term_models = [model for model in term_models if model is not None]

        total = (
            data.get("totalElements")
            or data.get("page", {}).get("totalElements")
            or len(elements)
        )

        result: Dict[str, Any] = {
            "terms": [
                model.model_dump(by_alias=True, mode="json") for model in term_models
            ],
            "total_items": total,
            "showing": len(term_models),
        }

        page_info = data.get("page") if isinstance(data, dict) else None
        if isinstance(page_info, dict):
            result["pagination"] = {
                "page": page_info.get("number", 0),
                "size": page_info.get("size", len(limited)),
                "total_pages": page_info.get("totalPages", 0),
                "total_items": page_info.get("totalElements", total),
            }

        return result

    @staticmethod
    def _build_term_model(item: Dict[str, Any]) -> Optional[TermInfo]:
        # OLS4 v2 endpoints may represent the identifier as `iri`, `@id`, or `id`.
        iri = item.get("iri") or item.get("@id") or item.get("id")
        # OLS4 v2 often returns `label` as a list (e.g. ["lymphocyte"]).
        label = item.get("label")
        if isinstance(label, list):
            label = next(
                (val for val in label if isinstance(val, str) and val.strip()), ""
            )
        elif not isinstance(label, str):
            label = ""

        # Prefer CURIE if present (more human-friendly), otherwise fall back to shortForm.
        short_form = (
            item.get("curie") or item.get("shortForm") or item.get("short_form") or ""
        )
        payload = {
            "iri": iri,
            "ontology_name": item.get("ontologyName")
            or item.get("ontology_name")
            or item.get("ontologyId")
            or "",
            "short_form": short_form,
            "label": label,
            "oboId": item.get("oboId")
            or item.get("obo_id")
            or item.get("curie")
            or short_form
            or None,
            "isObsolete": item.get("isObsolete") or item.get("is_obsolete", False),
        }

        if not payload["iri"]:
            return None

        try:
            return TermInfo.model_validate(payload)
        except ValidationError:
            return None


__all__ = [
    "OLSTool",
    "OntologyInfo",
    "OntologySearchResponse",
    "TermInfo",
    "TermSearchResponse",
    "DetailedTermInfo",
    "url_encode_iri",
]
