# mirna_tool.py
"""
miRNA/lncRNA tools for ToolUniverse via RNAcentral and EBI Search APIs.

Provides miRNA and lncRNA search, sequence retrieval, cross-references, and
publication data by leveraging RNAcentral (the comprehensive ncRNA aggregator)
and EBI Search (for text-based queries with faceted filtering).

miRBase and LNCipedia data is aggregated through RNAcentral, which provides
a unified REST API for accessing ncRNA data from 50+ databases.

APIs used:
  - RNAcentral REST API: https://rnacentral.org/api/v1/
  - EBI Search: https://www.ebi.ac.uk/ebisearch/ws/rest/rnacentral

No authentication required. Free public access.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool


RNACENTRAL_BASE = "https://rnacentral.org/api/v1"
EBI_SEARCH_BASE = "https://www.ebi.ac.uk/ebisearch/ws/rest/rnacentral"

# Standard EBI search fields
EBI_FIELDS = "description,rna_type,length,expert_db,has_secondary_structure,has_genomic_coordinates"

# Common species name to NCBI Taxonomy ID mapping
SPECIES_TAXID = {
    "homo sapiens": "9606",
    "human": "9606",
    "mus musculus": "10090",
    "mouse": "10090",
    "rattus norvegicus": "10116",
    "rat": "10116",
    "drosophila melanogaster": "7227",
    "fruit fly": "7227",
    "caenorhabditis elegans": "6239",
    "danio rerio": "7955",
    "zebrafish": "7955",
    "arabidopsis thaliana": "3702",
    "saccharomyces cerevisiae": "4932",
    "gallus gallus": "9031",
    "chicken": "9031",
    "bos taurus": "9913",
    "sus scrofa": "9823",
    "xenopus tropicalis": "8364",
}


class miRNASearchTool(BaseTool):
    """
    Search for miRNAs/lncRNAs/ncRNAs via EBI Search of RNAcentral.
    Can filter results by RNA type for focused results.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        # Get default RNA type filter from tool config fields
        fields = tool_config.get("fields", {})
        self.default_rna_type = fields.get("rna_type_filter", "")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            query = arguments.get("query", "")
            # User-supplied rna_type overrides config default
            rna_type_filter = arguments.get("rna_type", "") or self.default_rna_type
            species = arguments.get("species", "")
            size = int(arguments.get("size", 10))

            # Build EBI search query with optional filters
            search_parts = [query]
            if rna_type_filter:
                search_parts.append(f"rna_type:{rna_type_filter}")
            if species:
                # Map species name to taxonomy ID for reliable filtering
                taxid = SPECIES_TAXID.get(species.lower(), "")
                if taxid:
                    search_parts.append(f"TAXONOMY:{taxid}")
                else:
                    # Try using the species name directly (works for exact matches)
                    search_parts.append(f"TAXONOMY:{species.replace(' ', '_')}")
            search_query = " AND ".join(search_parts)

            params = {
                "query": search_query,
                "format": "json",
                "size": min(size, 100),
                "fields": EBI_FIELDS,
            }

            resp = requests.get(EBI_SEARCH_BASE, params=params, timeout=self.timeout)
            resp.raise_for_status()
            result = resp.json()

            entries = []
            for entry in result.get("entries", []):
                fields = entry.get("fields", {})
                entries.append(
                    {
                        "rnacentral_id": entry.get("id", ""),
                        "description": (
                            fields.get("description", [""])[0]
                            if fields.get("description")
                            else ""
                        ),
                        "rna_type": (
                            fields.get("rna_type", [""])[0]
                            if fields.get("rna_type")
                            else ""
                        ),
                        "length": int(fields.get("length", ["0"])[0])
                        if fields.get("length")
                        else 0,
                        "expert_databases": fields.get("expert_db", []),
                        "has_secondary_structure": (
                            fields.get("has_secondary_structure", ["False"])[0]
                            == "True"
                            if fields.get("has_secondary_structure")
                            else False
                        ),
                        "has_genomic_coordinates": (
                            fields.get("has_genomic_coordinates", ["False"])[0]
                            == "True"
                            if fields.get("has_genomic_coordinates")
                            else False
                        ),
                    }
                )

            return {
                "status": "success",
                "data": {
                    "total_hits": result.get("hitCount", 0),
                    "returned": len(entries),
                    "entries": entries,
                },
                "metadata": {
                    "source": "EBI Search / RNAcentral",
                    "query": search_query,
                },
            }

        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"EBI Search API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to EBI Search API"}
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {"status": "error", "error": f"EBI Search API HTTP error: {code}"}
        except Exception as e:
            return {"status": "error", "error": f"miRNA search failed: {str(e)}"}


