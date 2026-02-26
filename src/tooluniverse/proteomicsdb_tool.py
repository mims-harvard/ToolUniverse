"""
ProteomicsDB Tool - Mass Spectrometry-based Protein Expression Database

Provides access to ProteomicsDB (proteomicsdb.org), a comprehensive database
of mass spectrometry-based protein quantification across human tissues,
cell lines, and body fluids.

API: https://www.proteomicsdb.org/proteomicsdb/logic/
Authentication: None required (free public API).
"""

import requests
from typing import Dict, Any, Optional, List
from .base_tool import BaseTool
from .tool_registry import register_tool

BASE_URL = "https://www.proteomicsdb.org/proteomicsdb/logic"
API_V2_URL = "https://www.proteomicsdb.org/proteomicsdb/logic/api_v2/api.xsodata"


def _odata_request(url, timeout=30):
    """Execute an OData GET request and return parsed JSON."""
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code != 200:
            return {
                "ok": False,
                "error": "ProteomicsDB returned HTTP %d" % resp.status_code,
            }
        data = resp.json()
        return {"ok": True, "data": data}
    except requests.exceptions.Timeout:
        return {"ok": False, "error": "ProteomicsDB request timed out"}
    except requests.exceptions.ConnectionError:
        return {"ok": False, "error": "Failed to connect to ProteomicsDB"}
    except ValueError:
        return {"ok": False, "error": "Invalid JSON response from ProteomicsDB"}
    except Exception as e:
        return {"ok": False, "error": "Request failed: %s" % str(e)}


def _xsjs_request(endpoint, params=None, timeout=30):
    """Execute a request to a ProteomicsDB .xsjs endpoint."""
    url = "%s/%s" % (BASE_URL, endpoint)
    try:
        resp = requests.get(url, params=params, timeout=timeout)
        if resp.status_code != 200:
            return {
                "ok": False,
                "error": "ProteomicsDB returned HTTP %d" % resp.status_code,
            }
        data = resp.json()
        return {"ok": True, "data": data}
    except requests.exceptions.Timeout:
        return {"ok": False, "error": "ProteomicsDB request timed out"}
    except requests.exceptions.ConnectionError:
        return {"ok": False, "error": "Failed to connect to ProteomicsDB"}
    except ValueError:
        return {"ok": False, "error": "Invalid JSON response from ProteomicsDB"}
    except Exception as e:
        return {"ok": False, "error": "Request failed: %s" % str(e)}


def _resolve_protein_id(uniprot_id, taxcode=9606):
    """Resolve a UniProt accession to a ProteomicsDB internal PROTEIN_ID.

    Returns the first SwissProt (canonical) match if available, else the first match.
    """
    url = (
        "%s/Protein?$filter=UNIQUE_IDENTIFIER eq '%s' and TAXCODE eq %d"
        "&$format=json&$select=PROTEIN_ID,UNIQUE_IDENTIFIER,ENTRY_NAME,"
        "PROTEIN_NAME,GENE_NAME,TAXCODE,MASS"
    ) % (API_V2_URL, uniprot_id, taxcode)

    result = _odata_request(url)
    if not result["ok"]:
        return None, result["error"]

    results = result["data"].get("d", {}).get("results", [])
    if not results:
        return None, "Protein '%s' not found in ProteomicsDB" % uniprot_id

    # Prefer the canonical (non-isoform) SwissProt entry
    for entry in results:
        uid = entry.get("UNIQUE_IDENTIFIER", "")
        if uid == uniprot_id and "-" not in uid:
            return entry["PROTEIN_ID"], None

    # Fallback to first result
    return results[0]["PROTEIN_ID"], None


