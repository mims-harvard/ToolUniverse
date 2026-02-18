# ebi_proteins_epitope_tool.py
"""
EBI Proteins API - Epitope endpoint tool for ToolUniverse.

This tool provides access to experimentally-determined epitope regions
on proteins, sourced from the Immune Epitope Database (IEDB). Epitope
data is critical for immunology research, vaccine design, and
understanding immune responses to proteins.

API: https://www.ebi.ac.uk/proteins/api/
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

EBI_PROTEINS_BASE_URL = "https://www.ebi.ac.uk/proteins/api"


@register_tool("EBIProteinsEpitopeTool")
class EBIProteinsEpitopeTool(BaseTool):
    """
    Tool for querying protein epitope data from the EBI Proteins API.

    Epitopes are regions of proteins recognized by the immune system
    (antibodies, T cells). This tool retrieves experimentally-determined
    epitope regions from the Immune Epitope Database (IEDB), including
    epitope sequences, positions, and supporting literature.

    Useful for: vaccine design, therapeutic antibody development,
    immunogenicity assessment, B-cell/T-cell epitope mapping.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the EBI Proteins epitope API call."""
        try:
            return self._get_epitopes(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"EBI Proteins API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to EBI Proteins API"}
        except requests.exceptions.HTTPError as e:
            return {"error": f"EBI Proteins API HTTP error: {e.response.status_code}"}
        except Exception as e:
            return {"error": f"Unexpected error querying EBI Proteins: {str(e)}"}

    def _get_epitopes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get epitope features for a protein by UniProt accession."""
        accession = arguments.get("accession", "")
        if not accession:
            return {
                "error": "accession parameter is required (UniProt accession, e.g., P04637)"
            }

        url = f"{EBI_PROTEINS_BASE_URL}/epitope/{accession}"
        headers = {"Accept": "application/json"}

        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        # Extract epitope features
        features = data.get("features", [])
        epitopes = []
        for f in features:
            evidences = f.get("evidences", [])
            pmids = []
            iedb_ids = []
            for ev in evidences:
                src = ev.get("source", {})
                if src.get("name") == "PubMed":
                    pmids.append(src.get("id"))
                if src.get("name") == "IEDB":
                    iedb_ids.append(src.get("id"))

            begin_val = f.get("begin")
            end_val = f.get("end")
            epitopes.append(
                {
                    "type": f.get("type"),
                    "begin": int(begin_val) if begin_val is not None else None,
                    "end": int(end_val) if end_val is not None else None,
                    "sequence": f.get("epitopeSequence"),
                    "match_score": f.get("matchScore"),
                    "description": f.get("description"),
                    "pmids": pmids[:5],
                    "iedb_ids": iedb_ids[:3],
                }
            )

        return {
            "data": {
                "accession": data.get("accession"),
                "entry_name": data.get("entryName"),
                "taxid": data.get("taxid"),
                "total_epitopes": len(epitopes),
                "epitopes": epitopes,
            },
            "metadata": {
                "source": "EBI Proteins API (IEDB epitopes)",
                "accession": accession,
                "sequence_length": len(data.get("sequence", "")),
            },
        }