class miRNAGetTool(BaseTool):
    """
    Get detailed miRNA/lncRNA information from RNAcentral by ID.
    Returns sequence, species, RNA type, and database cross-references.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "get_rna")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            endpoint = self.endpoint

            if endpoint == "get_rna":
                return self._get_rna(arguments)
            elif endpoint == "get_publications":
                return self._get_publications(arguments)
            elif endpoint == "get_xrefs":
                return self._get_xrefs(arguments)
            else:
                return {"status": "error", "error": f"Unknown endpoint: {endpoint}"}

        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"RNAcentral API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to RNAcentral API"}
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            if code == 404:
                return {
                    "status": "error",
                    "error": f"RNA entry not found: {arguments.get('rnacentral_id', '')}",
                }
            return {"status": "error", "error": f"RNAcentral API HTTP error: {code}"}
        except Exception as e:
            return {"status": "error", "error": f"RNAcentral query failed: {str(e)}"}

    def _get_rna(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get RNA entry details including sequence."""
        rnacentral_id = arguments.get("rnacentral_id", "")
        taxid = arguments.get("taxid")

        # Build URL: /api/v1/rna/{URS}/{taxid} or /api/v1/rna/{URS}
        if taxid:
            url = f"{RNACENTRAL_BASE}/rna/{rnacentral_id}/{taxid}?format=json"
        else:
            url = f"{RNACENTRAL_BASE}/rna/{rnacentral_id}?format=json"

        resp = requests.get(url, timeout=self.timeout)
        resp.raise_for_status()
        result = resp.json()

        return {
            "status": "success",
            "data": {
                "rnacentral_id": result.get("rnacentral_id", ""),
                "description": result.get("description", ""),
                "short_description": result.get("short_description", ""),
                "sequence": result.get("sequence", ""),
                "length": result.get("length", 0),
                "rna_type": result.get("rna_type", ""),
                "species": result.get("species", ""),
                "taxid": result.get("taxid"),
                "genes": result.get("genes", []),
                "publications_count": result.get("publications", 0),
                "is_active": result.get("is_active", True),
                "distinct_databases": result.get("distinct_databases", ""),
            },
            "metadata": {
                "source": "RNAcentral",
                "url": f"https://rnacentral.org/rna/{rnacentral_id}",
            },
        }

    def _get_publications(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get publications associated with an RNA entry."""
        rnacentral_id = arguments.get("rnacentral_id", "")
        page_size = int(arguments.get("page_size", 10))

        url = (
            f"{RNACENTRAL_BASE}/rna/{rnacentral_id}/publications"
            f"?format=json&page_size={min(page_size, 50)}"
        )

        resp = requests.get(url, timeout=self.timeout)
        resp.raise_for_status()
        result = resp.json()

        publications = []
        for pub in result.get("results", []):
            publications.append(
                {
                    "title": pub.get("title", ""),
                    "authors": pub.get("authors", []),
                    "publication": pub.get("publication", ""),
                    "pubmed_id": pub.get("pubmed_id", ""),
                    "doi": pub.get("doi", ""),
                    "expert_db": pub.get("expert_db", False),
                }
            )

        return {
            "status": "success",
            "data": {
                "total_publications": result.get("count", 0),
                "returned": len(publications),
                "publications": publications,
            },
            "metadata": {
                "source": "RNAcentral",
                "rnacentral_id": rnacentral_id,
            },
        }

    def _get_xrefs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get cross-references for an RNA entry."""
        rnacentral_id = arguments.get("rnacentral_id", "")
        page_size = int(arguments.get("page_size", 10))

        url = (
            f"{RNACENTRAL_BASE}/rna/{rnacentral_id}/xrefs"
            f"?format=json&page_size={min(page_size, 50)}"
        )

        resp = requests.get(url, timeout=self.timeout)
        resp.raise_for_status()
        result = resp.json()

        xrefs = []
        for xref in result.get("results", []):
            acc = xref.get("accession", {})
            xrefs.append(
                {
                    "database": xref.get("database", ""),
                    "accession_id": acc.get("id", ""),
                    "external_id": acc.get("external_id", ""),
                    "description": acc.get("description", ""),
                    "species": acc.get("species", ""),
                    "rna_type": acc.get("rna_type", ""),
                    "gene": acc.get("gene", ""),
                    "taxid": xref.get("taxid"),
                    "is_active": xref.get("is_active", True),
                    "expert_db_url": acc.get("expert_db_url", ""),
                    "mirbase_mature_products": xref.get("mirbase_mature_products"),
                    "mirbase_precursor": xref.get("mirbase_precursor"),
                }
            )

        return {
            "status": "success",
            "data": {
                "total_xrefs": result.get("count", 0),
                "returned": len(xrefs),
                "cross_references": xrefs,
            },
            "metadata": {
                "source": "RNAcentral",
                "rnacentral_id": rnacentral_id,
            },
        }
