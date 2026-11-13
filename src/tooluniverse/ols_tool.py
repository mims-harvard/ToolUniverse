"""OLS API tool for ToolUniverse.

This module exposes the Ontology Lookup Service (OLS) endpoints that were
previously available through the dedicated MCP server. The MCP tooling has been
adapted into a synchronous local tool that fits the ToolUniverse runtime.
"""

from __future__ import annotations

import re
import urllib.parse
from typing import Any, Dict, List, Optional

import requests
from pydantic import (
    AliasChoices,
    BaseModel,
    Field,
    HttpUrl,
    ValidationError,
    field_validator,
)

from .base_tool import BaseTool
from .tool_registry import register_tool

OLS_BASE_URL = "https://www.ebi.ac.uk/ols4"
REQUEST_TIMEOUT = 30.0  # 30 second timeout to prevent hanging on slow API responses

# OLS4's `/api/search?exact=true` flag on its own restricts almost nothing: the
# endpoint defaults to matching across label, synonym, description, iri,
# short_form and obo_id, so an "exact" hit against a *description* token still
# drags in the whole neighbourhood. Measured against the live API:
#   q=fibroblast&ontology=cl&exact=true                     -> 167 of 168 terms
#   q=fibroblast&ontology=cl&exact=true&queryFields=label   -> 1 term
#   q=T cell&ontology=cl&exact=true                         -> 6803 terms
#   q=T cell&ontology=cl&exact=true&queryFields=label,synonym -> 1 term
# Constraining `queryFields` is therefore what makes `exact` mean what it says.
# Synonyms are included because an exact hit on an alternative name is a genuine
# exact match ('T-lymphocyte' -> CL:0000084 'T cell', 'aspirin' -> CHEBI:15365).
_EXACT_NAME_FIELDS = "label,synonym"

# Identifier-shaped queries are not names, and restricting them to label/synonym
# returns nothing at all (q=CL:0000084&queryFields=label,synonym -> 0 hits), so
# they get matched against the identifier fields instead.
_EXACT_IDENTIFIER_FIELDS = "obo_id,short_form,iri"

# CURIE ('CL:0000084') or OBO underscore form ('CL_0000084'). Deliberately
# rejects anything containing whitespace so ordinary multi-word labels such as
# 'type 2 diabetes mellitus' are treated as names.
_IDENTIFIER_QUERY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9.]*[:_][A-Za-z0-9._-]+$")


def _exact_query_fields(query: str) -> str:
    """Return the OLS4 ``queryFields`` set that makes ``exact=true`` restrictive."""

    candidate = query.strip()
    if candidate.lower().startswith(("http://", "https://")):
        return _EXACT_IDENTIFIER_FIELDS
    if _IDENTIFIER_QUERY_RE.match(candidate):
        return _EXACT_IDENTIFIER_FIELDS
    return _EXACT_NAME_FIELDS


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
    # OBO PURLs are case-sensitive and always upper-case the prefix, so a
    # well-formed but differently-cased CURIE ('mondo:0005180', the canonical
    # Bioregistry spelling) must be normalized. Forwarding the caller's casing
    # verbatim produced a valid-looking PURL that OLS resolves to nothing,
    # which is indistinguishable from a genuine leaf term.
    separator = ":" if ":" in term_id else ("_" if "_" in term_id else "")
    if separator:
        prefix, local = term_id.split(separator, 1)
        return f"http://purl.obolibrary.org/obo/{prefix.upper()}_{local}"
    return term_id


# EFO:0000270 carries 49 curatedFrom entries -- the text each data source
# annotated with the term -- and this many are reported.
CURATED_FROM_PER_TERM = 25


def _as_string_list(value) -> Optional[List[str]]:
    """OLS sends a string, a list of strings, or nothing, per field and version."""
    if value is None:
        return None
    if isinstance(value, str):
        return [value] if value.strip() else None
    if isinstance(value, list):
        items = [item for item in value if isinstance(item, str) and item.strip()]
        return items or None
    return None


