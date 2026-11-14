# monarch_v3_tool.py
"""
Monarch Initiative V3 API tool for ToolUniverse.

The Monarch Initiative integrates gene, disease, and phenotype data
from multiple organisms to support biomedical discovery. The V3 API
provides access to a knowledge graph linking genes, diseases, phenotypes,
and variants across species.

API: https://api.monarchinitiative.org/v3/api/
No authentication required. Free public access.
"""

import re
from typing import Dict, Any, Optional

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

MONARCH_BASE_URL = "https://api.monarchinitiative.org/v3/api"

# OLS4 carries the `term replaced by` annotation that Monarch's own payload
# omits, so an obsolete term can point at its replacement instead of being a
# dead end. Only consulted for terms Monarch has already marked deprecated.
_OLS4_TERMS_URL = "https://www.ebi.ac.uk/ols4/api/ontologies/{ontology}/terms"
_OBO_IRI = "http://purl.obolibrary.org/obo/{term}"

_UNDERSCORE_CURIE_RE = re.compile(r"^([A-Za-z]+)_(\d+)$")


def _is_deprecated(payload: Dict[str, Any]) -> bool:
    """Monarch reports live terms as `deprecated: None`, not `False`."""
    return bool(payload.get("deprecated"))


def _replaced_by(curie: str, timeout: int) -> Optional[str]:
    """Resolve the MONDO term an obsolete CURIE was replaced by, or None.

    Monarch keeps obsolete terms queryable but strips their content, so
    `Mondo_get_disease` on one returns an empty record that looks like a
    disease with no annotations. The replacement is recorded in the source
    ontology, which OLS4 exposes.

    MONDO only: the OBO PURL built below is wrong by construction for the
    other prefixes that reach `_normalize_curie` -- Orphanet lives at
    `orpha.net/ORDO/` under the OLS4 ontology `ordo`, EFO at
    `ebi.ac.uk/efo/`, and OMIM is not an OLS4 ontology at all -- so
    querying for them would spend a request to learn nothing.
    """
    prefix, _, local = curie.partition(":")
    if not local or prefix.upper() != "MONDO":
        return None
    try:
        response = requests.get(
            _OLS4_TERMS_URL.format(ontology=prefix.lower()),
            params={"iri": _OBO_IRI.format(term=f"{prefix.upper()}_{local}")},
            headers={"Accept": "application/json"},
            timeout=timeout,
        )
        response.raise_for_status()
        terms = response.json().get("_embedded", {}).get("terms") or []
    except Exception:
        return None

    for term in terms:
        replacement = term.get("term_replaced_by")
        if replacement:
            return str(replacement).rsplit("/", 1)[-1].replace("_", ":", 1)
    return None


def _deprecation_metadata(
    curie: str, empty_clause: str, timeout: int
) -> Dict[str, Any]:
    """The `deprecated`/`replaced_by`/note trio for a known-obsolete CURIE.

    `empty_clause` names whatever the caller is about to hand back empty, verb
    included, so one wording serves both a stripped record ("the empty fields
    above mean") and a stripped result set ("this empty result means").
    Capped below the caller's timeout: the answer it accompanies is already
    complete, so a slow OLS4 must not stall it.
    """
    replacement = _replaced_by(curie, min(timeout, 10))
    next_step = (
        f"Re-query {replacement} for the current term."
        if replacement
        else "No replacement term is recorded; search by name for the current term."
    )
    return {
        "deprecated": True,
        "replaced_by": replacement,
        "deprecation_note": (
            f"{curie} is an obsolete Mondo term. Monarch strips the annotations "
            f"of obsolete terms, so {empty_clause} 'not recorded here', not "
            f"'none exist'. {next_step}"
        ),
    }


def _obsolescence_metadata(curie: str, timeout: int) -> Dict[str, Any]:
    """Deprecation metadata for an empty result set, or {} if there is none.

    `_mondo_get_disease` reads `deprecated` off the record it already has, but
    these endpoints return rows and nothing else -- so obsolescence has to be
    asked for separately, which is why this probes /entity. Silent for live
    terms, non-MONDO CURIEs and probe failures.
    """
    if not curie.upper().startswith("MONDO:"):
        return {}
    try:
        response = requests.get(
            f"{MONARCH_BASE_URL}/entity/{curie}", timeout=min(timeout, 10)
        )
        response.raise_for_status()
        if not _is_deprecated(response.json()):
            return {}
    except Exception:
        return {}

    return _deprecation_metadata(curie, "this empty result means", timeout)


