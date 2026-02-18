# ensembl_map_tool.py
"""
Ensembl Assembly Mapping tool for ToolUniverse.

Provides coordinate conversion between genome assemblies (e.g., GRCh37 to GRCh38)
and mapping of protein/cDNA positions to genomic coordinates.

API: https://rest.ensembl.org
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

ENSEMBL_BASE_URL = "https://rest.ensembl.org"
ENSEMBL_HEADERS = {"User-Agent": "ToolUniverse/1.0", "Accept": "application/json"}


@register_tool("EnsemblMapTool")
class EnsemblMapTool(BaseTool):
    """
    Tool for Ensembl coordinate mapping operations.

    Supports:
    - Assembly-to-assembly coordinate conversion (GRCh37 <-> GRCh38)
    - Protein position to genomic coordinate mapping
    - cDNA position to genomic coordinate mapping

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 90)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "assembly_map")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Ensembl mapping API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"Ensembl API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to Ensembl REST API"}
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            text = ""
            if e.response is not None:
                try:
                    text = e.response.json().get("error", "")
                except Exception:
                    text = e.response.text[:200]
            return {"error": f"Ensembl API HTTP {status}: {text}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "assembly_map":
            return self._assembly_map(arguments)
        elif self.endpoint == "translate_coords":
            return self._translate_coords(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _assembly_map(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Convert coordinates between genome assemblies."""
        species = arguments.get("species", "human")
        source_asm = arguments.get("source_assembly")
        chrom = arguments.get("chromosome")
        start = arguments.get("start")
        end = arguments.get("end")
        target_asm = arguments.get("target_assembly")

        if not all([source_asm, chrom, start, end, target_asm]):
            return {
                "error": "source_assembly, chromosome, start, end, and target_assembly are all required."
            }

        url = f"{ENSEMBL_BASE_URL}/map/{species}/{source_asm}/{chrom}:{start}..{end}/{target_asm}"
        response = requests.get(
            url,
            params={"content-type": "application/json"},
            headers=ENSEMBL_HEADERS,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        mappings = data.get("mappings", [])

        return {
            "data": {
                "mappings": [
                    {
                        "original": m.get("original", {}),
                        "mapped": m.get("mapped", {}),
                    }
                    for m in mappings
                ]
            },
            "metadata": {
                "source": "Ensembl REST API (rest.ensembl.org)",
                "total_mappings": len(mappings),
            },
        }

    def _translate_coords(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Map protein or cDNA positions to genomic coordinates."""
        ensembl_id = arguments.get("ensembl_id", "")
        start = arguments.get("start")
        end = arguments.get("end")

        if not ensembl_id or start is None or end is None:
            return {"error": "ensembl_id, start, and end are all required."}

        # Determine if this is a protein (ENSP) or transcript (ENST) ID
        if ensembl_id.startswith("ENSP"):
            coord_type = "translation"
        elif ensembl_id.startswith("ENST"):
            coord_type = "cdna"
        else:
            coord_type = "cdna"  # Default to cDNA

        url = f"{ENSEMBL_BASE_URL}/map/{coord_type}/{ensembl_id}/{start}..{end}"
        response = requests.get(
            url,
            params={"content-type": "application/json"},
            headers=ENSEMBL_HEADERS,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        mappings = data.get("mappings", [])

        return {
            "data": {
                "mappings": [
                    {
                        "seq_region_name": m.get("seq_region_name"),
                        "start": m.get("start"),
                        "end": m.get("end"),
                        "strand": m.get("strand"),
                        "coord_system": m.get("coord_system"),
                    }
                    for m in mappings
                ]
            },
            "metadata": {
                "source": "Ensembl REST API (rest.ensembl.org)",
                "query_id": ensembl_id,
                "coordinate_type": "protein" if coord_type == "translation" else "cDNA",
                "total_mappings": len(mappings),
            },
        }
