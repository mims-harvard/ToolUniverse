"""
ClinGen Dosage Sensitivity JSON API Tool

Provides access to ClinGen dosage sensitivity curations via the JSON API
at search.clinicalgenome.org. Returns haploinsufficiency and triplosensitivity
scores with genomic coordinates, pLI scores, and disease associations.

This uses the structured JSON API rather than CSV parsing, providing richer
data including genomic coordinates in both GRCh37 and GRCh38.
"""

import requests
from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool

CLINGEN_API_URL = "https://search.clinicalgenome.org/api/dosage"


@register_tool("ClinGenDosageTool")
class ClinGenDosageTool(BaseTool):
    """
    ClinGen Dosage Sensitivity JSON API tool.

    Uses the search.clinicalgenome.org/api/dosage endpoint which returns
    structured JSON with detailed dosage sensitivity curations.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        fields = tool_config.get("fields", {})
        self.operation = fields.get("operation", "")
        self.timeout = fields.get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to operation handler based on config."""
        operation = self.operation or arguments.get("operation")

        if not operation:
            return {"status": "error", "error": "Missing: operation"}

        operation_map = {
            "dosage_by_gene": self._dosage_by_gene,
            "dosage_region_search": self._dosage_region_search,
        }

        handler = operation_map.get(operation)
        if not handler:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

        return handler(arguments)

    def _dosage_by_gene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search ClinGen dosage sensitivity curations by gene symbol."""
        gene = arguments.get("gene")
        if not gene:
            return {"status": "error", "error": "Missing required parameter: gene"}

        try:
            response = requests.get(
                CLINGEN_API_URL,
                params={"search": gene},
                timeout=self.timeout,
            )
            response.raise_for_status()

            data = response.json()
            rows = data.get("rows", [])

            # Filter for exact or close matches
            gene_upper = gene.upper()
            matches = [
                row for row in rows if row.get("symbol", "").upper() == gene_upper
            ]

            # If no exact match, try partial
            if not matches:
                matches = [
                    row for row in rows if gene_upper in row.get("symbol", "").upper()
                ]

            return {
                "status": "success",
                "data": matches,
                "total": len(matches),
                "gene_searched": gene,
                "source": "ClinGen Dosage Sensitivity (JSON API)",
            }
        except requests.exceptions.Timeout:
            return {"status": "error", "error": f"Timeout after {self.timeout}s"}
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _dosage_region_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search dosage curations by genomic region."""
        chromosome = arguments.get("chromosome")
        start = arguments.get("start")
        end = arguments.get("end")
        assembly = arguments.get("assembly", "GRCh38")

        if not all([chromosome, start, end]):
            return {
                "status": "error",
                "error": "Missing required parameters: chromosome, start, end",
            }

        try:
            # Fetch all dosage curations and filter by region overlap
            response = requests.get(
                CLINGEN_API_URL,
                timeout=self.timeout,
            )
            response.raise_for_status()

            data = response.json()
            rows = data.get("rows", [])

            # Use appropriate coordinate field based on assembly
            coord_field = "grch38" if assembly == "GRCh38" else "grch37"

            # Normalize chromosome
            chrom_str = str(chromosome).replace("chr", "")

            # Filter by region overlap
            matches = []
            for row in rows:
                coords = row.get(coord_field, "")
                if not coords:
                    continue

                # Parse coordinates like "chr17:43044295-43125370"
                try:
                    chrom_part, pos_part = coords.split(":")
                    row_chrom = chrom_part.replace("chr", "")
                    row_start, row_end = pos_part.split("-")
                    row_start = int(row_start)
                    row_end = int(row_end)

                    # Check chromosome match and overlap
                    if row_chrom == chrom_str:
                        if row_start <= end and row_end >= start:
                            matches.append(row)
                except (ValueError, IndexError):
                    continue

            return {
                "status": "success",
                "data": matches,
                "total": len(matches),
                "region_queried": f"chr{chrom_str}:{start}-{end}",
                "assembly": assembly,
                "source": "ClinGen Dosage Sensitivity (JSON API)",
            }
        except requests.exceptions.Timeout:
            return {"status": "error", "error": f"Timeout after {self.timeout}s"}
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