# Biolink association categories are directed: the category name reads
# "<subject>To<object>Association". Anchoring an entity on the wrong side is
# silently valid at the API (it just matches nothing), so a caller asking
# "which genes cause MONDO:0006559?" as subject=MONDO:0006559 gets a confident
# empty list rather than the three causal genes the object side would return.
# Map each category to the kind of entity that belongs on each side so an empty
# result can say which side the caller's CURIE actually belongs on.
_ASSOCIATION_SIDES = {
    "biolink:CausalGeneToDiseaseAssociation": ("gene", "disease"),
    "biolink:CorrelatedGeneToDiseaseAssociation": ("gene", "disease"),
    "biolink:GeneToPhenotypicFeatureAssociation": ("gene", "phenotype"),
    "biolink:DiseaseToPhenotypicFeatureAssociation": ("disease", "phenotype"),
    "biolink:GeneToPathwayAssociation": ("gene", "pathway"),
    "biolink:GeneToExpressionSiteAssociation": ("gene", "expression site"),
}

# Only unambiguous CURIE prefixes -- enough to recognise a disease passed where
# a gene belongs (and vice versa) without guessing about multi-purpose
# namespaces such as MGI/ZFIN, which identify both genes and genotypes.
_CURIE_PREFIX_KIND = {
    "HGNC": "gene",
    "NCBIGENE": "gene",
    "ENSEMBL": "gene",
    "MONDO": "disease",
    "OMIM": "disease",
    "DOID": "disease",
    "ORPHANET": "disease",
    "HP": "phenotype",
}


def _curie_kind(curie: str) -> str:
    """Best-effort entity kind for a CURIE, or '' when the prefix is ambiguous."""
    if not isinstance(curie, str) or ":" not in curie:
        return ""
    return _CURIE_PREFIX_KIND.get(curie.split(":", 1)[0].strip().upper(), "")


def _direction_hint(category: str, subject: str, obj: str) -> str:
    """Explain the subject/object direction when a query returned nothing and
    the supplied CURIE looks like it belongs on the other side."""
    sides = _ASSOCIATION_SIDES.get(category)
    if not sides:
        return ""
    subject_kind, object_kind = sides
    if subject_kind == object_kind:
        return ""
    preamble = (
        f"{category} is directed: the {subject_kind} is the 'subject' "
        f"and the {object_kind} is the 'object'."
    )
    if subject and not obj and _curie_kind(subject) == object_kind:
        return (
            f"{preamble} You passed {subject} (a {object_kind}) as 'subject'; "
            f"retry with object='{subject}' to get its {subject_kind}s."
        )
    if obj and not subject and _curie_kind(obj) == subject_kind:
        return (
            f"{preamble} You passed {obj} (a {subject_kind}) as 'object'; "
            f"retry with subject='{obj}' to get its {object_kind}s."
        )
    return ""


def _normalize_curie(entity_id: str) -> str:
    """Convert an underscore-delimited ontology CURIE to the colon form Monarch
    requires. OpenTargets and other tools emit 'MONDO_0004995' / 'EFO_0008572' /
    'Orphanet_238583', but Monarch's /entity endpoint 404s on those and needs
    'MONDO:0004995'. Feeding one tool's output into Mondo_get_disease broke with
    a bare 404 that never revealed the delimiter was the cause."""
    if not isinstance(entity_id, str):
        return entity_id
    stripped = entity_id.strip()
    m = _UNDERSCORE_CURIE_RE.match(stripped)
    return f"{m.group(1)}:{m.group(2)}" if m else stripped


