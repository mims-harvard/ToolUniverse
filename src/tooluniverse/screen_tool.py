import requests
from typing import Any, Dict
from urllib.parse import quote
from .base_tool import BaseTool
from .http_utils import request_with_retry
from .screen_ccre_tool import ScreenCcreTool
from .tool_registry import register_tool


ENSEMBL_LOOKUP_URL = "https://rest.ensembl.org/lookup/symbol/homo_sapiens"
_ELEMENT_TYPE_MAP = {
    "enhancer": {"pELS", "dELS"},
    "promoter": {"PLS"},
    "insulator": {"CTCF-only"},
    "dnase-h3k4me3": {"DNase-H3K4me3"},
    "all": None,
    "pls": {"PLS"},
    "pels": {"pELS"},
    "dels": {"dELS"},
    "ctcf-only": {"CTCF-only"},
}


@register_tool("SCREENRESTTool")
class SCREENRESTTool(BaseTool):
    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self.timeout = 30
        self._gene_lookup_cache: Dict[str, tuple[Dict[str, Any], str]] = {}

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            arguments = dict(arguments or {})
            allowed = {
                "gene_name",
                "query",
                "element_type",
                "limit",
                "offset",
                "flank_bp",
                "assembly",
            }
            unknown = sorted(set(arguments) - allowed)
            if unknown:
                return {
                    "status": "error",
                    "error": f"Unknown parameter(s): {', '.join(unknown)}",
                }

            if "query" in arguments:
                if (
                    "gene_name" in arguments
                    and arguments["gene_name"] != arguments["query"]
                ):
                    return {
                        "status": "error",
                        "error": "Conflicting values for query and gene_name",
                    }
                arguments["gene_name"] = arguments.pop("query")

            gene_name = arguments.get("gene_name")
            if not isinstance(gene_name, str) or not gene_name.strip():
                return {
                    "status": "error",
                    "error": "gene_name (or query) must be a non-empty human gene symbol",
                }
            gene_name = gene_name.strip()

            assembly = arguments.get("assembly", "GRCh38")
            if assembly != "GRCh38":
                return {
                    "status": "error",
                    "error": "SCREEN_get_regulatory_elements currently supports assembly='GRCh38' only",
                }

            element_type = arguments.get("element_type", "enhancer")
            if not isinstance(element_type, str) or element_type.strip().lower() not in _ELEMENT_TYPE_MAP:
                return {
                    "status": "error",
                    "error": (
                        "element_type must be enhancer, promoter, insulator, all, "
                        "PLS, pELS, dELS, CTCF-only, or DNase-H3K4me3"
                    ),
                }
            element_type_key = element_type.strip().lower()
            allowed_classes = _ELEMENT_TYPE_MAP[element_type_key]

            limit = arguments.get("limit", 10)
            offset = arguments.get("offset", 0)
            flank_bp = arguments.get("flank_bp", 10000)
            if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 200:
                return {"status": "error", "error": "limit must be an integer from 1 to 200"}
            if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
                return {"status": "error", "error": "offset must be a non-negative integer"}
            if (
                isinstance(flank_bp, bool)
                or not isinstance(flank_bp, int)
                or not 0 <= flank_bp <= 1000000
            ):
                return {
                    "status": "error",
                    "error": "flank_bp must be an integer from 0 to 1000000",
                }

            lookup_url = f"{ENSEMBL_LOOKUP_URL}/{quote(gene_name, safe='')}"
            cache_key = gene_name.upper()
            cached_lookup = self._gene_lookup_cache.get(cache_key)
            if cached_lookup is None:
                lookup_response = request_with_retry(
                    self.session,
                    "GET",
                    f"{lookup_url}?content-type=application/json",
                    headers={"Accept": "application/json"},
                    timeout=self.timeout,
                    max_attempts=3,
                )
                if lookup_response.status_code == 404:
                    return {
                        "status": "error",
                        "error": f"Human gene not found in Ensembl: {gene_name}",
                    }
                lookup_response.raise_for_status()
                gene = lookup_response.json()
                resolved_lookup_url = lookup_response.url
            else:
                gene, resolved_lookup_url = cached_lookup
            required_gene_fields = {
                "id",
                "display_name",
                "assembly_name",
                "seq_region_name",
                "start",
                "end",
                "strand",
            }
            if not isinstance(gene, dict) or not required_gene_fields.issubset(gene):
                return {"status": "error", "error": "Ensembl returned malformed gene coordinates"}
            if gene["assembly_name"] != assembly:
                return {
                    "status": "error",
                    "error": "Ensembl gene assembly conflicts with the requested SCREEN assembly",
                }
            if str(gene["display_name"]).upper() != gene_name.upper():
                return {
                    "status": "error",
                    "error": "Ensembl resolved a different official gene symbol; use the returned official symbol explicitly",
                }
            if cached_lookup is None:
                self._gene_lookup_cache[cache_key] = (dict(gene), resolved_lookup_url)

            region_start = max(1, int(gene["start"]) - flank_bp)
            region_end = int(gene["end"]) + flank_bp
            screen = ScreenCcreTool({"fields": {"operation": "search_region"}})
            screen_result = screen.run(
                {
                    "chrom": str(gene["seq_region_name"]),
                    "start": region_start,
                    "end": region_end,
                    "assembly": assembly,
                }
            )
            if screen_result.get("status") != "success":
                return screen_result

            all_ccres = screen_result.get("data")
            if not isinstance(all_ccres, list):
                return {"status": "error", "error": "SCREEN returned malformed cCRE data"}
            filtered = (
                all_ccres
                if allowed_classes is None
                else [row for row in all_ccres if row.get("element_type") in allowed_classes]
            )
            total = len(filtered)
            page = filtered[offset : offset + limit]
            next_offset = offset + len(page)
            has_more = next_offset < total

            return {
                "status": "success",
                "data": {
                    "gene_name": gene["display_name"],
                    "requested_gene_name": gene_name,
                    "ensembl_gene_id": gene["id"],
                    "element_type": element_type,
                    "count": len(page),
                    "total_results": total,
                    "regulatory_elements": page,
                    "gene_coordinates": {
                        "assembly": gene["assembly_name"],
                        "chrom": f"chr{gene['seq_region_name']}",
                        "start": gene["start"],
                        "end": gene["end"],
                        "strand": gene["strand"],
                    },
                    "query_region": {
                        "assembly": assembly,
                        "chrom": f"chr{gene['seq_region_name']}",
                        "start": region_start,
                        "end": region_end,
                        "flank_bp": flank_bp,
                    },
                    "functional_association_claimed": False,
                },
                "metadata": {
                    "source": "ENCODE SCREEN Registry of cCREs",
                    "coordinate_source": "Ensembl REST lookup/symbol",
                    "gene_resolution_url": resolved_lookup_url,
                    "returned": len(page),
                    "total_results": total,
                    "total_results_is_exact": True,
                    "limit": limit,
                    "offset": offset,
                    "has_more": has_more,
                    "next_offset": next_offset if has_more else None,
                    "result_set_complete": offset == 0 and len(page) == total,
                    "screen_region_total_before_element_filter": len(all_ccres),
                    "element_classes_applied": (
                        sorted(allowed_classes) if allowed_classes is not None else None
                    ),
                    "note": (
                        "These cCREs overlap the Ensembl gene interval plus the requested "
                        "flank; overlap does not by itself prove functional regulation of the gene."
                    ),
                },
            }
        except requests.exceptions.HTTPError as e:
            return {"status": "error", "error": f"SCREEN/Ensembl API HTTP error: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"SCREEN/Ensembl API error: {str(e)}"}
