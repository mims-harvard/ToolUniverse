# uniparc_tool.py
"""
UniProt UniParc tool for ToolUniverse.

UniParc (UniProt Archive) is a comprehensive, non-redundant protein sequence
archive that stores every unique protein sequence ever seen in major databases
(UniProtKB, RefSeq, Ensembl, PDB, etc.). Each unique sequence gets a stable
UPI identifier. Useful for tracking protein sequences across databases and
identifying all database records sharing an identical sequence.

API: https://rest.uniprot.org/uniparc/
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

UNIPARC_BASE_URL = "https://rest.uniprot.org/uniparc"


@register_tool("UniParcTool")
class UniParcTool(BaseTool):
    """
    Tool for querying UniProt UniParc sequence archive.

    Supports:
    - Get UniParc entry by UPI identifier (cross-references, sequence features)
    - Search UniParc by gene name, organism, database membership

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "get_entry")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the UniParc API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"UniParc API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to UniParc API"}
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            if status == 404:
                return {
                    "error": "Entry not found in UniParc. Check the UPI identifier."
                }
            if status == 400:
                return {"error": "Bad request. Check query syntax."}
            return {"error": f"UniParc API HTTP {status}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "get_entry":
            return self._get_entry(arguments)
        elif self.endpoint == "search":
            return self._search(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _get_entry(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get UniParc entry by UPI identifier."""
        upi = arguments.get("upi", "")
        if not upi:
            return {"error": "upi is required (e.g., 'UPI000002ED67' for TP53)."}

        url = f"{UNIPARC_BASE_URL}/{upi}"
        headers = {"Accept": "application/json"}
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        # Process cross-references (limit to active ones)
        cross_refs = []
        for xref in data.get("uniParcCrossReferences", []):
            if xref.get("active", False):
                organism = xref.get("organism", {})
                cross_refs.append(
                    {
                        "database": xref.get("database"),
                        "id": xref.get("id"),
                        "active": True,
                        "gene_name": xref.get("geneName"),
                        "protein_name": xref.get("proteinName"),
                        "organism": organism.get("scientificName")
                        if organism
                        else None,
                        "taxon_id": organism.get("taxonId") if organism else None,
                    }
                )

        # Process sequence features
        seq_features = []
        for feat in data.get("sequenceFeatures", []):
            interpro = feat.get("interproGroup", {})
            seq_features.append(
                {
                    "database": feat.get("database"),
                    "database_id": feat.get("databaseId"),
                    "interpro_id": interpro.get("id") if interpro else None,
                    "interpro_name": interpro.get("name") if interpro else None,
                    "locations": feat.get("locations", []),
                }
            )

        seq = data.get("sequence", {})
        return {
            "data": {
                "uniparc_id": data.get("uniParcId"),
                "sequence": {
                    "value": seq.get("value"),
                    "length": seq.get("length"),
                    "mol_weight": seq.get("molWeight"),
                    "crc64": seq.get("crc64"),
                    "md5": seq.get("md5"),
                },
                "cross_references": cross_refs[:30],
                "sequence_features": seq_features[:20],
            },
            "metadata": {
                "source": "UniProt UniParc (uniprot.org/uniparc)",
                "total_cross_references": len(data.get("uniParcCrossReferences", [])),
                "active_cross_references": len(cross_refs),
            },
        }

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search UniParc by gene, organism, or database."""
        query = arguments.get("query", "")
        if not query:
            return {
                "error": "query is required (e.g., 'gene:TP53 AND organism_id:9606')."
            }

        size = min(arguments.get("size", 5), 10)
        params = {
            "query": query,
            "size": size,
            "fields": "upi,accession,organism,gene",
        }

        url = f"{UNIPARC_BASE_URL}/search"
        headers = {"Accept": "application/json"}
        response = requests.get(
            url, params=params, headers=headers, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        entries = []
        for entry in results:
            organisms = entry.get("organisms", [])
            gene_names = entry.get("geneNames", [])
            entries.append(
                {
                    "uniparc_id": entry.get("uniParcId"),
                    "uniprot_accessions": entry.get("uniProtKBAccessions", []),
                    "organisms": [
                        {
                            "name": org.get("scientificName"),
                            "taxon_id": org.get("taxonId"),
                        }
                        for org in organisms[:5]
                    ],
                    "gene_names": gene_names[:5],
                    "oldest_created": entry.get("oldestCrossRefCreated"),
                    "most_recent_updated": entry.get("mostRecentCrossRefUpdated"),
                }
            )

        return {
            "data": entries,
            "metadata": {
                "source": "UniProt UniParc (uniprot.org/uniparc)",
                "query": query,
                "returned": len(entries),
            },
        }