def _search_row(item: Dict[str, Any]) -> Dict[str, Any]:
    """One hit of Monarch's /search endpoint.

    Both search handlers in this module call that one endpoint and used to
    build their own row from it: the general one kept fifteen fields and the
    Mondo one six, so a disease search lost the score that orders the hits,
    the match_type that says whether the name or a synonym matched, the
    synonyms themselves, the namespace and who asserted the record. Same
    endpoint, same row.
    """
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "category": item.get("category"),
        "symbol": item.get("symbol"),
        "description": item.get("description"),
        "taxon": item.get("in_taxon"),
        "taxon_label": item.get("in_taxon_label"),
        "deprecated": _is_deprecated(item),
        # The order the hits come back in, and who asserted each one. A
        # search that returns ten rows and no score gives no way to tell
        # the best match from the tenth.
        "score": item.get("score"),
        "provided_by": item.get("provided_by"),
        "namespace": item.get("namespace"),
        "synonyms": item.get("synonym") or [],
        "xrefs": item.get("xref") or [],
        # Whether the row matched on the name, a synonym or the
        # description, which is what separates an exact hit from a text
        # match deep in a description.
        "match_type": item.get("match_type"),
    }


@register_tool("MonarchV3Tool")
class MonarchV3Tool(BaseTool):
    """
    Tool for querying the Monarch Initiative V3 knowledge graph.

    Monarch provides integrated data linking genes, diseases, phenotypes,
    and model organisms. The V3 API supports entity lookup, association
    queries, and cross-species phenotype comparisons. Data sources include
    OMIM, ClinVar, HPO, MGI, ZFIN, FlyBase, WormBase, and others.

    Supports: entity lookup, phenotype associations, disease-gene associations.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "entity")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Monarch V3 API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Monarch API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to Monarch Initiative API",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"Monarch API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying Monarch: {str(e)}",
            }

    def _rows(self, rows: list, metadata: Dict[str, Any], curie: str) -> Dict[str, Any]:
        """Envelope a row-returning endpoint, disclosing an obsolete CURIE.

        Nothing distinguishes "obsolete, so stripped" from "live, but nothing
        recorded" in a bare empty list, so every such endpoint asks the same
        question on the same condition.
        """
        if not rows:
            metadata.update(_obsolescence_metadata(curie, self.timeout))
        return {"status": "success", "data": rows, "metadata": metadata}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate Monarch V3 endpoint."""
        handlers = {
            "entity": self._get_entity,
            "associations": self._get_associations,
            "search": self._search,
            "mondo_search": self._mondo_search,
            "mondo_disease": self._mondo_get_disease,
            "mondo_phenotypes": self._mondo_get_phenotypes,
            "histopheno": self._histopheno,
            "mappings": self._get_mappings,
            "semsim_search": self._semsim_search,
            "semsim_compare": self._semsim_compare,
        }
        handler = handlers.get(self.endpoint)
        if handler:
            return handler(arguments)
        return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    @staticmethod
    def _pagination(arguments: Dict[str, Any], default: int, maximum: int):
        limit = arguments.get("limit", default)
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= maximum
        ):
            return (
                None,
                None,
                {
                    "status": "error",
                    "error": f"limit must be an integer between 1 and {maximum}",
                    "parameter": "limit",
                },
            )
        offset = arguments.get("offset", 0)
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            return (
                None,
                None,
                {
                    "status": "error",
                    "error": "offset must be a non-negative integer",
                    "parameter": "offset",
                },
            )
        return limit, offset, None

    @staticmethod
    def _pagination_metadata(data: Any, returned: int, limit: int, offset: int):
        total = data.get("total") if isinstance(data, dict) else None
        total_is_exact = (
            isinstance(total, int) and not isinstance(total, bool) and total >= 0
        )
        if not total_is_exact:
            total = None
        has_more = offset + returned < total if total_is_exact else None
        truncated = offset > 0 or has_more is True or not total_is_exact
        return {
            "total_results": total,
            "total_results_is_exact": total_is_exact,
            "returned": returned,
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
            "next_offset": offset + returned if has_more and returned else None,
            "truncated": truncated,
            "result_set_complete": not truncated,
        }

    def _get_entity(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed entity information by CURIE identifier."""
        entity_id = _normalize_curie(
            arguments.get("entity_id") or arguments.get("id", "")
        )
        if not entity_id:
            return {
                "status": "error",
                "error": "id parameter is required (e.g., HGNC:11998, MONDO:0005148, HP:0001250)",
            }

        url = f"{MONARCH_BASE_URL}/entity/{entity_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        return {
            "status": "success",
            "data": {
                "id": data.get("id"),
                "name": data.get("name"),
                "full_name": data.get("full_name"),
                "category": data.get("category"),
                "description": data.get("description"),
                "symbol": data.get("symbol"),
                "synonyms": data.get("synonym", []),
                "xrefs": data.get("xref", []),
                "taxon": data.get("in_taxon"),
                "taxon_label": data.get("in_taxon_label"),
                "provided_by": data.get("provided_by"),
                "deprecated": _is_deprecated(data),
                # What the entity is linked to. The response carries 41
                # phenotype curies with their labels for a disease, and an
                # entity lookup that returns a name and a description and none
                # of them is a stub of the record.
                "has_phenotype": data.get("has_phenotype") or [],
                "has_phenotype_label": data.get("has_phenotype_label") or [],
                # How much of each kind of association the entity has, which
                # is how a caller decides which follow-up call is worth making.
                "association_counts": [
                    {
                        "label": count.get("label"),
                        "category": count.get("category"),
                        "count": count.get("count"),
                    }
                    for count in (data.get("association_counts") or [])
                    if isinstance(count, dict)
                ],
                "iri": data.get("iri"),
                "inheritance": data.get("inheritance"),
                # For a gene entity, the diseases it causes -- the single most
                # asked-for fact about a gene, present in the same response.
                "causes_disease": [
                    {
                        "id": entry.get("id"),
                        "name": entry.get("name"),
                        "category": entry.get("category"),
                    }
                    for entry in (data.get("causes_disease") or [])
                    if isinstance(entry, dict)
                ],
                "node_relationships": [
                    {
                        "relation": rel.get("relation"),
                        "relation_label": rel.get("relation_label"),
                        "related_entity_id": (rel.get("related_entity") or {}).get(
                            "id"
                        ),
                        "related_entity_name": (rel.get("related_entity") or {}).get(
                            "name"
                        ),
                    }
                    for rel in (data.get("node_relationships") or [])
                    if isinstance(rel, dict)
                ],
            },
            "metadata": {
                "source": "Monarch Initiative V3",
            },
        }

    def _get_associations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get associations for an entity with optional filtering by category."""
        subject = _normalize_curie(arguments.get("subject", ""))
        obj = _normalize_curie(arguments.get("object", ""))
        if not subject and not obj:
            return {
                "status": "error",
                "error": (
                    "At least one of 'subject' or 'object' is required (a CURIE). "
                    "Associations are directed: use 'subject' for the entity on the "
                    "left of the category (e.g. subject='HGNC:11998' with "
                    "biolink:CausalGeneToDiseaseAssociation for a gene's diseases) "
                    "and 'object' for the entity on the right (e.g. "
                    "object='MONDO:0005148' with the same category for a disease's "
                    "causal genes)."
                ),
            }

        category = arguments.get("category", "")
        limit, offset, pagination_error = self._pagination(arguments, 20, 200)
        if pagination_error is not None:
            return pagination_error

        url = f"{MONARCH_BASE_URL}/association/all"
        params = {"limit": limit, "offset": offset}
        if subject:
            params["subject"] = subject
        if obj:
            params["object"] = obj
        if category:
            params["category"] = category

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        associations = []
        for item in data.get("items", []):
            associations.append(
                {
                    "subject": item.get("subject"),
                    "subject_label": item.get("subject_label"),
                    "object": item.get("object"),
                    "object_label": item.get("object_label"),
                    "category": item.get("category"),
                    "predicate": item.get("predicate"),
                    "negated": item.get("negated"),
                    "provided_by": item.get("provided_by"),
                    "primary_knowledge_source": item.get("primary_knowledge_source"),
                    # Biolink records HOW an association was arrived at, and
                    # none of it reached the caller. `knowledge_level`
                    # separates a curated assertion from a prediction and
                    # `agent_type` a human curator from an automated pipeline;
                    # an agent weighing evidence cannot tell those apart from
                    # the subject, object and predicate alone.
                    "knowledge_level": item.get("knowledge_level"),
                    "agent_type": item.get("agent_type"),
                    "aggregator_knowledge_source": item.get(
                        "aggregator_knowledge_source"
                    )
                    or [],
                    "publications": item.get("publications") or [],
                    "evidence_count": item.get("evidence_count"),
                    "frequency_qualifier": item.get("frequency_qualifier"),
                    # How often the phenotype occurs in the disease. HPO
                    # annotations carry it as a percentage and as the raw
                    # quotient; a disease-phenotype row without it says only
                    # that the phenotype has been seen at all.
                    "has_percentage": item.get("has_percentage"),
                    "has_quotient": item.get("has_quotient"),
                    "has_count": item.get("has_count"),
                    "has_total": item.get("has_total"),
                    "onset_qualifier": item.get("onset_qualifier"),
                    "sex_qualifier": item.get("sex_qualifier"),
                    "disease_context_qualifier": item.get("disease_context_qualifier"),
                    "association_id": item.get("id"),
                    # The subject as the source database wrote it, before
                    # Monarch normalised the curie, and what kind of thing
                    # each end is. A row whose subject came back as an
                    # equivalent id is otherwise indistinguishable from one
                    # that matched exactly.
                    "original_subject": item.get("original_subject"),
                    "original_object": item.get("original_object"),
                    "subject_category": item.get("subject_category"),
                    "object_category": item.get("object_category"),
                    "subject_taxon": item.get("subject_taxon"),
                    "subject_taxon_label": item.get("subject_taxon_label"),
                }
            )

        metadata = self._pagination_metadata(data, len(associations), limit, offset)
        metadata.update(
            {
                "source": "Monarch Initiative V3",
                "subject": subject,
                "object": obj,
                "category": category,
            }
        )
        if not associations:
            hint = _direction_hint(category, subject, obj)
            if hint:
                metadata["note"] = hint
            metadata.update(_obsolescence_metadata(subject or obj, self.timeout))

        return {
            "status": "success",
            "data": associations,
            "metadata": metadata,
        }

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search Monarch knowledge graph for entities by name/keyword."""
        query = arguments.get("query") or arguments.get("q", "")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        limit, offset, pagination_error = self._pagination(arguments, 10, 50)
        if pagination_error is not None:
            return pagination_error
        category = arguments.get("category")

        url = f"{MONARCH_BASE_URL}/search"
        params = {
            "q": query,
            "limit": limit,
            "offset": offset,
        }
        if category:
            params["category"] = category

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        results = [_search_row(item) for item in data.get("items", [])]

        metadata = self._pagination_metadata(data, len(results), limit, offset)
        metadata.update(
            {
                "source": "Monarch Initiative V3",
                "query": query,
                "category": category,
            }
        )
        return {
            "status": "success",
            "data": results,
            "metadata": metadata,
        }

    # --- Mondo Disease Ontology specific endpoints ---

    def _mondo_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for diseases in the Mondo Disease Ontology via Monarch."""
        query = arguments.get("query", "").strip()
        if not query:
            return {
                "status": "error",
                "error": "query parameter is required (e.g., 'Alzheimer', 'breast cancer', 'diabetes')",
            }

        limit, offset, pagination_error = self._pagination(arguments, 10, 50)
        if pagination_error is not None:
            return pagination_error

        url = f"{MONARCH_BASE_URL}/search"
        params = {
            "q": query,
            "category": "biolink:Disease",
            "limit": limit,
            "offset": offset,
        }

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        # `xref` was this handler's name for the same list the general
        # search calls `xrefs`; both are returned so neither caller breaks.
        results = []
        for item in data.get("items", []):
            row = _search_row(item)
            row["xref"] = row["xrefs"]
            results.append(row)

        metadata = self._pagination_metadata(data, len(results), limit, offset)
        metadata.update(
            {
                "source": "Mondo Disease Ontology (via Monarch Initiative V3)",
                "query": query,
                "category": "biolink:Disease",
            }
        )
        return {
            "status": "success",
            "data": results,
            "metadata": metadata,
        }

    def _mondo_get_disease(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed Mondo disease information including hierarchy and cross-references."""
        disease_id = _normalize_curie(arguments.get("disease_id", ""))
        if not disease_id:
            return {
                "status": "error",
                "error": "disease_id parameter is required (e.g., MONDO:0004975, MONDO:0005148)",
            }

        url = f"{MONARCH_BASE_URL}/entity/{disease_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        category = data.get("category", "")
        if category and "Disease" not in category:
            return {
                "status": "error",
                "error": f"Entity {disease_id} is not a disease (category: {category})",
            }

        hierarchy = data.get("node_hierarchy", {})
        parent_diseases = []
        if hierarchy and isinstance(hierarchy, dict):
            for parent in hierarchy.get("super_classes", []):
                if isinstance(parent, dict):
                    parent_diseases.append(
                        {"id": parent.get("id"), "name": parent.get("name")}
                    )

        mappings = []
        for m in data.get("mappings", []) or []:
            if isinstance(m, dict):
                mappings.append({"id": m.get("id"), "url": m.get("url")})

        assoc_counts = {}
        for ac in data.get("association_counts", []) or []:
            if isinstance(ac, dict):
                assoc_counts[ac.get("label", "")] = ac.get("count", 0)

        raw_genes = data.get("causal_gene", []) or []
        causal_genes = []
        for gene in raw_genes:
            if isinstance(gene, dict):
                causal_genes.append({"id": gene.get("id"), "name": gene.get("name")})
            elif isinstance(gene, str):
                causal_genes.append({"id": gene, "name": None})

        raw_inheritance = data.get("inheritance")
        if isinstance(raw_inheritance, dict):
            inheritance = {
                "id": raw_inheritance.get("id"),
                "name": raw_inheritance.get("name"),
            }
        elif isinstance(raw_inheritance, str):
            inheritance = {"id": None, "name": raw_inheritance}
        else:
            inheritance = None

        # Monarch keeps obsolete terms queryable but strips their content, so
        # without this an obsolete ID returns a fully populated-looking record
        # whose every field is empty -- indistinguishable from a live disease
        # that simply has no annotations yet.
        deprecated = _is_deprecated(data)
        result = {
            "status": "success",
            "data": {
                "id": data.get("id"),
                "name": data.get("name"),
                "description": data.get("description"),
                "synonyms": data.get("synonym", []),
                "xrefs": data.get("xref", []),
                "mappings": mappings,
                "parent_diseases": parent_diseases,
                "subtypes_count": len(data.get("has_descendant", []) or []),
                "causal_genes": causal_genes,
                "inheritance": inheritance,
                "association_counts": assoc_counts,
                "deprecated": deprecated,
            },
            "metadata": {
                "source": "Mondo Disease Ontology (via Monarch Initiative V3)",
                "disease_id": disease_id,
            },
        }

        if deprecated:
            # `deprecated` is already known from the record above, so unlike the
            # row endpoints this needs no /entity probe -- only the note.
            disclosure = _deprecation_metadata(
                disease_id, "the empty fields above mean", self.timeout
            )
            result["data"]["replaced_by"] = disclosure["replaced_by"]
            result["metadata"]["deprecation_note"] = disclosure["deprecation_note"]

        return result

    def _mondo_get_phenotypes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get HPO phenotypes associated with a Mondo disease."""
        disease_id = _normalize_curie(arguments.get("disease_id", ""))
        if not disease_id:
            return {
                "status": "error",
                "error": "disease_id parameter is required (e.g., MONDO:0004975, MONDO:0005148)",
            }

        limit, offset, pagination_error = self._pagination(arguments, 20, 200)
        if pagination_error is not None:
            return pagination_error

        url = f"{MONARCH_BASE_URL}/association"
        params = {
            "subject": disease_id,
            "category": "biolink:DiseaseToPhenotypicFeatureAssociation",
            "limit": limit,
            "offset": offset,
        }

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        phenotypes = []
        for item in data.get("items", []):
            phenotypes.append(
                {
                    "phenotype_id": item.get("object"),
                    "phenotype_name": item.get("object_label"),
                    "disease_subtype": item.get("subject_label"),
                    "disease_subtype_id": item.get("subject"),
                    "predicate": item.get("predicate"),
                    "negated": item.get("negated"),
                    "primary_knowledge_source": item.get("primary_knowledge_source"),
                    # How often the phenotype occurs in the disease. This is
                    # the content of an HPO annotation: an obligate feature
                    # and an occasional one are not the same claim, and
                    # without it they arrive as identical rows.
                    "frequency_id": item.get("frequency_qualifier"),
                    "frequency": item.get("frequency_qualifier_label"),
                    "observed_count": item.get("has_count"),
                    "observed_total": item.get("has_total"),
                    "observed_percentage": item.get("has_percentage"),
                    # When it appears, and in whom.
                    "onset_id": item.get("onset_qualifier"),
                    "onset": item.get("onset_qualifier_label"),
                    "sex": item.get("sex_qualifier_label") or item.get("sex_qualifier"),
                    # What the claim rests on. knowledge_level separates a
                    # curated assertion from a prediction, and agent_type says
                    # whether a human made it.
                    "evidence": item.get("has_evidence"),
                    "knowledge_level": item.get("knowledge_level"),
                    "agent_type": item.get("agent_type"),
                    "publications": item.get("publications"),
                }
            )

        metadata = self._pagination_metadata(data, len(phenotypes), limit, offset)
        metadata["total_phenotypes"] = metadata["total_results"]
        metadata.update(
            {
                "source": "Mondo Disease Ontology (via Monarch Initiative V3)",
                "disease_id": disease_id,
            }
        )
        return self._rows(rows=phenotypes, metadata=metadata, curie=disease_id)

    # --- Additional Monarch V3 endpoints ---

    def _histopheno(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get phenotype counts by body system for a disease."""
        entity_id = _normalize_curie(arguments.get("entity_id", ""))
        if not entity_id:
            return {
                "status": "error",
                "error": "entity_id is required (e.g., MONDO:0007947 for Marfan syndrome)",
            }

        url = f"{MONARCH_BASE_URL}/histopheno/{entity_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        items = []
        for item in data.get("items", []):
            count = item.get("count", 0)
            if count > 0:
                items.append(
                    {
                        "body_system": item.get("label"),
                        "phenotype_count": count,
                        "id": item.get("id"),
                    }
                )
        items.sort(key=lambda x: x["phenotype_count"], reverse=True)

        metadata = {
            "source": "Monarch Initiative V3 - Histopheno",
            "entity_id": data.get("id", entity_id),
            "total_systems_with_phenotypes": len(items),
        }
        return self._rows(rows=items, metadata=metadata, curie=entity_id)

    def _get_mappings(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get cross-ontology mappings for an entity."""
        entity_id = _normalize_curie(arguments.get("entity_id", ""))
        if not entity_id:
            return {
                "status": "error",
                "error": "entity_id is required (e.g., MONDO:0005148 for type 2 diabetes)",
            }

        limit, offset, pagination_error = self._pagination(arguments, 20, 100)
        if pagination_error is not None:
            return pagination_error

        url = f"{MONARCH_BASE_URL}/mappings"
        params = {"entity_id": entity_id, "limit": limit, "offset": offset}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        mappings = []
        for item in data.get("items", []):
            mappings.append(
                {
                    "subject_id": item.get("subject_id"),
                    "subject_label": item.get("subject_label"),
                    "predicate": item.get("predicate_id"),
                    "object_id": item.get("object_id"),
                    "object_label": item.get("object_label"),
                    "mapping_source": item.get("mapping_source"),
                    # SSSOM's `mapping_justification` is the difference
                    # between a mapping a curator asserted
                    # (ManualMappingCuration) and one a string match produced
                    # (LexicalMatching). Returning the pair and the predicate
                    # without it presents both as the same fact.
                    "mapping_justification": item.get("mapping_justification"),
                    "mapping_id": item.get("id"),
                    "mapping_provider": item.get("mapping_provider"),
                    "confidence": item.get("confidence"),
                }
            )

        metadata = self._pagination_metadata(data, len(mappings), limit, offset)
        metadata["total_mappings"] = metadata["total_results"]
        metadata.update(
            {
                "source": "Monarch Initiative V3 - Mappings",
                "entity_id": entity_id,
            }
        )
        return self._rows(rows=mappings, metadata=metadata, curie=entity_id)

    def _semsim_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for diseases matching a set of phenotypes using semantic similarity."""
        phenotypes = arguments.get("phenotypes", [])
        if not phenotypes or not isinstance(phenotypes, list):
            return {
                "status": "error",
                "error": "phenotypes list is required (e.g., ['HP:0001250', 'HP:0001249'])",
            }

        group = arguments.get("group", "Human Diseases")
        limit = arguments.get("limit") or 10

        url = f"{MONARCH_BASE_URL}/semsim/search"
        payload = {
            "termset": phenotypes,
            "group": group,
            "limit": min(limit, 50),
        }

        response = requests.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        results = []
        for item in data if isinstance(data, list) else []:
            subject = item.get("subject", {})
            similarity = item.get("similarity", {})
            results.append(
                {
                    "disease_id": subject.get("id"),
                    "disease_name": subject.get("name"),
                    # The matched term's own cross-references and synonyms,
                    # which is how a hit is carried into another ontology.
                    "disease_category": subject.get("category"),
                    "disease_iri": subject.get("iri"),
                    "disease_xrefs": subject.get("xref") or [],
                    "disease_provided_by": subject.get("provided_by"),
                    "disease_synonyms": (subject.get("synonym") or [])
                    + (subject.get("related_synonym") or []),
                    "score": item.get("score"),
                    "average_score": similarity.get("average_score"),
                    "best_score": similarity.get("best_score"),
                    "metric": similarity.get("metric"),
                    # Which of the queried phenotypes each matched term
                    # answered, and through which common ancestor. A score
                    # with no subsuming term behind it cannot be explained.
                    "object_best_matches": self._flatten_best_matches(
                        similarity.get("object_best_matches")
                    ),
                    "matched_phenotypes": [
                        {
                            "query_phenotype": v.get("match_source"),
                            "query_label": v.get("match_source_label"),
                            "matched_phenotype": v.get("match_target"),
                            "matched_label": v.get("match_target_label"),
                            "score": v.get("score"),
                        }
                        for v in similarity.get("object_best_matches", {}).values()
                    ],
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "Monarch Initiative V3 - Semantic Similarity",
                "query_phenotypes": phenotypes,
                "group": group,
                "total_results": len(results),
            },
        }

    @staticmethod
    def _normalize_termset(value: Any) -> list:
        """Accept a list of HPO CURIEs or a comma-separated string."""
        if isinstance(value, str):
            return [t.strip() for t in value.split(",") if t.strip()]
        if isinstance(value, list):
            return [str(t).strip() for t in value if str(t).strip()]
        return []

    @staticmethod
    def _flatten_best_matches(matches: Any) -> list:
        """Flatten a best-matches mapping into a simple list of pairs."""
        flat = []
        if not isinstance(matches, dict):
            return flat
        for entry in matches.values():
            if not isinstance(entry, dict):
                continue
            sim = entry.get("similarity") or {}
            flat.append(
                {
                    "query_phenotype": entry.get("match_source"),
                    "query_label": entry.get("match_source_label"),
                    "matched_phenotype": entry.get("match_target"),
                    "matched_label": entry.get("match_target_label"),
                    "score": entry.get("score"),
                    "ancestor_id": sim.get("ancestor_id"),
                    "ancestor_label": sim.get("ancestor_label"),
                    # The term that subsumes both sides of the match, which is
                    # the reason the pair scored at all.
                    "match_subsumer": entry.get("match_subsumer"),
                    "match_subsumer_label": entry.get("match_subsumer_label"),
                    "jaccard_similarity": sim.get("jaccard_similarity"),
                    "phenodigm_score": sim.get("phenodigm_score"),
                }
            )
        return flat

    def _semsim_compare(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Compare two explicit phenotype profiles (HPO term sets) pairwise.

        Computes semantic similarity (Phenodigm / Jaccard / information
        content) between a subject term set and an object term set, returning
        the overall scores and the per-term best matches in each direction.
        """
        subjects = self._normalize_termset(
            arguments.get("subjects") or arguments.get("subject_terms")
        )
        objects = self._normalize_termset(
            arguments.get("objects") or arguments.get("object_terms")
        )
        if not subjects:
            return {
                "status": "error",
                "error": (
                    "subjects is required: a list of HPO CURIEs "
                    "(e.g., ['HP:0001250', 'HP:0004322'])"
                ),
            }
        if not objects:
            return {
                "status": "error",
                "error": (
                    "objects is required: a list of HPO CURIEs "
                    "(e.g., ['HP:0001263', 'HP:0000252'])"
                ),
            }

        subject_path = ",".join(subjects)
        object_path = ",".join(objects)
        url = f"{MONARCH_BASE_URL}/semsim/compare/{subject_path}/{object_path}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        return {
            "status": "success",
            "data": {
                "average_score": data.get("average_score"),
                "best_score": data.get("best_score"),
                "metric": data.get("metric"),
                "subject_best_matches": self._flatten_best_matches(
                    data.get("subject_best_matches")
                ),
                "object_best_matches": self._flatten_best_matches(
                    data.get("object_best_matches")
                ),
            },
            "metadata": {
                "source": "Monarch Initiative V3 - Semantic Similarity Compare",
                "subjects": subjects,
                "objects": objects,
            },
        }
