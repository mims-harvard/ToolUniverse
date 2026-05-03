"""
ClinGen Database REST API Tool

This tool provides access to ClinGen (Clinical Genome Resource) data including:
- Gene-Disease Validity curations
- Dosage Sensitivity curations
- Clinical Actionability curations
- Variant Pathogenicity data

ClinGen is a NIH-funded resource providing authoritative information on
gene-disease relationships for use in clinical genomics.
"""

import requests
import csv
import io
from typing import Dict, Any, List, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URLs for ClinGen APIs
CLINGEN_BASE_URL = "https://search.clinicalgenome.org"
ACTIONABILITY_ADULT_URL = "https://actionability.clinicalgenome.org/ac/Adult/api"
ACTIONABILITY_PEDIATRIC_URL = (
    "https://actionability.clinicalgenome.org/ac/Pediatric/api"
)
EREPO_BASE_URL = "https://erepo.clinicalgenome.org/evrepo/api"


@register_tool("ClinGenTool")
class ClinGenTool(BaseTool):
    """
    ClinGen Database REST API tool.

    Provides access to ClinGen curated data including gene-disease validity,
    dosage sensitivity, and clinical actionability.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        fields = tool_config.get("fields", {})
        self.operation = fields.get("operation", "")
        self.timeout = fields.get("timeout", 60)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to operation handler based on config."""
        operation = self.operation or arguments.get("operation")

        if not operation:
            return {"status": "error", "error": "Missing: operation"}

        operation_map = {
            "get_gene_validity": self._get_gene_validity,
            "search_gene_validity": self._search_gene_validity,
            "get_dosage_sensitivity": self._get_dosage_sensitivity,
            "search_dosage_sensitivity": self._search_dosage_sensitivity,
            "get_actionability_adult": self._get_actionability_adult,
            "get_actionability_pediatric": self._get_actionability_pediatric,
            "search_actionability": self._search_actionability,
            "get_variant_classifications": self._get_variant_classifications,
        }

        handler = operation_map.get(operation)
        if not handler:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

        return handler(arguments)

    def _get_gene_validity(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get all gene-disease validity curations from ClinGen."""
        try:
            url = f"{CLINGEN_BASE_URL}/kb/gene-validity/download"

            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()

            # Parse CSV response
            curations = self._parse_csv(response.text)

            # Optional filtering by gene
            gene = arguments.get("gene")
            if gene:
                gene_upper = gene.upper()
                # Handle both "GENE SYMBOL" (from CSV) and "Gene Symbol" key formats
                curations = [
                    c
                    for c in curations
                    if c.get("GENE SYMBOL", c.get("Gene Symbol", "")).upper()
                    == gene_upper
                ]

            return {
                "status": "success",
                "data": curations[:100],  # Limit to first 100 for performance
                "total": len(curations),
                "source": "ClinGen Gene-Disease Validity",
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

    def _search_gene_validity(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search gene-disease validity curations by gene symbol."""
        gene = arguments.get("gene")
        if not gene:
            return {"status": "error", "error": "Missing required parameter: gene"}

        try:
            url = f"{CLINGEN_BASE_URL}/kb/gene-validity/download"

            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()

            # Parse CSV response
            curations = self._parse_csv(response.text)

            # Filter by gene symbol (case-insensitive)
            # Handle both "GENE SYMBOL" (from CSV) and "Gene Symbol" key formats
            gene_upper = gene.upper()
            matches = []
            for c in curations:
                gene_val = c.get("GENE SYMBOL", c.get("Gene Symbol", ""))
                if gene_upper in gene_val.upper():
                    matches.append(c)

            return {
                "status": "success",
                "data": matches,
                "total": len(matches),
                "gene_searched": gene,
                "source": "ClinGen Gene-Disease Validity",
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

    def _get_dosage_sensitivity(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get all dosage sensitivity curations from ClinGen."""
        include_regions = arguments.get("include_regions", False)

        try:
            if include_regions:
                url = f"{CLINGEN_BASE_URL}/kb/gene-dosage/downloadall"
            else:
                url = f"{CLINGEN_BASE_URL}/kb/gene-dosage/download"

            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()

            # Parse CSV response
            curations = self._parse_csv(response.text)

            # Optional filtering by gene
            gene = arguments.get("gene")
            if gene:
                gene_upper = gene.upper()
                # Handle both "GENE SYMBOL" and "Gene Symbol" key formats
                curations = [
                    c
                    for c in curations
                    if gene_upper
                    in c.get("GENE SYMBOL", c.get("Gene Symbol", "")).upper()
                ]

            return {
                "status": "success",
                "data": curations[:100],  # Limit for performance
                "total": len(curations),
                "include_regions": include_regions,
                "source": "ClinGen Dosage Sensitivity",
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

    def _search_dosage_sensitivity(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search dosage sensitivity curations by gene symbol."""
        gene = arguments.get("gene")
        if not gene:
            return {"status": "error", "error": "Missing required parameter: gene"}

        try:
            # Use the simpler download endpoint (genes only) for searching
            url = f"{CLINGEN_BASE_URL}/kb/gene-dosage/download"

            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()

            # Parse CSV response
            curations = self._parse_csv(response.text)

            # Filter by gene symbol (case-insensitive)
            # Handle different column name formats from different endpoints
            gene_upper = gene.upper()
            matches = []
            for c in curations:
                gene_val = c.get(
                    "GENE SYMBOL", c.get("GENE/REGION", c.get("Gene Symbol", ""))
                )
                if gene_upper in gene_val.upper():
                    matches.append(c)

            return {
                "status": "success",
                "data": matches,
                "total": len(matches),
                "gene_searched": gene,
                "source": "ClinGen Dosage Sensitivity",
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

    def _get_actionability_adult(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get clinical actionability curations for adult context."""
        return self._get_actionability(arguments, "Adult")

    def _get_actionability_pediatric(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get clinical actionability curations for pediatric context."""
        return self._get_actionability(arguments, "Pediatric")

    def _get_actionability(
        self, arguments: Dict[str, Any], context: str
    ) -> Dict[str, Any]:
        """Get clinical actionability curations for a specific context."""
        try:
            base_url = (
                ACTIONABILITY_ADULT_URL
                if context == "Adult"
                else ACTIONABILITY_PEDIATRIC_URL
            )

            # Use flat format for easier parsing
            url = f"{base_url}/summ?flavor=flat"

            headers = {"Accept": "application/json"}
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()

            # Extract curations from the response
            curations = data if isinstance(data, list) else data.get("data", data)

            # Optional filtering by gene
            gene = arguments.get("gene")
            if gene and isinstance(curations, list):
                gene_upper = gene.upper()
                curations = [
                    c
                    for c in curations
                    if gene_upper in str(c.get("gene", "")).upper()
                    or gene_upper in str(c.get("Gene", "")).upper()
                    or gene_upper in str(c.get("hgncId", "")).upper()
                ]

            return {
                "status": "success",
                "data": curations[:100] if isinstance(curations, list) else curations,
                "total": len(curations) if isinstance(curations, list) else 1,
                "context": context,
                "source": f"ClinGen Clinical Actionability ({context})",
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

    def _search_actionability(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search clinical actionability across both adult and pediatric contexts."""
        gene = arguments.get("gene")
        if not gene:
            return {"status": "error", "error": "Missing required parameter: gene"}

        try:
            results = {"Adult": [], "Pediatric": []}

            for context, base_url in [
                ("Adult", ACTIONABILITY_ADULT_URL),
                ("Pediatric", ACTIONABILITY_PEDIATRIC_URL),
            ]:
                try:
                    url = f"{base_url}/summ?flavor=flat"
                    headers = {"Accept": "application/json"}
                    response = requests.get(url, headers=headers, timeout=self.timeout)
                    response.raise_for_status()

                    data = response.json()
                    curations = (
                        data if isinstance(data, list) else data.get("data", data)
                    )

                    # Filter by gene
                    gene_upper = gene.upper()
                    if isinstance(curations, list):
                        matches = [
                            c
                            for c in curations
                            if gene_upper in str(c.get("gene", "")).upper()
                            or gene_upper in str(c.get("Gene", "")).upper()
                        ]
                        results[context] = matches
                except Exception:
                    # Continue with other context if one fails
                    pass

            return {
                "status": "success",
                "data": results,
                "gene_searched": gene,
                "adult_count": len(results["Adult"]),
                "pediatric_count": len(results["Pediatric"]),
                "source": "ClinGen Clinical Actionability",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _get_variant_classifications(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get variant pathogenicity classifications from ClinGen Evidence Repository."""
        try:
            url = f"{EREPO_BASE_URL}/classifications/all"

            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()

            # API returns TSV (tab-separated) with first line starting with #
            tsv_text = response.text
            lines = tsv_text.strip().split("\n")

            # Strip leading # from header line
            if lines and lines[0].startswith("#"):
                lines[0] = lines[0][1:]

            data = []
            if len(lines) > 1:
                reader = csv.DictReader(io.StringIO("\n".join(lines)), delimiter="\t")
                for row in reader:
                    cleaned = {k.strip(): v.strip() for k, v in row.items() if k and v}
                    if cleaned:
                        data.append(cleaned)

            # Optional filtering by gene
            gene = arguments.get("gene")
            if gene:
                gene_upper = gene.upper()
                data = [
                    v
                    for v in data
                    if gene_upper in str(v.get("HGNC Gene Symbol", "")).upper()
                ]

            # Optional filtering by variant
            variant = arguments.get("variant")
            if variant:
                variant_str = str(variant).upper()
                data = [
                    v
                    for v in data
                    if variant_str in str(v.get("Variation", "")).upper()
                    or variant_str in str(v.get("HGVS Expressions", "")).upper()
                ]

            result = {
                "status": "success",
                "data": data[:100],
                "total": len(data),
                "source": "ClinGen Evidence Repository",
            }
            if not data and gene:
                result["note"] = (
                    f"No variant classifications found for {gene}. "
                    "The ClinGen Evidence Repository only contains variants "
                    "curated by Variant Curation Expert Panels (VCEPs). "
                    "Not all genes have active VCEPs. Try ClinGen_get_gene_validity "
                    "for gene-disease validity or clinvar_search_variants for "
                    "ClinVar variant classifications."
                )
            return result
        except requests.exceptions.Timeout:
            return {"status": "error", "error": f"Timeout after {self.timeout}s"}
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _parse_csv(self, csv_text: str) -> List[Dict[str, Any]]:
        """Parse CSV text into list of dictionaries.

        Handles ClinGen's special CSV format which has metadata headers
        before the actual data rows.
        """
        result = []
        try:
            lines = csv_text.strip().split("\n")

            # Find the header row (contains "GENE SYMBOL" or similar)
            header_idx = None
            for i, line in enumerate(lines):
                if "GENE SYMBOL" in line.upper():
                    header_idx = i
                    break

            if header_idx is None:
                # Fallback - try standard CSV parsing
                reader = csv.DictReader(io.StringIO(csv_text))
                for row in reader:
                    cleaned = {k: v for k, v in row.items() if v and k}
                    if cleaned:
                        result.append(cleaned)
                return result

            # Find where actual data starts (skip separator row after header)
            data_start = header_idx + 1
            if data_start < len(lines) and "+++++" in lines[data_start]:
                data_start += 1

            # Build new CSV content: header + data rows
            header_line = lines[header_idx]
            data_lines = [line for line in lines[data_start:] if "+++++" not in line]
            csv_content = header_line + "\n" + "\n".join(data_lines)

            # Use StringIO to read CSV from string
            reader = csv.DictReader(io.StringIO(csv_content))
            for row in reader:
                # Clean up the row - remove empty values
                cleaned = {}
                for k, v in row.items():
                    if v and k:
                        # Strip whitespace
                        k = k.strip()
                        v = v.strip()
                        if v:
                            cleaned[k] = v
                if cleaned and len(cleaned) > 2:  # Must have meaningful data
                    result.append(cleaned)
        except Exception:
            # Log but don't fail
            pass
        return result
