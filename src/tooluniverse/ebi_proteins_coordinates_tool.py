# ebi_proteins_coordinates_tool.py
"""
EBI Proteins Coordinates tool for ToolUniverse.

The EBI Proteins API Coordinates endpoint maps UniProt protein positions to
genomic coordinates at exon-level resolution. This enables translation between
protein residue numbering and chromosomal positions, essential for connecting
variant-level information across protein and genome databases.

API: https://www.ebi.ac.uk/proteins/api/coordinates/
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

EBI_PROTEINS_BASE_URL = "https://www.ebi.ac.uk/proteins/api"


@register_tool("EBIProteinsCoordinatesTool")
class EBIProteinsCoordinatesTool(BaseTool):
    """
    Tool for querying EBI Proteins API coordinate mappings.

    Supports:
    - Map protein positions to genomic coordinates (exon-level)
    - Get protein-to-genome coordinate mappings for a UniProt accession

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "get_coordinates")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the EBI Proteins Coordinates API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"EBI Proteins API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to EBI Proteins API"}
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            if status == 404:
                return {
                    "error": "Protein not found. Provide a valid UniProt accession (e.g., 'P04637' for TP53)."
                }
            if status == 400:
                return {"error": "Bad request. Check the UniProt accession format."}
            return {"error": f"EBI Proteins API HTTP {status}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "get_coordinates":
            return self._get_coordinates(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _get_coordinates(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get protein-to-genomic coordinate mappings."""
        accession = arguments.get("accession", "")
        if not accession:
            return {
                "error": "accession is required (UniProt accession, e.g., 'P04637' for TP53, 'P00533' for EGFR)."
            }

        accession = accession.strip()
        url = f"{EBI_PROTEINS_BASE_URL}/coordinates/{accession}"
        response = requests.get(
            url, timeout=self.timeout, headers={"Accept": "application/json"}
        )
        response.raise_for_status()
        data = response.json()

        # Extract gene info
        gene_info = []
        for g in data.get("gene", []):
            gene_info.append(
                {
                    "value": g.get("value"),
                    "type": g.get("type"),
                }
            )

        # Extract genomic coordinates
        gn_coordinates = data.get("gnCoordinate", [])
        mappings = []
        for gc in gn_coordinates[:10]:  # Limit to 10 transcript mappings
            genomic_loc = gc.get("genomicLocation", {})
            exons = genomic_loc.get("exon", [])

            exon_mappings = []
            for exon in exons[:20]:
                prot_loc = exon.get("proteinLocation", {})
                genome_loc = exon.get("genomeLocation", {})
                exon_mappings.append(
                    {
                        "exon_id": exon.get("id"),
                        "protein_start": prot_loc.get("begin", {}).get("position"),
                        "protein_end": prot_loc.get("end", {}).get("position"),
                        "genome_start": genome_loc.get("begin", {}).get("position"),
                        "genome_end": genome_loc.get("end", {}).get("position"),
                    }
                )

            mappings.append(
                {
                    "ensembl_gene_id": gc.get("ensemblGeneId"),
                    "ensembl_transcript_id": gc.get("ensemblTranscriptId"),
                    "ensembl_translation_id": gc.get("ensemblTranslationId"),
                    "chromosome": genomic_loc.get("chromosome"),
                    "start": genomic_loc.get("start"),
                    "end": genomic_loc.get("end"),
                    "reverse_strand": genomic_loc.get("reverseStrand"),
                    "num_exons": len(exons),
                    "exons": exon_mappings,
                }
            )

        return {
            "data": {
                "accession": data.get("accession"),
                "protein_name": data.get("name"),
                "taxid": data.get("taxid"),
                "gene": gene_info,
                "coordinate_mappings": mappings,
            },
            "metadata": {
                "source": "EBI Proteins API (ebi.ac.uk/proteins/api)",
                "total_transcript_mappings": len(gn_coordinates),
                "returned_mappings": len(mappings),
            },
        }
