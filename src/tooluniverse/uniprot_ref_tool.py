# uniprot_ref_tool.py
"""
UniProt Reference Datasets API tool for ToolUniverse.

Provides access to UniProt's controlled vocabularies and reference datasets:
- Diseases: Curated disease definitions with OMIM/MeSH cross-references
- Keywords: Standardized annotation terms for protein function/process/location
- Proteomes: Reference proteome data with chromosome-level protein counts

API: https://rest.uniprot.org/
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool
from .uniprot_pagination import pagination_metadata

UNIPROT_BASE_URL = "https://rest.uniprot.org"


# A proteome search row names this many of its components; a plant
# proteome can list hundreds of scaffolds.
COMPONENT_NAMES_PER_PROTEOME = 50


def _validated_search_size(arguments: Dict[str, Any]) -> tuple[int | None, str | None]:
    """Validate the shared UniProt REST search page size (official max 500)."""
    raw_size = arguments.get("size")
    raw_size = 10 if raw_size is None else raw_size
    try:
        if isinstance(raw_size, bool):
            raise ValueError
        size = int(raw_size)
        if isinstance(raw_size, float) and not raw_size.is_integer():
            raise ValueError
        if not 1 <= size <= 500:
            raise ValueError
    except (TypeError, ValueError):
        return None, "size must be an integer from 1 to 500"
    return size, None


@register_tool("UniProtRefTool")
class UniProtRefTool(BaseTool):
    """
    Tool for querying UniProt reference datasets (diseases, keywords, proteomes).

    UniProt maintains curated controlled vocabularies that standardize protein
    annotations across the database. This tool provides access to:
    - Disease vocabulary: 6K+ curated disease entries with cross-refs to OMIM, MeSH, MedGen
    - Keyword vocabulary: 1.2K+ standardized terms for biological process, function, etc.
    - Proteomes: Reference proteome summaries with assembly and component data

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "search_diseases")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the UniProt reference dataset API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"UniProt API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to UniProt API"}
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {"status": "error", "error": "Resource not found in UniProt"}
            return {
                "status": "error",
                "error": f"UniProt API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying UniProt: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate UniProt reference endpoint."""
        if self.endpoint == "search_diseases":
            return self._search_diseases(arguments)
        elif self.endpoint == "get_disease":
            return self._get_disease(arguments)
        elif self.endpoint == "search_keywords":
            return self._search_keywords(arguments)
        elif self.endpoint == "get_keyword":
            return self._get_keyword(arguments)
        elif self.endpoint == "get_proteome":
            return self._get_proteome(arguments)
        elif self.endpoint == "search_proteomes":
            return self._search_proteomes(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _search_diseases(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search UniProt controlled disease vocabulary."""
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        size, size_error = _validated_search_size(arguments)
        if size_error:
            return {"status": "error", "error": size_error}
        assert size is not None
        url = f"{UNIPROT_BASE_URL}/diseases/search"
        params = {"query": query, "size": size, "format": "json"}
        if arguments.get("cursor"):
            params["cursor"] = arguments["cursor"]

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        diseases = []
        for r in data.get("results", []):
            xrefs = []
            for xr in r.get("crossReferences", []):
                xrefs.append(
                    {
                        "database": xr.get("databaseType"),
                        "id": xr.get("id"),
                        # MIM cross-references carry the property that says
                        # which KIND of entry the id is -- "gene", "phenotype"
                        # -- and an OMIM gene id used as a disease id is a
                        # different claim.
                        "properties": xr.get("properties") or [],
                    }
                )

            diseases.append(
                {
                    "id": r.get("id"),
                    "name": r.get("name"),
                    "acronym": r.get("acronym"),
                    "definition": r.get("definition"),
                    "alternative_names": r.get("alternativeNames", []),
                    "cross_references": xrefs,
                    "reviewed_protein_count": r.get("statistics", {}).get(
                        "reviewedProteinCount"
                    ),
                    "unreviewed_protein_count": r.get("statistics", {}).get(
                        "unreviewedProteinCount"
                    ),
                    "keywords": r.get("keywords") or [],
                }
            )

        return {
            "status": "success",
            "data": diseases,
            "metadata": {
                "source": "UniProt Controlled Disease Vocabulary",
                "query": query,
                **pagination_metadata(response, len(diseases)),
            },
        }

    def _get_disease(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get a specific disease entry by UniProt disease ID."""
        disease_id = arguments.get("disease_id", "")
        if not disease_id:
            return {"status": "error", "error": "disease_id parameter is required"}

        url = f"{UNIPROT_BASE_URL}/diseases/{disease_id}"
        params = {"format": "json"}

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        r = response.json()

        xrefs = []
        for xr in r.get("crossReferences", []):
            xrefs.append(
                {
                    "database": xr.get("databaseType"),
                    "id": xr.get("id"),
                    "properties": xr.get("properties", []),
                }
            )

        return {
            "status": "success",
            "data": {
                "id": r.get("id"),
                "name": r.get("name"),
                "acronym": r.get("acronym"),
                "definition": r.get("definition"),
                "alternative_names": r.get("alternativeNames", []),
                "cross_references": xrefs,
                "reviewed_protein_count": r.get("statistics", {}).get(
                    "reviewedProteinCount"
                ),
                "unreviewed_protein_count": r.get("statistics", {}).get(
                    "unreviewedProteinCount"
                ),
            },
            "metadata": {
                "source": "UniProt Controlled Disease Vocabulary",
            },
        }

    def _search_keywords(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search UniProt keyword controlled vocabulary."""
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        size, size_error = _validated_search_size(arguments)
        if size_error:
            return {"status": "error", "error": size_error}
        assert size is not None
        url = f"{UNIPROT_BASE_URL}/keywords/search"
        params = {"query": query, "size": size, "format": "json"}
        if arguments.get("cursor"):
            params["cursor"] = arguments["cursor"]

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        keywords = []
        for r in data.get("results", []):
            kw = r.get("keyword", {})
            keywords.append(
                {
                    "id": kw.get("id"),
                    "name": kw.get("name"),
                    "category": r.get("category", {}).get("name")
                    if isinstance(r.get("category"), dict)
                    else r.get("category"),
                    "definition": r.get("definition"),
                    "reviewed_protein_count": r.get("statistics", {}).get(
                        "reviewedProteinCount"
                    ),
                    # The unreviewed count beside the reviewed one. A keyword
                    # on 300 Swiss-Prot entries and 40,000 TrEMBL ones is a
                    # different thing from one on 300 and 12, and only half
                    # the pair was reported.
                    "unreviewed_protein_count": r.get("statistics", {}).get(
                        "unreviewedProteinCount"
                    ),
                    "category_id": r.get("category", {}).get("id")
                    if isinstance(r.get("category"), dict)
                    else None,
                    # Where the keyword sits in the hierarchy, and the GO
                    # terms it corresponds to -- which is how a keyword
                    # search is carried into an enrichment analysis.
                    "parents": [
                        {
                            "id": (parent.get("keyword") or {}).get("id"),
                            "name": (parent.get("keyword") or {}).get("name"),
                        }
                        for parent in (r.get("parents") or [])
                        if isinstance(parent, dict)
                    ],
                    "children": [
                        {
                            "id": (child.get("keyword") or {}).get("id"),
                            "name": (child.get("keyword") or {}).get("name"),
                        }
                        for child in (r.get("children") or [])
                        if isinstance(child, dict)
                    ],
                    "gene_ontologies": [
                        {"go_id": go.get("goId"), "name": go.get("name")}
                        for go in (r.get("geneOntologies") or [])
                        if isinstance(go, dict)
                    ],
                    "synonyms": r.get("synonyms") or [],
                    "links": r.get("links") or [],
                }
            )

        return {
            "status": "success",
            "data": keywords,
            "metadata": {
                "source": "UniProt Keyword Controlled Vocabulary",
                "query": query,
                **pagination_metadata(response, len(keywords)),
            },
        }

    def _get_keyword(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get a specific keyword entry by UniProt keyword ID."""
        keyword_id = arguments.get("keyword_id", "")
        if not keyword_id:
            return {"status": "error", "error": "keyword_id parameter is required"}

        url = f"{UNIPROT_BASE_URL}/keywords/{keyword_id}"
        params = {"format": "json"}

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        r = response.json()

        kw = r.get("keyword", {})
        parents = []
        for p in r.get("parents", []):
            pkw = p.get("keyword", {})
            parents.append(
                {
                    "id": pkw.get("id"),
                    "name": pkw.get("name"),
                }
            )

        go_mappings = []
        for g in r.get("geneOntologies", []):
            go_mappings.append(
                {
                    "go_id": g.get("goId"),
                    "name": g.get("name"),
                }
            )

        return {
            "status": "success",
            "data": {
                "id": kw.get("id"),
                "name": kw.get("name"),
                "category": r.get("category", {}).get("name")
                if isinstance(r.get("category"), dict)
                else r.get("category"),
                "definition": r.get("definition"),
                "parents": parents,
                "go_mappings": go_mappings,
                "reviewed_protein_count": r.get("statistics", {}).get(
                    "reviewedProteinCount"
                ),
                "unreviewed_protein_count": r.get("statistics", {}).get(
                    "unreviewedProteinCount"
                ),
            },
            "metadata": {
                "source": "UniProt Keyword Controlled Vocabulary",
            },
        }

    def _get_proteome(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get reference proteome information by UniProt proteome ID."""
        proteome_id = arguments.get("proteome_id", "")
        if not proteome_id:
            return {"status": "error", "error": "proteome_id parameter is required"}

        url = f"{UNIPROT_BASE_URL}/proteomes/{proteome_id}"
        params = {"format": "json"}

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        r = response.json()

        tax = r.get("taxonomy", {})
        all_components = r.get("components", [])
        total_proteins = sum((c.get("proteinCount") or 0) for c in all_components)
        component_offset = max(arguments.get("component_offset") or 0, 0)
        component_limit = min(max(arguments.get("component_limit") or 30, 1), 500)
        component_page = all_components[
            component_offset : component_offset + component_limit
        ]
        components = []
        for c in component_page:
            count = c.get("proteinCount", 0) or 0
            genome_acc = None
            for xr in c.get("proteomeCrossReferences", []):
                if xr.get("database") == "GenomeAccession":
                    genome_acc = xr.get("id")
                    break
            components.append(
                {
                    "name": c.get("name"),
                    "protein_count": count,
                    "genome_accession": genome_acc,
                }
            )

        has_more = component_offset + len(components) < len(all_components)
        description = r.get("description") or ""
        return {
            "status": "success",
            "data": {
                "id": r.get("id"),
                "description": description,
                "description_length": len(description),
                "organism": {
                    "scientific_name": tax.get("scientificName"),
                    "common_name": tax.get("commonName"),
                    "taxon_id": tax.get("taxonId"),
                },
                "proteome_type": r.get("proteomeType"),
                "components": components,
                "total_protein_count": total_proteins,
                # The organism's place in the tree, which a taxon id alone
                # does not give: 30 ranks of lineage are in the same record.
                "taxon_lineage": [
                    {
                        "taxon_id": node.get("taxonId"),
                        "scientific_name": node.get("scientificName"),
                        "common_name": node.get("commonName"),
                        "rank": node.get("rank"),
                    }
                    for node in (r.get("taxonLineage") or [])
                    if isinstance(node, dict)
                ],
                "strain": tax.get("strain"),
                "synonyms": tax.get("synonyms") or [],
                # The papers describing the proteome, with the 2,840 author
                # names and the cross-references that make them citable. The
                # record carries them; the answer had none.
                "citations": [
                    {
                        "id": (citation.get("citation") or citation).get("id"),
                        "title": (citation.get("citation") or citation).get("title"),
                        "journal": (citation.get("citation") or citation).get(
                            "journal"
                        ),
                        "publication_date": (
                            citation.get("citation") or citation
                        ).get("publicationDate"),
                        "authors": (citation.get("citation") or citation).get(
                            "authors"
                        )
                        or [],
                        "cross_references": (
                            citation.get("citation") or citation
                        ).get("citationCrossReferences")
                        or [],
                        "citation_type": (citation.get("citation") or citation).get(
                            "citationType"
                        ),
                        "first_page": (citation.get("citation") or citation).get(
                            "firstPage"
                        ),
                        "last_page": (citation.get("citation") or citation).get(
                            "lastPage"
                        ),
                        "volume": (citation.get("citation") or citation).get("volume"),
                        # A consortium paper has an authoring group and no
                        # author list, so without this the citation reads as
                        # having no authors at all.
                        "authoring_group": (citation.get("citation") or citation).get(
                            "authoringGroup"
                        )
                        or [],
                    }
                    for citation in (r.get("citations") or [])
                    if isinstance(citation, dict)
                ],
                "genome_assembly": r.get("genomeAssembly"),
                "genome_annotation": r.get("genomeAnnotation"),
                "annotation_score": r.get("annotationScore"),
                "busco": r.get("proteomeCompletenessReport", {}).get("buscoReport")
                if isinstance(r.get("proteomeCompletenessReport"), dict)
                else None,
                "cpd": r.get("proteomeCompletenessReport", {}).get("cpdReport")
                if isinstance(r.get("proteomeCompletenessReport"), dict)
                else None,
            },
            "metadata": {
                "source": "UniProt Proteomes",
                "total_components": len(all_components),
                "components_returned": len(components),
                "component_offset": component_offset,
                "components_truncated": has_more,
                "next_component_offset": (
                    component_offset + len(components) if has_more else None
                ),
            },
        }

    def _search_proteomes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search UniProt reference proteomes."""
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        size, size_error = _validated_search_size(arguments)
        if size_error:
            return {"status": "error", "error": size_error}
        assert size is not None
        url = f"{UNIPROT_BASE_URL}/proteomes/search"
        params = {"query": query, "size": size, "format": "json"}
        if arguments.get("cursor"):
            params["cursor"] = arguments["cursor"]

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        proteomes = []
        for r in data.get("results", []):
            tax = r.get("taxonomy", {})
            total_proteins = sum(
                (c.get("proteinCount") or 0) for c in r.get("components", [])
            )
            proteomes.append(
                {
                    "id": r.get("id"),
                    "organism": tax.get("scientificName"),
                    "common_name": tax.get("commonName"),
                    "taxon_id": tax.get("taxonId"),
                    "proteome_type": r.get("proteomeType"),
                    "protein_count": total_proteins,
                    # A proteome search is scanned to choose one, and the row
                    # gave four fields of a record that also says where the
                    # organism sits in the tree, how complete the proteome is
                    # and what describes it. The lineage and the citations are
                    # summarised here, in full on UniProtRef_get_proteome.
                    "taxon_lineage": [
                        node.get("scientificName")
                        for node in (r.get("taxonLineage") or [])
                        if isinstance(node, dict) and node.get("scientificName")
                    ],
                    "taxon_rank": tax.get("rank"),
                    "strain": tax.get("strain"),
                    # `taxon_lineage` is names only, and the id is how a
                    # lineage is followed rather than matched; the rank is
                    # what makes "Mammalia" a class rather than a guess.
                    "taxon_lineage_nodes": [
                        {
                            "scientific_name": node.get("scientificName"),
                            "taxon_id": node.get("taxonId"),
                            "rank": node.get("rank"),
                        }
                        for node in (r.get("taxonLineage") or [])
                        if isinstance(node, dict)
                    ],
                    "component_count": len(r.get("components") or []),
                    # What the components are -- "Chromosome 1", "Mitochondrion"
                    # -- where the row gave only how many there were and which
                    # databases they cross-reference.
                    "component_names": [
                        component.get("name")
                        for component in (r.get("components") or [])
                        if isinstance(component, dict) and component.get("name")
                    ][:COMPONENT_NAMES_PER_PROTEOME],
                    "citation_count": len(r.get("citations") or []),
                    "annotation_score": r.get("annotationScore"),
                    "genome_assembly_id": (r.get("genomeAssembly") or {}).get(
                        "assemblyId"
                    )
                    if isinstance(r.get("genomeAssembly"), dict)
                    else None,
                    "busco_complete_percent": (
                        (r.get("proteomeCompletenessReport") or {}).get("buscoReport")
                        or {}
                    ).get("complete")
                    if isinstance(r.get("proteomeCompletenessReport"), dict)
                    else None,
                    "component_databases": sorted(
                        {
                            xref.get("database")
                            for component in (r.get("components") or [])
                            if isinstance(component, dict)
                            for xref in (
                                component.get("proteomeCrossReferences") or []
                            )
                            if isinstance(xref, dict) and xref.get("database")
                        }
                    ),
                }
            )

        return {
            "status": "success",
            "data": proteomes,
            "metadata": {
                "source": "UniProt Proteomes",
                "query": query,
                **pagination_metadata(response, len(proteomes)),
            },
        }