@register_tool("ProteomicsDBTool")
class ProteomicsDBTool(BaseTool):
    """
    Tool for querying ProteomicsDB, a mass spectrometry-based protein
    expression database covering human tissues, cell lines, and body fluids.

    Complements HPA (antibody-based) with MS-based quantitative proteomics
    from the Human Proteome Project. Provides iBAQ and TOP3 quantification
    across 340+ biological sources.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])

    def run(self, arguments):
        """Execute a ProteomicsDB query."""
        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        handlers = {
            "get_protein_expression": self._get_protein_expression,
            "search_proteins": self._search_proteins,
            "get_expression_summary": self._get_expression_summary,
            "list_tissues": self._list_tissues,
        }

        handler = handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": "Unknown operation: %s" % operation,
                "available_operations": list(handlers.keys()),
            }

        try:
            return handler(arguments)
        except Exception as e:
            return {"status": "error", "error": "Operation failed: %s" % str(e)}

    def _get_protein_expression(self, arguments):
        """Get protein expression across tissues/cell lines."""
        uniprot_id = arguments.get("uniprot_id")
        if not uniprot_id:
            return {"status": "error", "error": "uniprot_id parameter is required"}

        tissue_category = arguments.get("tissue_category", "tissue;fluid;cell line")
        calculation_method = arguments.get("calculation_method", "iBAQ")

        # Map user-friendly category to API format
        category_map = {
            "tissue": "tissue",
            "cell line": "cell line",
            "cell_line": "cell line",
            "fluid": "fluid",
            "all": "tissue;fluid;cell line",
        }
        if tissue_category in category_map:
            bio_source = category_map[tissue_category]
        else:
            bio_source = tissue_category

        # Map calculation method
        calc_map = {"iBAQ": "iBAQ", "ibaq": "iBAQ", "TOP3": "top3", "top3": "top3"}
        calc_unit = calc_map.get(calculation_method, "iBAQ")

        # Use the heatmap cluster endpoint (the primary expression data API)
        result = _xsjs_request(
            "getExpressionProfileHeatmapCluster.xsjs",
            params={
                "proteins": uniprot_id,
                "omics": "Proteomics",
                "biologicalSource": bio_source,
                "quantification": "MS1",
                "calculationMethod": calc_unit,
                "swissprotOnly": 1,
                "noIsoforms": 1,
                "source": "db",
                "datasetIds": "",
                "impute": 0,
                "taxcode": 9606,
            },
            timeout=60,
        )

        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        data = result["data"]
        mapdata = data.get("mapdata", [])
        tissuedata = data.get("tissuedata", [])
        proteindata = data.get("proteindata", [])

        if not mapdata:
            return {
                "status": "success",
                "data": {
                    "uniprot_id": uniprot_id,
                    "calculation_method": calc_unit,
                    "tissue_category": bio_source,
                    "num_tissues": 0,
                    "expression_records": [],
                },
            }

        # Build tissue lookup: tissue_id -> [name, sap_synonym, category]
        tissue_lookup = {}
        for t in tissuedata:
            # Format: [tissue_id, name, sap_synonym, category]
            if len(t) >= 4:
                tissue_lookup[t[0]] = {
                    "tissue_name": t[1] or "",
                    "tissue_group": t[2] or "",
                    "tissue_category": t[3] or "",
                }

        # Build expression records
        # mapdata format: [protein_id, tissue_id, val1, val2, val3, val4]
        # val1 appears to be the main normalized expression value (log10 iBAQ)
        records = []
        for row in mapdata:
            if len(row) < 3:
                continue
            tissue_id = row[1]
            tissue_info = tissue_lookup.get(tissue_id, {})
            rec = {
                "tissue_id": tissue_id,
                "tissue_name": tissue_info.get("tissue_name", ""),
                "tissue_group": tissue_info.get("tissue_group", ""),
                "tissue_category": tissue_info.get("tissue_category", ""),
                "expression_value": row[2] if len(row) > 2 else None,
            }
            # Add additional quantification values if present
            if len(row) > 3:
                rec["median_expression"] = row[3]
            if len(row) > 4:
                rec["min_expression"] = row[4]
            if len(row) > 5:
                rec["max_expression"] = row[5]
            records.append(rec)

        # Sort by expression value descending
        records.sort(key=lambda r: r.get("expression_value") or 0, reverse=True)

        # Get protein info
        protein_name = ""
        gene_name = ""
        if proteindata and len(proteindata[0]) >= 4:
            protein_name = proteindata[0][1]
            gene_name = proteindata[0][2]

        return {
            "status": "success",
            "data": {
                "uniprot_id": uniprot_id,
                "protein_name": protein_name,
                "gene_name": gene_name,
                "calculation_method": calc_unit,
                "tissue_category": bio_source,
                "num_tissues": len(records),
                "expression_records": records,
            },
        }

    def _search_proteins(self, arguments):
        """Search for proteins by gene name, UniProt ID, or protein name."""
        query = arguments.get("query")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        organism_id = arguments.get("organism_id", 9606)
        max_results = arguments.get("max_results", 20)

        # Try gene name first, then UniProt ID, then protein name
        # Use OData substringof for flexible matching
        url = (
            "%s/Protein?$filter=(substringof('%s',GENE_NAME) or "
            "substringof('%s',UNIQUE_IDENTIFIER) or "
            "substringof('%s',PROTEIN_NAME)) and TAXCODE eq %d"
            "&$format=json&$select=PROTEIN_ID,UNIQUE_IDENTIFIER,ENTRY_NAME,"
            "PROTEIN_NAME,GENE_NAME,TAXCODE,MASS"
            "&$top=%d"
        ) % (API_V2_URL, query, query, query, organism_id, max_results)

        result = _odata_request(url, timeout=30)
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        raw_results = result["data"].get("d", {}).get("results", [])

        # Deduplicate by UNIQUE_IDENTIFIER (same protein can appear with
        # different PROTEIN_IDs due to database versions)
        seen = set()
        proteins = []
        for r in raw_results:
            uid = r.get("UNIQUE_IDENTIFIER", "")
            if uid in seen:
                continue
            seen.add(uid)
            mass_val = r.get("MASS")
            if mass_val is not None:
                try:
                    mass_val = float(mass_val)
                except (ValueError, TypeError):
                    mass_val = None
            proteins.append(
                {
                    "protein_id": r.get("PROTEIN_ID"),
                    "uniprot_id": uid,
                    "entry_name": r.get("ENTRY_NAME", ""),
                    "protein_name": r.get("PROTEIN_NAME", ""),
                    "gene_name": r.get("GENE_NAME", ""),
                    "organism_id": r.get("TAXCODE"),
                    "mass_da": mass_val,
                }
            )

        return {
            "status": "success",
            "data": {
                "query": query,
                "organism_id": organism_id,
                "num_results": len(proteins),
                "proteins": proteins,
            },
        }

    def _get_expression_summary(self, arguments):
        """Get top tissues by expression level for a protein."""
        uniprot_id = arguments.get("uniprot_id")
        if not uniprot_id:
            return {"status": "error", "error": "uniprot_id parameter is required"}

        top_n = arguments.get("top_n", 10)

        # Get expression across all categories
        expr_result = self._get_protein_expression(
            {
                "uniprot_id": uniprot_id,
                "tissue_category": "all",
                "calculation_method": "iBAQ",
            }
        )

        if expr_result.get("status") != "success":
            return expr_result

        expr_data = expr_result["data"]
        records = expr_data.get("expression_records", [])

        # Already sorted by expression value descending
        top_records = records[:top_n]

        # Separate by category
        tissue_count = sum(1 for r in records if r.get("tissue_category") == "tissue")
        cell_line_count = sum(
            1 for r in records if r.get("tissue_category") == "cell line"
        )
        fluid_count = sum(1 for r in records if r.get("tissue_category") == "fluid")

        return {
            "status": "success",
            "data": {
                "uniprot_id": uniprot_id,
                "protein_name": expr_data.get("protein_name", ""),
                "gene_name": expr_data.get("gene_name", ""),
                "total_sources": len(records),
                "tissue_count": tissue_count,
                "cell_line_count": cell_line_count,
                "fluid_count": fluid_count,
                "top_n": top_n,
                "top_expression": top_records,
            },
        }

    def _list_tissues(self, arguments):
        """List all available tissues/cell lines in ProteomicsDB."""
        tissue_category = arguments.get("tissue_category")

        # Build OData filter
        filter_parts = []
        if tissue_category:
            cat_map = {
                "tissue": "tissue",
                "cell line": "cell line",
                "cell_line": "cell line",
                "fluid": "fluid",
            }
            cat_val = cat_map.get(tissue_category, tissue_category)
            filter_parts.append("CATEGORY eq '%s'" % cat_val)

        filter_str = ""
        if filter_parts:
            filter_str = "&$filter=" + " and ".join(filter_parts)

        url = (
            "%s/Tissue?$format=json&$select=TISSUE_ID,NAME,CATEGORY,SAP_SYNONYM"
            "&$top=5000%s"
        ) % (API_V2_URL, filter_str)

        result = _odata_request(url, timeout=30)
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        raw_results = result["data"].get("d", {}).get("results", [])

        tissues = []
        for r in raw_results:
            name = r.get("NAME", "")
            category = r.get("CATEGORY", "")
            # Skip entries with empty name or category
            if not name or not category:
                continue
            tissues.append(
                {
                    "tissue_id": r.get("TISSUE_ID", ""),
                    "name": name,
                    "category": category,
                    "group": r.get("SAP_SYNONYM", ""),
                }
            )

        # Sort by category then name
        tissues.sort(key=lambda t: (t["category"], t["name"]))

        # Count by category
        cat_counts = {}
        for t in tissues:
            cat = t["category"]
            cat_counts[cat] = cat_counts.get(cat, 0) + 1

        return {
            "status": "success",
            "data": {
                "filter_category": tissue_category,
                "total_sources": len(tissues),
                "category_counts": cat_counts,
                "tissues": tissues,
            },
        }
