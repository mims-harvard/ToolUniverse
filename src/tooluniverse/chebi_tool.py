# chebi_tool.py
"""
ChEBI 2.0 REST API tool for ToolUniverse.

ChEBI (Chemical Entities of Biological Interest) is a freely available
dictionary of molecular entities focused on 'small' chemical compounds,
maintained by EMBL-EBI. It provides an ontology-based classification
system, cross-references to other chemical databases, and detailed
structural information for 195,000+ compounds.

API: https://www.ebi.ac.uk/chebi/backend/api/
No authentication required. Free for all use.
"""

import re
import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

CHEBI_BASE_URL = "https://www.ebi.ac.uk/chebi/backend/api/public"

# advanced_search is server-side paginated at 15 hits per page and exposes the
# page number as a 1-indexed query-string parameter (`?page=1` is the first
# page and is byte-identical to omitting the parameter; `?page=0` and any page
# beyond `number_pages` return a non-JSON error body). `limit` is clamped to
# 100, so at most ceil(100 / 15) == 7 pages are ever needed; the cap below is
# a hard stop that protects against a server that stops honouring `page`.
_SEARCH_PAGE_SIZE = 15
_SEARCH_MAX_PAGES = 8

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text):
    """Remove search-highlight markup (e.g. <em>...</em>) ChEBI embeds in
    name/synonym fields. Non-string values pass through unchanged."""
    if isinstance(text, str):
        return _HTML_TAG_RE.sub("", text)
    return text


def _normalize_chebi_id(chebi_id):
    """Accept the 'CHEBI:16113' CURIE that ChEBI_search / ChEBI_get_compound
    emit (chebi_accession) and reduce it to the bare id the ontology endpoints
    expect. Without this, chaining ChEBI_search -> ChEBI_get_ontology_parents
    broke: the ontology tools required a bare integer and rejected the prefixed
    accession the search hands back."""
    if isinstance(chebi_id, str):
        chebi_id = chebi_id.strip()
        if chebi_id.upper().startswith("CHEBI:"):
            chebi_id = chebi_id.split(":", 1)[1].strip()
    return chebi_id


