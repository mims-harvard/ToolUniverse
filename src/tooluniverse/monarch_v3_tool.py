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

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

MONARCH_BASE_URL = "https://api.monarchinitiative.org/v3/api"


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
            return {"error": f"Monarch API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to Monarch Initiative API"}
        except requests.exceptions.HTTPError as e:
            return {"error": f"Monarch API HTTP error: {e.response.status_code}"}
        except Exception as e:
            return {"error": f"Unexpected error querying Monarch: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate Monarch V3 endpoint."""
        if self.endpoint == "entity":
            return self._get_entity(arguments)
        elif self.endpoint == "associations":
            return self._get_associations(arguments)
        elif self.endpoint == "search":
            return self._search(arguments)
        elif self.endpoint == "mondo_search":
            return self._mondo_search(arguments)
        elif self.endpoint == "mondo_disease":
            return self._mondo_get_disease(arguments)
        elif self.endpoint == "mondo_phenotypes":
            return self._mondo_get_phenotypes(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _get_entity(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed entity information by CURIE identifier."""
        entity_id = arguments.get("entity_id", "")
        if not entity_id:
            return {
                "error": "entity_id parameter is required (e.g., HGNC:11998, MONDO:0005148, HP:0001250)"
            }

        url = f"{MONARCH_BASE_URL}/entity/{entity_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        return {
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
            },
            "metadata": {
                "source": "Monarch Initiative V3",
            },
        }

    def _get_associations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get associations for an entity with filtering by category."""
        subject = arguments.get("subject", "")
        if not subject:
            return {
                "error": "subject parameter is required (e.g., HGNC:11998 or MONDO:0005148)"
            }

        category = arguments.get("category", "")
        if not category:
            return {
                "error": "category parameter is required. Options: biolink:GeneToPhenotypicFeatureAssociation, biolink:DiseaseToPhenotypicFeatureAssociation, biolink:CorrelatedGeneToDiseaseAssociation, biolink:CausalGeneToDiseaseAssociation, biolink:VariantToDiseaseAssociation, biolink:GeneToPathwayAssociation"
            }

        limit = arguments.get("limit") or 20

        url = f"{MONARCH_BASE_URL}/association"
        params = {
            "subject": subject,
            "category": category,
            "limit": min(limit, 200),
        }

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
                }
            )

        return {
            "data": associations,
            "metadata": {
                "source": "Monarch Initiative V3",
                "subject": subject,
                "category": category,
                "total_results": data.get("total", len(associations)),
            },
        }

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search Monarch knowledge graph for entities by name/keyword."""
        query = arguments.get("query", "")
        if not query:
            return {"error": "query parameter is required"}

        limit = arguments.get("limit") or 10
        category = arguments.get("category")  # e.g., biolink:Gene, biolink:Disease

        url = f"{MONARCH_BASE_URL}/search"
        params = {
            "q": query,
            "limit": min(limit, 50),
        }
        if category:
            params["category"] = category

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        results = []
        for item in data.get("items", []):
            results.append(
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "category": item.get("category"),
                    "symbol": item.get("symbol"),
                    "description": item.get("description"),
                    "taxon": item.get("in_taxon"),
                    "taxon_label": item.get("in_taxon_label"),
                }
            )

        return {
            "data": results,
            "metadata": {
                "source": "Monarch Initiative V3",
                "query": query,
                "total_results": data.get("total", len(results)),
            },
        }

    # --- Mondo Disease Ontology specific endpoints ---

    def _mondo_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for diseases in the Mondo Disease Ontology via Monarch."""
        query = arguments.get("query", "").strip()
        if not query:
            return {
                "error": "query parameter is required (e.g., 'Alzheimer', 'breast cancer', 'diabetes')"
            }

        limit = arguments.get("limit") or 10

        url = f"{MONARCH_BASE_URL}/search"
        params = {
            "q": query,
            "category": "biolink:Disease",
            "limit": min(limit, 50),
        }

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        results = []
        for item in data.get("items", []):
            results.append(
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "category": item.get("category"),
                    "description": item.get("description"),
                    "xref": item.get("xref", []),
                }
            )

        return {
            "data": results,
            "metadata": {
                "source": "Mondo Disease Ontology (via Monarch Initiative V3)",
                "query": query,
                "total_results": data.get("total", len(results)),
            },
        }

    def _mondo_get_disease(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed Mondo disease information including hierarchy and cross-references."""
        disease_id = arguments.get("disease_id", "").strip()
        if not disease_id:
            return {
                "error": "disease_id parameter is required (e.g., MONDO:0004975, MONDO:0005148)"
            }

        url = f"{MONARCH_BASE_URL}/entity/{disease_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        # Verify this is a disease
        category = data.get("category", "")
        if category and "Disease" not in category:
            return {
                "error": f"Entity {disease_id} is not a disease (category: {category})"
            }

        # Extract hierarchy
        hierarchy = data.get("node_hierarchy", {})
        parent_diseases = []
        if hierarchy and isinstance(hierarchy, dict):
            for parent in hierarchy.get("super_classes", []):
                if isinstance(parent, dict):
                    parent_diseases.append(
                        {
                            "id": parent.get("id"),
                            "name": parent.get("name"),
                        }
                    )

        # Extract mappings (cross-references to other ontologies)
        mappings = []
        for m in data.get("mappings", []) or []:
            if isinstance(m, dict):
                mappings.append(
                    {
                        "id": m.get("id"),
                        "url": m.get("url"),
                    }
                )

        # Extract association counts
        assoc_counts = {}
        for ac in data.get("association_counts", []) or []:
            if isinstance(ac, dict):
                assoc_counts[ac.get("label", "")] = ac.get("count", 0)

        # Extract causal genes (API returns full entity objects, extract key fields)
        raw_genes = data.get("causal_gene", []) or []
        causal_genes = []
        for gene in raw_genes:
            if isinstance(gene, dict):
                causal_genes.append(
                    {
                        "id": gene.get("id"),
                        "name": gene.get("name"),
                    }
                )
            elif isinstance(gene, str):
                causal_genes.append({"id": gene, "name": None})

        # Extract inheritance pattern (API returns full entity object or None)
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

        return {
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
            },
            "metadata": {
                "source": "Mondo Disease Ontology (via Monarch Initiative V3)",
                "disease_id": disease_id,
            },
        }

    def _mondo_get_phenotypes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get HPO phenotypes associated with a Mondo disease."""
        disease_id = arguments.get("disease_id", "").strip()
        if not disease_id:
            return {
                "error": "disease_id parameter is required (e.g., MONDO:0004975, MONDO:0005148)"
            }

        limit = arguments.get("limit") or 20

        url = f"{MONARCH_BASE_URL}/association"
        params = {
            "subject": disease_id,
            "category": "biolink:DiseaseToPhenotypicFeatureAssociation",
            "limit": min(limit, 200),
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
                }
            )

        return {
            "data": phenotypes,
            "metadata": {
                "source": "Mondo Disease Ontology (via Monarch Initiative V3)",
                "disease_id": disease_id,
                "total_phenotypes": data.get("total", len(phenotypes)),
            },
        }