def _infer_ontology_from_term_id(term_id: str) -> str:
    """Infer OLS ontology identifier from a CURIE prefix (e.g. 'HP:0001234' → 'hp').

    Accepts both the colon CURIE and the underscore form used in OBO IRIs
    ('MONDO_0005180'), which these tools emit themselves in their `iri` and
    `shortForm` fields.
    """
    if not term_id or term_id.startswith("http"):
        return ""
    for separator in (":", "_"):
        if separator in term_id:
            return term_id.split(separator, 1)[0].lower()
    return ""


class OntologyInfo(BaseModel):
    """Description of a single ontology entry in OLS."""

    id: str = Field(
        ..., description="Unique identifier for the ontology", alias="ontologyId"
    )
    # 16 of the 287 ontologies OLS lists carry no plain `title`, and a required
    # str made get_ontology_info answer a validation error for each of them --
    # and made search_ontologies drop all 16 while still reporting
    # total_items: 287. Twelve name the title under a Dublin Core or rdfs key,
    # sometimes as a list. medgen, oio and the two schemaorg entries have no
    # title under any key in either API version, and now come back as null.
    title: Optional[str] = Field(
        None,
        description="Name of the ontology",
        validation_alias=AliasChoices(
            "title",
            "http://purl.org/dc/terms/title",
            "http://purl.org/dc/elements/1.1/title",
            "label",
            "http://www.w3.org/2000/01/rdf-schema#label",
        ),
    )

    # OLS v2 publishes the release as the OWL annotation property rather than
    # under a short key; v1's flat `version` carried the identical string.
    version: Optional[str] = Field(
        None,
        description="Version of the ontology",
        validation_alias=AliasChoices(
            "version", "http://www.w3.org/2002/07/owl#versionInfo"
        ),
    )
    description: Optional[str] = Field(None, description="Description of the ontology")
    domain: Optional[str] = Field(None, description="Domain of the ontology")
    homepage: Optional[HttpUrl] = Field(None, description="URL for the ontology")
    preferred_prefix: Optional[str] = Field(
        None, description="Preferred prefix for the ontology", alias="preferredPrefix"
    )
    # v2 dropped `numberOfTerms`; the count it reported is v2's
    # `numberOfClasses` (identical on go, hp, efo, mondo, chebi and uberon).
    number_of_terms: Optional[int] = Field(
        None,
        description="Number of terms in the ontology",
        validation_alias=AliasChoices("numberOfTerms", "numberOfClasses"),
    )
    number_of_classes: Optional[int] = Field(
        None, description="Number of classes in the ontology", alias="numberOfClasses"
    )
    repository: Optional[HttpUrl] = Field(
        None, description="Repository URL for the ontology"
    )
    # EFO imports terms from 40 ontologies and 36 import from it. Which
    # ontologies an ontology depends on, and which depend on it, is the
    # question "ontology info" is asked for when choosing one to annotate
    # against; none of these five reached the caller.
    imports_from: Optional[List[str]] = Field(
        None,
        description="Ontologies this one imports terms from",
        alias="importsFrom",
    )
    exports_to: Optional[List[str]] = Field(
        None,
        description="Ontologies that import terms from this one",
        alias="exportsTo",
    )
    links_to: Optional[List[str]] = Field(
        None,
        description="Property and term IRIs from other ontologies that this one uses",
        alias="linksTo",
    )
    creators: Optional[List[str]] = Field(
        None,
        description="Who authored the ontology, from dc:creator",
        validation_alias=AliasChoices(
            "creators",
            "http://purl.org/dc/elements/1.1/creator",
            "http://purl.org/dc/terms/creator",
        ),
    )
    languages: Optional[List[str]] = Field(
        None,
        description=(
            "Language codes the ontology carries labels in. EFO has eight, so "
            "a label search can miss a term that is only labelled in one."
        ),
        validation_alias=AliasChoices("languages", "language"),
    )
    license: Optional[str] = Field(
        None,
        description="Licence the ontology is published under",
        validation_alias=AliasChoices(
            "license",
            "http://purl.org/dc/terms/license",
            "http://purl.org/dc/elements/1.1/license",
        ),
    )
    loaded: Optional[str] = Field(
        None, description="When OLS last loaded this ontology, so how current it is"
    )
    mailing_list: Optional[str] = Field(
        None, description="Where to ask about the ontology", alias="mailingList"
    )
    number_of_properties: Optional[int] = Field(
        None, description="Number of properties", alias="numberOfProperties"
    )
    number_of_individuals: Optional[int] = Field(
        None, description="Number of individuals", alias="numberOfIndividuals"
    )

    @field_validator(
        "imports_from",
        "exports_to",
        "links_to",
        "creators",
        "languages",
        mode="before",
    )
    @classmethod
    def _as_list_of_strings(cls, value):
        """Each of these is a list on v2 and a bare string on some entries."""
        if value is None:
            return None
        if isinstance(value, str):
            return [value] if value.strip() else None
        if isinstance(value, list):
            items = [str(item) for item in value if item is not None]
            return items or None
        return None

    @field_validator("license", "loaded", mode="before")
    @classmethod
    def _first_string(cls, value):
        if isinstance(value, list):
            value = value[0] if value else None
        return str(value) if value is not None else None

    @field_validator("title", "version", mode="before")
    @classmethod
    def _first_of_a_list(cls, value):
        """Several of these keys hold a list. Measured across all 287
        ontologies OLS lists: `label` is a list every one of the 199 times it
        is present, rdfs#label 3 times out of 20, the two Dublin Core titles
        once and twice, and owl#versionInfo for 8 ontologies -- foodon answers
        ['2026-02-02', '2026-09-20'] and bmont ['2025-06-20', 'Version
        Release: 0.5.8']. OLS gives no order for those, so the first is taken
        and the rest dropped rather than joined into a version string that
        upstream never published.

        Without this, giving `version` the owl#versionInfo alias turned those 8
        into validation errors, which is how the commit before this one broke
        them."""
        if isinstance(value, list):
            return value[0] if value else None
        return value


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
    # The search endpoint answers all five of these on every hit and the row
    # carried a label and an id. A term search whose rows have no definition
    # costs one get_term_info call per hit to decide which hit was meant --
    # and `description` is where OLS records a merge, e.g. ZFA:0009046 says
    # "CL:0000804 and CL:0000812 were merged ... into CL:0000084".
    description: Optional[List[str]] = Field(
        None, description="Definition of the term, as the search hit carries it"
    )
    synonyms: Optional[List[str]] = Field(
        None, description="Exact synonyms of the term"
    )
    related_synonyms: Optional[List[str]] = Field(
        None,
        description=(
            "Related synonyms, which OBO distinguishes from exact ones: a "
            "related synonym cannot be substituted for the label."
        ),
    )
    ontology_prefix: Optional[str] = Field(
        None,
        description="Ontology prefix as used in the CURIE, e.g. ZFA",
        alias="ontologyPrefix",
    )
    type: Optional[str] = Field(
        None, description="What kind of entity the hit is: class, property or individual"
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

    # `description` and `synonyms` are inherited from TermInfo, which now
    # carries them because the search hits do too.
    # An ontology merges terms, and the retired id becomes an alternative id
    # on the surviving one. Without it, a caller holding an old EFO id cannot
    # tell that the term they were given is the replacement -- and OLS answers
    # it in the same record, under `annotation.has_alternative_id`.
    alternative_ids: Optional[List[str]] = Field(
        None,
        description=(
            "Other ids this term is known by, including ids merged into it. "
            "From annotation.has_alternative_id."
        ),
    )
    synonym_scopes: Optional[List[Dict[str, Any]]] = Field(
        None,
        description=(
            "Each synonym with the scope OBO assigns it -- hasExactSynonym "
            "against hasRelatedSynonym -- which `synonyms` flattens away. An "
            "exact synonym can be substituted for the label; a related one "
            "cannot."
        ),
    )
    lang: Optional[str] = Field(None, description="Language of the label")


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
        "get_term_xrefs": "_handle_get_term_xrefs",
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
            return handler(arguments)
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

        rows = min(
            max(
                1,
                int(
                    arguments.get("rows")
                    or arguments.get("limit")
                    or arguments.get("size")
                    or 10
                ),
            ),
            100,
        )
        start = max(0, int(arguments.get("start") or 0))
        ontology = arguments.get("ontology")
        exact_match = bool(arguments.get("exact_match", False))
        include_obsolete = bool(arguments.get("include_obsolete", False))

        params = {
            "q": query,
            "rows": rows,
            "start": start,
            "exact": exact_match,
            "obsoletes": include_obsolete,
        }
        # Only constrain `queryFields` when exact matching was actually asked
        # for; the unfiltered search must keep its full-text recall.
        exact_fields = _exact_query_fields(str(query)) if exact_match else None
        if exact_fields:
            params["queryFields"] = exact_fields
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
                "start": start,
                "has_more": start + len(term_models) < num_found,
                "next_start": (
                    start + len(term_models)
                    if start + len(term_models) < num_found
                    else None
                ),
            }
        else:
            formatted = self._format_term_collection(data, rows)

        formatted["query"] = query
        filters = {
            "ontology": ontology,
            "exact_match": exact_match,
            "include_obsolete": include_obsolete,
        }
        # State which fields the exact match was applied to, so the echoed
        # `exact_match: true` is a verifiable claim rather than an assertion the
        # caller has to take on trust.
        if exact_fields:
            filters["exact_match_fields"] = exact_fields
        formatted["filters"] = filters
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
        size = min(max(1, int(arguments.get("size", 20))), 1000)

        params: Dict[str, Any] = {"page": page, "size": size}
        if search:
            params["search"] = search

        data = self._get_json("/api/v2/ontologies", params=params)
        # Feature-120A-001: OLS v4 returns ontologies in top-level 'elements', not '_embedded'
        ontologies = data.get(
            "elements", data.get("_embedded", {}).get("ontologies", [])
        )

        validated: List[Dict[str, Any]] = []
        dropped = 0
        for item in ontologies:
            try:
                validated.append(
                    OntologyInfo.model_validate(item).model_dump(
                        by_alias=True, mode="json"
                    )
                )
            except ValidationError:
                # Skipping the row is the right call -- one unreadable ontology
                # should not fail the whole listing -- but it has to be
                # counted. This handler used to drop silently and still report
                # upstream's total_items, so when `title` was a required field
                # it returned 263 of the 287 ontologies OLS lists and the
                # pagination still said 287.
                dropped += 1

        total_pages = data.get("totalPages", 0)
        total_items = data.get("totalElements", len(ontologies))
        has_more = page + 1 < total_pages
        payload = {
            # No fallback to the raw upstream objects here. `validated or
            # ontologies` meant that a page on which every row failed
            # validation came back as raw OLS v2 payloads -- different keys,
            # different shapes, under a schema describing the projected ones.
            # Returning no rows and saying how many were unreadable is the
            # honest answer.
            "results": validated,
            "pagination": {
                "page": page,
                "size": size,
                # `showing` is what this page actually carries, the same word
                # the term handlers in this tool use; total_items stays
                # upstream's count. They differ when rows were dropped.
                "showing": len(validated),
                "dropped": dropped,
                "total_pages": total_pages,
                "total_items": total_items,
                "has_more": has_more,
                "next_page": page + 1 if has_more else None,
            },
            "search": search,
        }
        # Keep the legacy top-level fields while also supplying the standard
        # ToolUniverse `data` envelope used by return-schema validation.
        return {"status": "success", "data": payload, **payload}

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
        annotation = term_data.get("annotation")
        if isinstance(annotation, dict) and annotation.get("has_alternative_id"):
            term_data["alternative_ids"] = annotation["has_alternative_id"]
        obo_synonyms = term_data.get("obo_synonym")
        if isinstance(obo_synonyms, list) and obo_synonyms:
            term_data["synonym_scopes"] = [
                {
                    "name": item.get("name"),
                    "scope": item.get("scope"),
                    "type": item.get("type"),
                    "xrefs": item.get("xrefs") or [],
                }
                for item in obo_synonyms
                if isinstance(item, dict)
            ]

        term = DetailedTermInfo.model_validate(term_data)
        # Convert HttpUrl objects to strings for JSON compatibility
        return term.model_dump(by_alias=True, mode="json")

    def _handle_get_term_xrefs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Return the obo_xref (database cross-references) of an OLS term.

        Translates any OLS term (EFO/MONDO/UBERON/CL/GO/CHEBI/ORDO/...) to its
        equivalent IDs in external vocabularies (DOID, ICD10, OMIM, UMLS, MeSH,
        NCIt, SNOMED/SCTID, MedDRA, etc.). This is the OxO-replacement mapping
        use case: the OLS4 term record carries an ``obo_xref`` array that the
        other OLS-family tools strip when they whitelist fields.
        """
        identifier = (
            arguments.get("id")
            or arguments.get("term_id")
            or arguments.get("obo_id")
            or arguments.get("term_iri")
        )
        if not identifier:
            return {
                "status": "error",
                "error": "`id` (or `term_id`/`obo_id`) is required for `get_term_xrefs`. Use CURIE style IDs, e.g. EFO:0004611 or MONDO:0005148.",
            }

        ontology = arguments.get("ontology") or _infer_ontology_from_term_id(identifier)
        terms = None
        # Prefer the ontology-scoped endpoint with obo_id, which reliably returns
        # the canonical record (and its obo_xref) for that ontology.
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

        term_data = terms[0]
        raw_xrefs = term_data.get("obo_xref") or []
        xrefs: List[Dict[str, Any]] = []
        for entry in raw_xrefs:
            if not isinstance(entry, dict):
                continue
            database = entry.get("database")
            local_id = entry.get("id")
            curie = (
                f"{database}:{local_id}" if database and local_id is not None else None
            )
            xrefs.append(
                {
                    "database": database,
                    "id": local_id,
                    "curie": curie,
                    "url": entry.get("url"),
                    "description": entry.get("description"),
                }
            )

        return {
            "status": "success",
            "data": {
                "obo_id": term_data.get("obo_id") or identifier,
                "iri": term_data.get("iri"),
                "label": term_data.get("label"),
                "ontology_name": term_data.get("ontology_name")
                or term_data.get("ontologyName")
                or ontology,
                "is_obsolete": term_data.get("is_obsolete", False),
                "xrefs": xrefs,
            },
            "metadata": {
                "query_id": identifier,
                "ontology": ontology or None,
                "xref_count": len(xrefs),
            },
        }

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
        size = min(max(1, int(arguments.get("size", 20))), 1000)
        page = max(0, int(arguments.get("page") or 0))
        encoded = url_encode_iri(term_iri)

        params = {
            "page": page,
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
        page = max(0, int(arguments.get("page") or 0))
        encoded = url_encode_iri(term_iri)

        params = {
            "page": page,
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
            if isinstance(term_data, dict) and not term_data.get("label"):
                legacy_terms = self._format_term_collection(term_data, size)
                if "terms" in legacy_terms:
                    legacy_terms["term_iri"] = term_iri
                    legacy_terms["ontology"] = ontology
                    legacy_terms["note"] = (
                        "Returned terms from an OLS collection response; "
                        "source term label was not available."
                    )
                    return legacy_terms
            label = term_data.get("label", "")
            if isinstance(label, list):
                label = next(
                    (
                        value
                        for value in label
                        if isinstance(value, str) and value.strip()
                    ),
                    "",
                )
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

        # The first call fetched the whole source record and only `label` was
        # read from it. Among what was thrown away: whether the source term is
        # obsolete -- EFO:0000270 is, since 3.38.0 -- which decides whether
        # the similar terms are worth having at all.
        source_term = {
            "iri": term_iri,
            "label": label,
            "curie": term_data.get("curie") if isinstance(term_data, dict) else None,
            "definition": _as_string_list(
                (term_data or {}).get("definition")
                if isinstance(term_data, dict)
                else None
            ),
            "synonyms": _as_string_list(
                (term_data or {}).get("synonym") if isinstance(term_data, dict) else None
            ),
            "is_obsolete": (term_data or {}).get("isObsolete")
            if isinstance(term_data, dict)
            else None,
            "curated_from_sources": _as_string_list(
                (term_data or {}).get("curatedFromSources")
                if isinstance(term_data, dict)
                else None
            ),
            "curated_from": [
                {
                    "text": entry.get("text"),
                    "source": entry.get("source"),
                    "subject_categories": entry.get("subjectCategories") or [],
                }
                for entry in (
                    ((term_data or {}).get("curatedFrom") or [])
                    if isinstance(term_data, dict)
                    else []
                )[:CURATED_FROM_PER_TERM]
                if isinstance(entry, dict)
            ],
        }

        payload = {
            "term_iri": term_iri,
            "source_label": label,
            "source_term": source_term,
            "ontology": ontology,
            "similar_terms": similar,
            "total": len(similar),
            "note": "Results via text search (OLS v4 semantic similarity endpoint unavailable).",
        }
        return {"status": "success", "data": payload, **payload}

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

        page_info = data.get("page") if isinstance(data, dict) else None
        if not isinstance(page_info, dict) and isinstance(data, dict):
            # OLS4 v2 hierarchy endpoints currently return pagination fields at
            # the top level (`page`, `numElements`, `totalPages`,
            # `totalElements`), while some Spring-style OLS responses use a
            # nested `page` object. Normalize both layouts.
            if any(
                key in data
                for key in ("page", "numElements", "totalPages", "totalElements")
            ):
                page_info = {
                    "number": data.get("page", 0),
                    "size": data.get("numElements", size),
                    "totalPages": data.get("totalPages", 0),
                    "totalElements": data.get("totalElements", 0),
                }

        if not elements:
            # Keep the success shape stable for empty result sets. Returning the
            # raw upstream envelope here meant a leaf term answered with
            # `totalElements`/`elements` while a non-leaf answered with
            # `total_items`/`terms`, so callers reading `data["terms"]` broke on
            # exactly the queries that legitimately have no children.
            total = (
                page_info.get("totalElements", 0)
                if isinstance(page_info, dict)
                else data.get("totalElements", 0)
                if isinstance(data, dict)
                else 0
            )
            result: Dict[str, Any] = {
                "terms": [],
                "total_items": total,
                "showing": 0,
            }
            if isinstance(page_info, dict):
                current = page_info.get("number", 0)
                total_pages = page_info.get("totalPages", 0)
                has_more = current + 1 < total_pages
                result["pagination"] = {
                    "page": current,
                    "size": page_info.get("size", size),
                    "total_pages": total_pages,
                    "total_items": total,
                    "has_more": has_more,
                    "next_page": current + 1 if has_more else None,
                }
            return result

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

        if isinstance(page_info, dict):
            current = page_info.get("number", 0)
            total_pages = page_info.get("totalPages", 0)
            has_more = current + 1 < total_pages
            result["pagination"] = {
                "page": current,
                "size": page_info.get("size", len(limited)),
                "total_pages": total_pages,
                "total_items": page_info.get("totalElements", total),
                "has_more": has_more,
                "next_page": current + 1 if has_more else None,
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
            "description": _as_string_list(
                item.get("description") or item.get("definition")
            ),
            "synonyms": _as_string_list(
                item.get("exact_synonyms")
                or item.get("synonyms")
                or item.get("synonym")
            ),
            "related_synonyms": _as_string_list(item.get("related_synonyms")),
            "ontologyPrefix": item.get("ontology_prefix")
            or item.get("ontologyPrefix"),
            "type": item.get("type") if isinstance(item.get("type"), str) else None,
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
