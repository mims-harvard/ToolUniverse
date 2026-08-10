# hpo_tool.py
"""
Human Phenotype Ontology (HPO) API tool for ToolUniverse.

HPO provides a standardized vocabulary of phenotypic abnormalities
encountered in human disease. Each term describes a phenotypic
feature (sign, symptom, or finding) and is organized in a directed
acyclic graph (DAG) hierarchy.

API: https://ontology.jax.org/api/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

HPO_BASE_URL = "https://ontology.jax.org/api/hp"
HPO_ANNOTATION_URL = "https://ontology.jax.org/api/network/annotation"


def _normalize_hpo_id(term_id: str) -> str:
    """Normalize an HPO term id to the canonical colon CURIE 'HP:0001250'.

    Accepts the underscore form 'HP_0001250' (which OpenTargets and other tools
    emit, e.g. phenotypeHPO.id) and a bare numeric id '0001250'. Without this,
    'HP_0001250' failed the old `startswith("HP:")` check and was turned into
    'HP:HP_0001250', causing an HPO API 404 -- a cross-tool chaining break in the
    OpenTargets-phenotype -> HPO_get_term path a clinician follows."""
    tid = str(term_id).strip()
    # Underscore CURIE from OpenTargets et al. -> colon CURIE.
    if tid.upper().startswith("HP_"):
        tid = "HP:" + tid[3:]
    elif not tid.upper().startswith("HP:"):
        tid = f"HP:{tid}"
    # Canonicalize the prefix case ('hp:' -> 'HP:').
    return "HP:" + tid.split(":", 1)[1] if ":" in tid else tid


@register_tool("HPOTool")
class HPOTool(BaseTool):
    """
    Tool for querying the Human Phenotype Ontology (HPO) at JAX.

    HPO provides structured phenotype terms used in clinical genetics,
    rare disease research, and differential diagnosis. Each term has
    definitions, synonyms, cross-references, and hierarchical relationships.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "get_term")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the HPO API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"HPO API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to HPO API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"HPO API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying HPO: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate HPO endpoint."""
        if self.endpoint == "get_term":
            return self._get_term(arguments)
        elif self.endpoint == "search_terms":
            return self._search_terms(arguments)
        elif self.endpoint == "get_term_hierarchy":
            return self._get_term_hierarchy(arguments)
        elif self.endpoint == "get_associated_genes":
            return self._get_associations(arguments, "genes")
        elif self.endpoint == "get_associated_diseases":
            return self._get_associations(arguments, "diseases")
        elif self.endpoint == "get_disease_annotations":
            return self._get_disease_annotations(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _get_disease_annotations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get the full HPO annotation profile for a disease.

        Uses the JAX network-annotation endpoint keyed by a disease ID
        (OMIM/ORPHA/DECIPHER). Returns curated MAxO medical actions
        (treatments / management with TREATS / PREVENTS relations and the
        phenotypes they target), phenotypes grouped by body system, and
        associated genes.
        """
        disease_id = arguments.get("disease_id") or arguments.get("id", "")
        disease_id = str(disease_id).strip()
        if not disease_id:
            return {
                "status": "error",
                "error": (
                    "disease_id parameter is required "
                    "(e.g., 'OMIM:154700', 'ORPHA:558', 'DECIPHER:...')"
                ),
            }

        url = f"{HPO_ANNOTATION_URL}/{disease_id}"
        response = requests.get(url, timeout=self.timeout)
        if response.status_code == 404:
            return {
                "status": "error",
                "error": (
                    f"No HPO disease annotation found for '{disease_id}'. "
                    "Use an OMIM / ORPHA / DECIPHER disease ID "
                    "(e.g., 'OMIM:154700')."
                ),
            }
        response.raise_for_status()
        data = response.json()

        # --- Medical actions (MAxO curated treatments / management) ---
        medical_actions = []
        for ma in data.get("medicalActions") or []:
            if not isinstance(ma, dict):
                continue
            targets = []
            for t in ma.get("targets") or []:
                if isinstance(t, dict):
                    targets.append({"id": t.get("id"), "name": t.get("name")})
            medical_actions.append(
                {
                    "id": ma.get("id"),
                    "name": ma.get("name"),
                    "relations": ma.get("relations") or [],
                    "targets": targets,
                }
            )

        # --- Phenotypes grouped by body system ---
        categories = []
        raw_categories = data.get("categories") or {}
        if isinstance(raw_categories, dict):
            for system, phenotypes in raw_categories.items():
                pheno_list = []
                if isinstance(phenotypes, list):
                    for p in phenotypes:
                        if isinstance(p, dict):
                            meta = p.get("metadata") or {}
                            pheno_list.append(
                                {
                                    "id": p.get("id"),
                                    "name": p.get("name"),
                                    "frequency": meta.get("frequency") or None,
                                    "onset": meta.get("onset") or None,
                                }
                            )
                categories.append(
                    {
                        "body_system": system,
                        "phenotype_count": len(pheno_list),
                        "phenotypes": pheno_list,
                    }
                )
            categories.sort(key=lambda c: c["phenotype_count"], reverse=True)

        # --- Associated genes ---
        genes = []
        for g in data.get("genes") or []:
            if isinstance(g, dict):
                genes.append({"id": g.get("id"), "name": g.get("name")})

        disease = data.get("disease") or {}
        total_phenotypes = sum(c["phenotype_count"] for c in categories)

        return {
            "status": "success",
            "data": {
                "disease": {
                    "id": disease.get("id"),
                    "name": disease.get("name"),
                    "mondo_id": disease.get("mondoId"),
                    "description": disease.get("description"),
                },
                "medical_actions": medical_actions,
                "categories": categories,
                "genes": genes,
            },
            "metadata": {
                "source": "HPO (JAX Ontology) network annotation",
                "disease_id": disease.get("id") or disease_id,
                "total_medical_actions": len(medical_actions),
                "total_body_systems": len(categories),
                "total_phenotypes": total_phenotypes,
                "total_genes": len(genes),
            },
        }

    def _get_associations(self, arguments: Dict[str, Any], kind: str) -> Dict[str, Any]:
        """Get genes or diseases annotated to an HPO phenotype term.

        Uses the JAX network-annotation endpoint, which returns the genes,
        diseases, assays and medical actions linked to a phenotype in a
        single response (the endpoint itself has no server-side paging).
        """
        term_id = arguments.get("term_id", "")
        if not term_id:
            return {
                "status": "error",
                "error": "term_id parameter is required (e.g., 'HP:0001250')",
            }
        term_id = _normalize_hpo_id(term_id)

        try:
            limit = int(arguments.get("limit", 50))
        except (TypeError, ValueError):
            limit = 50
        limit = max(1, min(limit, 500))

        # Fix-19C-1/19C-2: a phenotype term can be linked to thousands of
        # genes/diseases (confirmed live: HP:0001263 "Global developmental
        # delay" has 2077 genes), but `limit` is capped at 500 and this
        # endpoint has no server-side paging -- previously the tool always
        # sliced from position 0, so well-known genes/diseases sorted past
        # position 500 by the API (e.g. SHANK3, MECP2 for that term) were
        # permanently unreachable with no way to page further. The full list
        # is already in memory from the one API call below, so paging is a
        # free client-side slice -- no extra round-trip needed.
        try:
            offset = int(arguments.get("offset", 0) or 0)
        except (TypeError, ValueError):
            offset = 0
        offset = max(0, offset)

        # The annotation endpoint lives under /api/network/, not /api/hp/.
        url = f"{HPO_ANNOTATION_URL}/{term_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        items = data.get(kind) or []
        total = len(items)
        trimmed = []
        for it in items[offset : offset + limit]:
            entry = {"id": it.get("id"), "name": it.get("name")}
            if kind == "diseases":
                entry["mondo_id"] = it.get("mondoId")
            trimmed.append(entry)

        return {
            "status": "success",
            "data": {kind: trimmed},
            "metadata": {
                "source": "HPO (JAX Ontology) network annotation",
                "term_id": term_id,
                "total": total,
                "offset": offset,
                "returned": len(trimmed),
                "has_more": offset + len(trimmed) < total,
            },
        }

    def _get_term(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information about an HPO term by its ID."""
        term_id = arguments.get("term_id", "")
        if not term_id:
            return {
                "status": "error",
                "error": "term_id parameter is required (e.g., 'HP:0001250')",
            }

        # Normalize the ID format (accepts HP:xxx, HP_xxx, and bare digits)
        term_id = _normalize_hpo_id(term_id)

        url = f"{HPO_BASE_URL}/terms/{term_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        result = {
            "id": data.get("id"),
            "name": data.get("name"),
            "definition": data.get("definition"),
            "comment": data.get("comment"),
            "synonyms": data.get("synonyms", []),
            "descendant_count": data.get("descendantCount"),
            "xrefs": data.get("xrefs", []),
        }

        # Extract translations if available
        translations = data.get("translations", [])
        if translations:
            result["translations"] = [
                {"language": t.get("language"), "name": t.get("name")}
                for t in translations[:5]
                if t and t.get("name")
            ]

        metadata = {
            "source": "HPO (JAX Ontology)",
            "term_id": term_id,
        }
        # The JAX ontology API silently resolves an obsolete/merged HPO ID to
        # its replacement term's record -- with no obsolescence flag anywhere
        # in the payload -- rather than 404ing or marking the response as a
        # redirect. Detect the ID mismatch ourselves and surface it, so a
        # caller doesn't mistake the replacement term's data for the term
        # they actually asked about (confirmed live: querying an obsolete ID
        # like HP:0006887 silently returns HP:0001249's full record).
        resolved_id = result["id"]
        if resolved_id and resolved_id != term_id:
            metadata["requested_id"] = term_id
            metadata["resolved_id"] = resolved_id
            metadata["note"] = (
                f"The requested term ID ({term_id}) differs from the "
                f"returned term's ID ({resolved_id}). This usually means "
                f"{term_id} is obsolete or was merged into {resolved_id} "
                "upstream. Use get_phenotype_by_HPO_ID for an explicit "
                "'deprecated' flag, or HPO_search_terms to find the "
                "current preferred term."
            )

        return {
            "status": "success",
            "data": result,
            "metadata": metadata,
        }

    def _search_terms(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for HPO terms by keyword."""
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        # Coerce max_results robustly: the schema allows integer|null, so a
        # caller may omit it, pass null, or pass an out-of-range value. Using
        # the raw value directly would crash on None (None > 50) and let
        # negatives/zero through.
        try:
            max_results = int(arguments.get("max_results") or 10)
        except (TypeError, ValueError):
            max_results = 10
        max_results = max(1, min(max_results, 50))

        url = f"{HPO_BASE_URL}/search"
        # The JAX ontology search endpoint sizes the page with `limit`. The
        # previous `max` key was silently ignored, capping every result set at
        # the API default of 10 regardless of the requested count.
        params = {"q": query, "limit": max_results}

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        # Defensive truncation in case an upstream change ever returns more
        # rows than requested.
        terms = data.get("terms", [])[:max_results]
        results = []
        for term in terms:
            results.append(
                {
                    "id": term.get("id"),
                    "name": term.get("name"),
                    "definition": term.get("definition"),
                    "descendant_count": term.get("descendantCount"),
                    "synonyms": term.get("synonyms", [])[:5],
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "HPO (JAX Ontology)",
                "query": query,
                "total_results": len(results),
                # Total matches available across all pages (the API reports this
                # as `totalCount`), so callers can see more terms exist beyond
                # the returned page instead of assuming this page is exhaustive.
                "total_available": data.get("totalCount", len(results)),
            },
        }

    def _get_term_hierarchy(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get parent and child terms in the HPO hierarchy."""
        term_id = arguments.get("term_id", "")
        if not term_id:
            return {
                "status": "error",
                "error": "term_id parameter is required (e.g., 'HP:0001250')",
            }

        term_id = _normalize_hpo_id(term_id)

        direction = arguments.get("direction", "children")

        url = f"{HPO_BASE_URL}/terms/{term_id}/{direction}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        results = []
        if isinstance(data, list):
            for term in data:
                results.append(
                    {
                        "id": term.get("id"),
                        "name": term.get("name"),
                    }
                )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "HPO (JAX Ontology)",
                "term_id": term_id,
                "direction": direction,
                "total_results": len(results),
            },
        }
