"""
dbSNP REST API Tool

This tool provides access to the dbSNP (Single Nucleotide Polymorphism) database
for variant information, allele frequencies, and genomic coordinates.
"""

from typing import Dict, Any
from .ncbi_eutils_tool import NCBIEUtilsTool
from .tool_registry import register_tool


class dbSNPRESTTool(NCBIEUtilsTool):
    """Base class for dbSNP REST API tools with rate limiting."""


@register_tool("dbSNPGetVariantByRsID")
class dbSNPGetVariantByRsID(dbSNPRESTTool):
    """Get variant information by rsID."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/esummary.fcgi"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get variant by rsID using E-utilities."""
        rsid = arguments.get("rsid", "")
        if not rsid:
            return {"status": "error", "error": "rsid is required"}

        # Remove 'rs' prefix if present
        if rsid.startswith("rs"):
            rsid = rsid[2:]

        params = {"db": "snp", "id": rsid, "retmode": "json"}

        result = self._make_request(self.endpoint, params)

        # Parse and extract useful data from NCBI response
        if result.get("status") == "success":
            data = result.get("data", {})
            if isinstance(data, dict) and "result" in data:
                result_data = data["result"]
                if rsid in result_data:
                    variant_data = result_data[rsid]

                    # Extract key information
                    parsed_data = {
                        "refsnp_id": f"rs{rsid}",
                        "snp_id": variant_data.get("snp_id"),
                        "chromosome": variant_data.get("chr"),
                        "position": variant_data.get("chrpos"),
                        "allele": variant_data.get("allele"),
                        "snp_class": variant_data.get("snp_class"),
                        "clinical_significance": variant_data.get(
                            "clinical_significance", ""
                        ).split(","),
                        "genes": [
                            gene.get("name") for gene in variant_data.get("genes", [])
                        ],
                        "allele_frequencies": variant_data.get("global_mafs", []),
                        "hgvs_notation": variant_data.get("docsum", ""),
                        "spdi_notation": variant_data.get("spdi", ""),
                        "function_class": variant_data.get("fxn_class", "").split(","),
                        "validated": variant_data.get("validated", "").split(","),
                        "created_date": variant_data.get("createdate"),
                        "updated_date": variant_data.get("updatedate"),
                    }

                    result["data"] = parsed_data
                    result["rsid"] = f"rs{rsid}"
                else:
                    result["status"] = "error"
                    result["error"] = f"Variant rs{rsid} not found in dbSNP"
            else:
                result["status"] = "error"
                result["error"] = "Invalid response format from NCBI E-utilities"

        return result


@register_tool("dbSNPSearchByGene")
class dbSNPSearchByGene(dbSNPRESTTool):
    """Search variants by gene symbol."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/esearch.fcgi"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search variants by gene using E-utilities."""
        gene_symbol = arguments.get("gene_symbol", "")
        if not gene_symbol:
            return {"status": "error", "error": "gene_symbol is required"}

        params = {
            "db": "snp",
            "term": f"{gene_symbol}[gene]",
            "retmode": "json",
            "retmax": arguments.get("limit", 20),
        }

        result = self._make_request(self.endpoint, params)

        # Parse and extract useful data from NCBI response
        if result.get("status") == "success":
            data = result.get("data", {})
            if isinstance(data, dict) and "esearchresult" in data:
                esearch_data = data["esearchresult"]

                # Extract variant IDs
                variant_ids = esearch_data.get("idlist", [])
                count = int(esearch_data.get("count", 0))

                # Create variant list with basic info
                variants = []
                for variant_id in variant_ids:
                    variants.append(
                        {"refsnp_id": f"rs{variant_id}", "snp_id": int(variant_id)}
                    )

                parsed_data = {
                    "variants": variants,
                    "total_count": count,
                    "returned_count": len(variants),
                }

                result["data"] = parsed_data
                result["gene_symbol"] = gene_symbol
            else:
                result["status"] = "error"
                result["error"] = "Invalid response format from NCBI E-utilities"

        return result


@register_tool("dbSNPGetFrequencies")
class dbSNPGetFrequencies(dbSNPRESTTool):
    """Get allele frequencies for a variant."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/esummary.fcgi"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get allele frequencies by rsID using E-utilities."""
        rsid = arguments.get("rsid", "")
        if not rsid:
            return {"status": "error", "error": "rsid is required"}

        # Remove 'rs' prefix if present
        if rsid.startswith("rs"):
            rsid = rsid[2:]

        params = {"db": "snp", "id": rsid, "retmode": "json"}

        result = self._make_request(self.endpoint, params)

        # Parse and extract frequency data from NCBI response
        if result.get("status") == "success":
            data = result.get("data", {})
            if isinstance(data, dict) and "result" in data:
                result_data = data["result"]
                if rsid in result_data:
                    variant_data = result_data[rsid]

                    # Extract allele frequency data
                    frequencies = []
                    global_mafs = variant_data.get("global_mafs", [])

                    for maf in global_mafs:
                        study = maf.get("study", "Unknown")
                        freq_str = maf.get("freq", "")

                        # Parse frequency string (e.g., "C=0.1505591/754")
                        if "=" in freq_str and "/" in freq_str:
                            try:
                                allele_part, count_part = freq_str.split("/")
                                allele = allele_part.split("=")[0]
                                frequency = float(allele_part.split("=")[1])
                                sample_count = int(count_part)

                                frequencies.append(
                                    {
                                        "study": study,
                                        "allele": allele,
                                        "frequency": frequency,
                                        "sample_count": sample_count,
                                    }
                                )
                            except (ValueError, IndexError):
                                # Skip malformed frequency entries
                                continue

                    parsed_data = {
                        "frequencies": frequencies,
                        "total_studies": len(frequencies),
                    }

                    result["data"] = parsed_data
                    result["rsid"] = f"rs{rsid}"
                else:
                    result["status"] = "error"
                    result["error"] = f"Variant rs{rsid} not found in dbSNP"
            else:
                result["status"] = "error"
                result["error"] = "Invalid response format from NCBI E-utilities"

        return result
