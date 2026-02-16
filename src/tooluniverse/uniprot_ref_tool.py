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

UNIPROT_BASE_URL = "https://rest.uniprot.org"


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
            return {"error": f"UniProt API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to UniProt API"}
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {"error": "Resource not found in UniProt"}
            return {"error": f"UniProt API HTTP error: {e.response.status_code}"}
        except Exception as e:
            return {"error": f"Unexpected error querying UniProt: {str(e)}"}

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
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _search_diseases(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search UniProt controlled disease vocabulary."""
        query = arguments.get("query", "")
        if not query:
            return {"error": "query parameter is required"}

        size = min(arguments.get("size") or 10, 25)
        url = f"{UNIPROT_BASE_URL}/diseases/search"
        params = {"query": query, "size": size, "format": "json"}

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
                }
            )

        return {
            "data": diseases,
            "metadata": {
                "source": "UniProt Controlled Disease Vocabulary",
                "query": query,
                "total_results": len(diseases),
            },
        }

    def _get_disease(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get a specific disease entry by UniProt disease ID."""
        disease_id = arguments.get("disease_id", "")
        if not disease_id:
            return {"error": "disease_id parameter is required"}

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
            return {"error": "query parameter is required"}

        size = min(arguments.get("size") or 10, 25)
        url = f"{UNIPROT_BASE_URL}/keywords/search"
        params = {"query": query, "size": size, "format": "json"}

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
                }
            )

        return {
            "data": keywords,
            "metadata": {
                "source": "UniProt Keyword Controlled Vocabulary",
                "query": query,
                "total_results": len(keywords),
            },
        }

    def _get_keyword(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get a specific keyword entry by UniProt keyword ID."""
        keyword_id = arguments.get("keyword_id", "")
        if not keyword_id:
            return {"error": "keyword_id parameter is required"}

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
            return {"error": "proteome_id parameter is required"}

        url = f"{UNIPROT_BASE_URL}/proteomes/{proteome_id}"
        params = {"format": "json"}

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        r = response.json()

        tax = r.get("taxonomy", {})
        components = []
        total_proteins = 0
        for c in r.get("components", [])[:30]:
            count = c.get("proteinCount", 0) or 0
            total_proteins += count
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

        return {
            "data": {
                "id": r.get("id"),
                "description": (r.get("description") or "")[:500],
                "organism": {
                    "scientific_name": tax.get("scientificName"),
                    "common_name": tax.get("commonName"),
                    "taxon_id": tax.get("taxonId"),
                },
                "proteome_type": r.get("proteomeType"),
                "components": components,
                "total_protein_count": total_proteins,
            },
            "metadata": {
                "source": "UniProt Proteomes",
            },
        }

    def _search_proteomes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search UniProt reference proteomes."""
        query = arguments.get("query", "")
        if not query:
            return {"error": "query parameter is required"}

        size = min(arguments.get("size") or 10, 25)
        url = f"{UNIPROT_BASE_URL}/proteomes/search"
        params = {"query": query, "size": size, "format": "json"}

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
                }
            )

        return {
            "data": proteomes,
            "metadata": {
                "source": "UniProt Proteomes",
                "query": query,
                "total_results": len(proteomes),
            },
        }
