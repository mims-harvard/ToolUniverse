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
from .uniprot_pagination import pagination_metadata

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
            return {
                "status": "error",
                "error": f"UniParc API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to UniParc API"}
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            if status == 404:
                return {
                    "status": "error",
                    "error": "Entry not found in UniParc. Check the UPI identifier.",
                }
            if status == 400:
                return {"status": "error", "error": "Bad request. Check query syntax."}
            return {"status": "error", "error": f"UniParc API HTTP {status}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "get_entry":
            return self._get_entry(arguments)
        elif self.endpoint == "search":
            return self._search(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _get_entry(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get UniParc entry by UPI identifier."""
        upi = arguments.get("upi", "")
        if not upi:
            return {
                "status": "error",
                "error": "upi is required (e.g., 'UPI000002ED67' for TP53).",
            }

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
        cross_reference_offset = max(arguments.get("cross_reference_offset") or 0, 0)
        cross_reference_limit = min(
            max(arguments.get("cross_reference_limit") or 100, 1), 500
        )
        feature_offset = max(arguments.get("feature_offset") or 0, 0)
        feature_limit = min(max(arguments.get("feature_limit") or 100, 1), 500)
        cross_reference_page = cross_refs[
            cross_reference_offset : cross_reference_offset + cross_reference_limit
        ]
        feature_page = seq_features[feature_offset : feature_offset + feature_limit]
        cross_reference_has_more = cross_reference_offset + len(
            cross_reference_page
        ) < len(cross_refs)
        feature_has_more = feature_offset + len(feature_page) < len(seq_features)

        return {
            "status": "success",
            "data": {
                "uniparc_id": data.get("uniParcId"),
                "sequence": {
                    "value": seq.get("value"),
                    "length": seq.get("length"),
                    "mol_weight": seq.get("molWeight"),
                    "crc64": seq.get("crc64"),
                    "md5": seq.get("md5"),
                },
                "cross_references": cross_reference_page,
                "sequence_features": feature_page,
            },
            "metadata": {
                "source": "UniProt UniParc (uniprot.org/uniparc)",
                "total_cross_references": len(data.get("uniParcCrossReferences", [])),
                "active_cross_references": len(cross_refs),
                "cross_references_returned": len(cross_reference_page),
                "cross_reference_offset": cross_reference_offset,
                "cross_references_truncated": cross_reference_has_more,
                "next_cross_reference_offset": (
                    cross_reference_offset + len(cross_reference_page)
                    if cross_reference_has_more
                    else None
                ),
                "total_sequence_features": len(seq_features),
                "sequence_features_returned": len(feature_page),
                "feature_offset": feature_offset,
                "sequence_features_truncated": feature_has_more,
                "next_feature_offset": (
                    feature_offset + len(feature_page) if feature_has_more else None
                ),
            },
        }

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search UniParc by gene, organism, or database."""
        query = arguments.get("query", "")
        if not query:
            return {
                "status": "error",
                "error": "query is required (e.g., 'gene:TP53 AND organism_id:9606').",
            }

        raw_size = arguments.get("size")
        raw_size = 5 if raw_size is None else raw_size
        try:
            if isinstance(raw_size, bool):
                raise ValueError
            size = int(raw_size)
            if isinstance(raw_size, float) and not raw_size.is_integer():
                raise ValueError
            if not 1 <= size <= 500:
                raise ValueError
        except (TypeError, ValueError):
            return {
                "status": "error",
                "error": "size must be an integer from 1 to 500",
            }
        params = {
            "query": query,
            "size": size,
            "fields": "upi,accession,organism,gene",
        }
        if arguments.get("cursor"):
            params["cursor"] = arguments["cursor"]

        url = f"{UNIPARC_BASE_URL}/search"
        headers = {"Accept": "application/json"}
        response = requests.get(
            url, params=params, headers=headers, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        organism_offset = max(int(arguments.get("organism_offset") or 0), 0)
        organism_limit = min(max(int(arguments.get("organism_limit") or 100), 1), 500)
        gene_name_offset = max(int(arguments.get("gene_name_offset") or 0), 0)
        gene_name_limit = min(max(int(arguments.get("gene_name_limit") or 100), 1), 500)
        entries = []
        for entry in results:
            organisms = entry.get("organisms", [])
            gene_names = entry.get("geneNames", [])
            organism_page = organisms[
                organism_offset : organism_offset + organism_limit
            ]
            gene_name_page = gene_names[
                gene_name_offset : gene_name_offset + gene_name_limit
            ]
            organisms_truncated = organism_offset + len(organism_page) < len(organisms)
            gene_names_truncated = gene_name_offset + len(gene_name_page) < len(
                gene_names
            )
            entries.append(
                {
                    "uniparc_id": entry.get("uniParcId"),
                    "uniprot_accessions": entry.get("uniProtKBAccessions", []),
                    "organisms": [
                        {
                            "name": org.get("scientificName"),
                            "taxon_id": org.get("taxonId"),
                        }
                        for org in organism_page
                    ],
                    "organisms_total": len(organisms),
                    "organisms_returned": len(organism_page),
                    "organisms_truncated": organisms_truncated,
                    "next_organism_offset": (
                        organism_offset + len(organism_page)
                        if organisms_truncated
                        else None
                    ),
                    "gene_names": gene_name_page,
                    "gene_names_total": len(gene_names),
                    "gene_names_returned": len(gene_name_page),
                    "gene_names_truncated": gene_names_truncated,
                    "next_gene_name_offset": (
                        gene_name_offset + len(gene_name_page)
                        if gene_names_truncated
                        else None
                    ),
                    "oldest_created": entry.get("oldestCrossRefCreated"),
                    "most_recent_updated": entry.get("mostRecentCrossRefUpdated"),
                }
            )

        return {
            "status": "success",
            "data": entries,
            "metadata": {
                "source": "UniProt UniParc (uniprot.org/uniparc)",
                "query": query,
                **pagination_metadata(response, len(entries)),
            },
        }