@register_tool("ChEBITool")
class ChEBITool(BaseTool):
    """
    Tool for querying ChEBI (Chemical Entities of Biological Interest).

    Provides compound lookup, text search, and ontology navigation
    for small molecules of biological relevance.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "get_compound"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the ChEBI API call."""
        try:
            return self._dispatch(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"ChEBI API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to ChEBI API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"ChEBI API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying ChEBI: {str(e)}",
            }

    def _dispatch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint based on config."""
        if self.endpoint_type == "get_compound":
            return self._get_compound(arguments)
        elif self.endpoint_type == "search":
            return self._search(arguments)
        elif self.endpoint_type == "ontology_children":
            return self._ontology_children(arguments)
        elif self.endpoint_type == "ontology_parents":
            return self._ontology_parents(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown endpoint_type: {self.endpoint_type}",
            }

    def _get_compound(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed compound information by ChEBI ID."""
        chebi_id = arguments.get("chebi_id", None)
        if chebi_id is None:
            return {
                "status": "error",
                "error": "chebi_id parameter is required (e.g., 15365 for aspirin)",
            }

        # Accept the "CHEBI:27732" CURIE form that ChEBI_search returns as
        # chebi_accession, not just the bare integer — so the two tools chain
        # without the caller having to strip the prefix.
        if isinstance(chebi_id, str):
            chebi_id = chebi_id.strip()
            if chebi_id.upper().startswith("CHEBI:"):
                chebi_id = chebi_id.split(":", 1)[1].strip()

        url = f"{CHEBI_BASE_URL}/compound/{chebi_id}/"
        response = requests.get(
            url,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        raw = response.json()

        # Extract synonyms
        synonyms = []
        names_dict = raw.get("names", {})
        for name_type, name_list in names_dict.items():
            if isinstance(name_list, list):
                for entry in name_list[:10]:
                    if isinstance(entry, dict):
                        syn = _strip_html(entry.get("name", ""))
                        if syn and syn not in synonyms:
                            synonyms.append(syn)

        # Chemical data is nested under 'chemical_data'
        chem_data = raw.get("chemical_data", {})
        if not isinstance(chem_data, dict):
            chem_data = {}

        # Structure data is under 'default_structure'
        struct_data = raw.get("default_structure", {})
        if not isinstance(struct_data, dict):
            struct_data = {}

        # Parse mass as float if string
        mass_val = chem_data.get("mass", None)
        if isinstance(mass_val, str):
            try:
                mass_val = float(mass_val)
            except ValueError:
                mass_val = None

        mono_mass = chem_data.get("monoisotopic_mass", None)
        if isinstance(mono_mass, str):
            try:
                mono_mass = float(mono_mass)
            except ValueError:
                mono_mass = None

        result = {
            "chebi_id": raw.get("id", chebi_id),
            "chebi_accession": raw.get("chebi_accession", f"CHEBI:{chebi_id}"),
            "name": _strip_html(raw.get("name", "")),
            "definition": _strip_html(raw.get("definition", None)),
            "stars": raw.get("stars", 0),
            "formula": chem_data.get("formula", None),
            "mass": mass_val,
            "monoisotopic_mass": mono_mass,
            "charge": chem_data.get("charge", None),
            "smiles": struct_data.get("smiles", None),
            "inchikey": struct_data.get("standard_inchi_key", None),
            "synonyms": synonyms[:20],
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "ChEBI",
                "query": str(chebi_id),
                "endpoint": "compound",
            },
        }

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search ChEBI by name, formula, or keyword using advanced search."""
        query = arguments.get("query", "")
        limit = arguments.get("limit", 10)
        if not query:
            return {
                "status": "error",
                "error": "query parameter is required (e.g., 'glucose', 'caffeine')",
            }

        if limit is None:
            limit = 10
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 10
        limit = max(0, min(limit, 100))

        # Use advanced_search endpoint for better relevance
        url = f"{CHEBI_BASE_URL}/advanced_search/"
        payload = {
            "text_search_specification": {
                "or_specification": [{"text": query, "category": "all"}]
            },
            "stars": [2, 3],
        }
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        # The endpoint returns only one page (15 hits) per request, so a single
        # POST can never satisfy limit > 15. Walk successive pages until we have
        # `limit` compounds or the result set is exhausted.
        compounds = []
        total_matches = None
        number_pages = None
        page = 1
        pages_fetched = 0
        while page <= _SEARCH_MAX_PAGES:
            try:
                response = requests.post(
                    url,
                    json=payload,
                    params={"page": page},
                    headers=headers,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                raw = response.json()
            except Exception:
                # Never discard the pages already in hand: a failure while
                # fetching page N > 1 degrades to "fewer results than asked
                # for", not to an error. Only a failed first page is fatal.
                if page == 1:
                    raise
                break

            pages_fetched += 1

            if not isinstance(raw, dict):
                break

            # `total` / `number_pages` are informational and may be absent on
            # some responses; fall back to single-page behaviour rather than
            # crashing or looping forever.
            if total_matches is None and isinstance(raw.get("total"), int):
                total_matches = raw["total"]
            if number_pages is None and isinstance(raw.get("number_pages"), int):
                number_pages = raw["number_pages"]

            results = raw.get("results", [])
            if not isinstance(results, list):
                results = []

            for hit in results:
                source = hit.get("_source", {}) if isinstance(hit, dict) else {}
                if not isinstance(source, dict):
                    source = {}
                compounds.append(
                    {
                        "chebi_accession": source.get("chebi_accession", ""),
                        # Strip HTML tags from name (ChEBI stores
                        # stereochemistry as HTML).
                        "name": _strip_html(source.get("name", "")),
                        "formula": source.get("formula", None),
                        "mass": source.get("mass", None),
                        "stars": source.get("stars", None),
                    }
                )

            if len(compounds) >= limit:
                break
            if not results:
                break
            if number_pages is not None:
                if page >= number_pages:
                    break
            elif len(results) < _SEARCH_PAGE_SIZE:
                # No page metadata and a short page: this was the last one.
                break
            page += 1

        compounds = compounds[:limit]

        result = {
            "query": query,
            # `result_count` keeps its original meaning: how many compounds are
            # in `compounds`. `total_matches` is how many the query matches in
            # ChEBI overall, so a caller can distinguish "10 of 116" from
            # "10 exist". It is None when the API omits the count.
            "result_count": len(compounds),
            "total_matches": total_matches,
            "compounds": compounds,
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "ChEBI",
                "query": query,
                "endpoint": "advanced_search",
                "pages_fetched": pages_fetched,
            },
        }

    def _ontology_children(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get ontology children of a ChEBI compound."""
        chebi_id = arguments.get("chebi_id", None)
        if chebi_id is None:
            return {
                "status": "error",
                "error": "chebi_id parameter is required (e.g., 15365 for aspirin)",
            }

        chebi_id = _normalize_chebi_id(chebi_id)
        url = f"{CHEBI_BASE_URL}/ontology/children/{chebi_id}/"
        response = requests.get(
            url,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        raw = response.json()

        # Extract relations
        relations = []
        ontology = raw.get("ontology_relations", {})
        incoming = ontology.get("incoming_relations", [])
        if isinstance(incoming, list):
            for rel in incoming:
                relations.append(
                    {
                        "child_id": rel.get("init_id", 0),
                        "child_name": rel.get("init_name", ""),
                        "relation_type": rel.get("relation_type", ""),
                        "parent_id": rel.get("final_id", 0),
                        "parent_name": rel.get("final_name", ""),
                    }
                )

        result = {
            "chebi_id": raw.get("id", chebi_id),
            "chebi_accession": raw.get("chebi_accession", f"CHEBI:{chebi_id}"),
            "relation_count": len(relations),
            "relations": relations,
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "ChEBI",
                "query": str(chebi_id),
                "endpoint": "ontology/children",
            },
        }

    def _ontology_parents(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get ontology parents (is-a / has-role ancestors) of a ChEBI compound."""
        chebi_id = arguments.get("chebi_id", None)
        if chebi_id is None:
            return {
                "status": "error",
                "error": "chebi_id parameter is required (e.g., 15377 for water)",
            }

        chebi_id = _normalize_chebi_id(chebi_id)
        url = f"{CHEBI_BASE_URL}/ontology/parents/{chebi_id}/"
        response = requests.get(
            url,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        raw = response.json()

        # Parents are the targets of outgoing_relations (the symmetric
        # counterpart of the children tool's incoming_relations).
        relations = []
        ontology = raw.get("ontology_relations", {})
        outgoing = ontology.get("outgoing_relations", [])
        if isinstance(outgoing, list):
            for rel in outgoing:
                relations.append(
                    {
                        "relation_type": rel.get("relation_type", ""),
                        "parent_id": rel.get("final_id", 0),
                        "parent_name": _strip_html(rel.get("final_name", "")),
                    }
                )

        result = {
            "chebi_id": raw.get("id", chebi_id),
            "chebi_accession": raw.get("chebi_accession", f"CHEBI:{chebi_id}"),
            "relation_count": len(relations),
            "relations": relations,
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "ChEBI",
                "query": str(chebi_id),
                "endpoint": "ontology/parents",
            },
        }
