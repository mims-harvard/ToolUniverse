# uniref_tool.py
"""
UniProt UniRef Clusters API tool for ToolUniverse.

UniRef provides clustered sets of protein sequences at different levels
of sequence identity: UniRef100, UniRef90, and UniRef50. These clusters
group related sequences to reduce redundancy and improve search speed.

API: https://rest.uniprot.org/uniref/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

UNIREF_BASE_URL = "https://rest.uniprot.org/uniref"


@register_tool("UniRefTool")
class UniRefTool(BaseTool):
    """
    Tool for querying UniProt UniRef protein sequence clusters.

    Supports:
    - Get cluster details by ID (UniRef90_XXXXX, UniRef50_XXXXX, UniRef100_XXXXX)
    - Search clusters by protein name, gene, or organism

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "get_cluster")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the UniRef API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"UniRef API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to UniRef API"}
        except requests.exceptions.HTTPError as e:
            return {"error": f"UniRef API HTTP error: {e.response.status_code}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "get_cluster":
            return self._get_cluster(arguments)
        elif self.endpoint == "search_clusters":
            return self._search_clusters(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _get_cluster(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get UniRef cluster details by cluster ID."""
        cluster_id = arguments.get("cluster_id", "")
        if not cluster_id:
            return {
                "error": "cluster_id parameter is required (e.g., 'UniRef90_P04637')"
            }

        cluster_id = cluster_id.strip()

        url = f"{UNIREF_BASE_URL}/{cluster_id}"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        # Parse representative member
        rep = data.get("representativeMember") or {}
        representative = {
            "member_id": rep.get("memberId"),
            "member_id_type": rep.get("memberIdType"),
            "organism_name": rep.get("organismName"),
            "organism_tax_id": rep.get("organismTaxId"),
            "sequence_length": rep.get("sequenceLength"),
            "protein_name": rep.get("proteinName"),
            "accessions": rep.get("accessions", []),
        }

        # Sequence info
        seq_obj = rep.get("sequence") or {}
        sequence = seq_obj.get("value")
        sequence_length = seq_obj.get("length")

        # Common taxon
        common_taxon = data.get("commonTaxon") or {}

        return {
            "data": {
                "cluster_id": data.get("id"),
                "name": data.get("name"),
                "entry_type": data.get("entryType"),
                "member_count": data.get("memberCount"),
                "updated": data.get("updated"),
                "seed_id": data.get("seedId"),
                "common_taxon": {
                    "scientific_name": common_taxon.get("scientificName"),
                    "taxon_id": common_taxon.get("taxonId"),
                },
                "representative_member": representative,
                "sequence": sequence,
                "sequence_length": sequence_length
                or representative.get("sequence_length"),
            },
            "metadata": {
                "source": "UniProt UniRef",
                "cluster_id": cluster_id,
            },
        }

    def _search_clusters(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search UniRef clusters by protein name, gene, or organism."""
        query = arguments.get("query", "")
        if not query:
            return {
                "error": "query parameter is required (e.g., 'p53', 'insulin', 'kinase Homo sapiens')"
            }

        cluster_type = arguments.get("cluster_type") or "UniRef90"
        size = min(arguments.get("size") or 10, 25)

        # Build the search query with identity filter
        # UniRef API uses decimal identity: 1.0 (UniRef100), 0.9 (UniRef90), 0.5 (UniRef50)
        identity_map = {
            "UniRef100": "1.0",
            "UniRef90": "0.9",
            "UniRef50": "0.5",
        }
        search_query = query
        identity_val = identity_map.get(cluster_type)
        if identity_val:
            search_query = f"{query} AND identity:{identity_val}"

        url = f"{UNIREF_BASE_URL}/search"
        params = {
            "query": search_query,
            "size": size,
        }

        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        results_raw = data.get("results", [])
        results = []
        for cluster in results_raw:
            rep = cluster.get("representativeMember") or {}
            common_taxon = cluster.get("commonTaxon") or {}

            results.append(
                {
                    "cluster_id": cluster.get("id"),
                    "name": cluster.get("name"),
                    "entry_type": cluster.get("entryType"),
                    "member_count": cluster.get("memberCount"),
                    "updated": cluster.get("updated"),
                    "representative_member_id": rep.get("memberId"),
                    "representative_organism": rep.get("organismName"),
                    "representative_protein": rep.get("proteinName"),
                    "representative_sequence_length": rep.get("sequenceLength"),
                    "common_taxon": common_taxon.get("scientificName"),
                }
            )

        return {
            "data": results,
            "metadata": {
                "source": "UniProt UniRef",
                "query": query,
                "cluster_type": cluster_type,
                "returned": len(results),
            },
        }
