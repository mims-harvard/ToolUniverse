"""
ENCODE SCREEN cCRE Tool - Registry of candidate cis-Regulatory Elements

Queries the ENCODE SCREEN (Search Candidate cis-Regulatory Elements by ENCODE)
registry, which annotates the human/mouse genome with candidate regulatory
elements (cCREs) and their epigenomic signal strengths. Each cCRE carries
DNase, H3K4me3 (promoter), H3K27ac (enhancer), and CTCF z-scores plus an
element classification (PLS = promoter-like, pELS/dELS = proximal/distal
enhancer-like, CTCF-only, DNase-H3K4me3).

This is a regulatory-genomics annotation service: given a genomic region you
get the regulatory elements overlapping it, and given a cCRE accession you get
its classification and coordinates. It is the curated, experimentally grounded
counterpart to sequence-to-track deep-learning predictors (Enformer/Borzoi),
which are not available as public REST endpoints.

API base: https://ga.staging.wenglab.org/graphql (GraphQL, no authentication)
Reference: ENCODE Project Consortium / Weng Lab, SCREEN. Moore et al.,
Nature 2020 (the ENCODE3 Registry of cCREs). https://screen.encodeproject.org
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool


SCREEN_GRAPHQL = "https://ga.staging.wenglab.org/graphql"

# SCREEN passes a z-score rank window for each assay; -10..10 spans the full
# range so that no element is filtered out by signal strength unless the caller
# narrows it via the *_min arguments below.
_RANK_FLOOR = -10
_RANK_CEIL = 10


@register_tool("ScreenCcreTool")
class ScreenCcreTool(BaseTool):
    """
    Tool for querying the ENCODE SCREEN registry of candidate cis-regulatory
    elements (cCREs).

    Supported operations (set via fields.operation):
    - search_region: list cCREs overlapping a genomic region
    - get_ccre: look up one or more cCREs by SCREEN accession
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = 30
        self.operation = tool_config.get("fields", {}).get("operation", "search_region")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        arguments = arguments or {}
        try:
            if self.operation == "search_region":
                return self._search_region(arguments)
            if self.operation == "get_ccre":
                return self._get_ccre(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": "ENCODE SCREEN API request timed out",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to ENCODE SCREEN API",
            }
        except Exception as e:  # never raise out of run()
            return {"status": "error", "error": f"ENCODE SCREEN API error: {e}"}

    # ---------------------------------------------------------------- helpers
    def _post(self, query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        resp = requests.post(
            SCREEN_GRAPHQL,
            json={"query": query, "variables": variables},
            timeout=self.timeout,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _norm_chrom(chrom: str) -> str:
        chrom = str(chrom).strip()
        return chrom if chrom.startswith("chr") else f"chr{chrom}"

    @staticmethod
    def _graphql_error(payload: Dict[str, Any]) -> str:
        """Join GraphQL error messages into one string for the error envelope."""
        return "SCREEN query error: " + "; ".join(
            err.get("message", "") for err in payload["errors"]
        )

    # ------------------------------------------------------------- operations
    def _search_region(self, args: Dict[str, Any]) -> Dict[str, Any]:
        chrom = args.get("chrom")
        start = args.get("start")
        end = args.get("end")
        if chrom is None or start is None or end is None:
            return {
                "status": "error",
                "error": "Missing required parameters: chrom, start, end",
            }
        try:
            start = int(start)
            end = int(end)
        except (TypeError, ValueError):
            return {
                "status": "error",
                "error": "start and end must be integers (1-based genomic coordinates)",
            }
        if end <= start:
            return {"status": "error", "error": "end must be greater than start"}

        assembly = args.get("assembly", "GRCh38")
        element_type = args.get("element_type")  # optional hint filter

        query = """
        query R($a:String!,$c:String!,$s:Int!,$e:Int!,$rf:Int!,$rc:Int!,$et:String){
          cCRESCREENSearch(
            assembly:$a, coord_chrom:$c, coord_start:$s, coord_end:$e,
            element_type:$et,
            rank_ctcf_start:$rf, rank_ctcf_end:$rc,
            rank_dnase_start:$rf, rank_dnase_end:$rc,
            rank_enhancer_start:$rf, rank_enhancer_end:$rc,
            rank_promoter_start:$rf, rank_promoter_end:$rc
          ){
            chrom start len pct
            ctcf_zscore dnase_zscore enhancer_zscore promoter_zscore maxz
            info{ accession isproximal ctcfmax k4me3max k27acmax }
          }
        }
        """
        variables = {
            "a": assembly,
            "c": self._norm_chrom(chrom),
            "s": start,
            "e": end,
            "rf": _RANK_FLOOR,
            "rc": _RANK_CEIL,
            "et": element_type,
        }
        payload = self._post(query, variables)
        if payload.get("errors"):
            return {"status": "error", "error": self._graphql_error(payload)}

        rows = (payload.get("data") or {}).get("cCRESCREENSearch") or []
        results = []
        for r in rows:
            info = r.get("info") or {}
            start_pos = r.get("start")
            length = r.get("len")
            results.append(
                {
                    "accession": info.get("accession"),
                    "chrom": r.get("chrom"),
                    "start": start_pos,
                    "end": (start_pos + length)
                    if (start_pos is not None and length is not None)
                    else None,
                    "element_type": r.get("pct"),
                    "is_proximal": info.get("isproximal"),
                    "dnase_zscore": r.get("dnase_zscore"),
                    "promoter_zscore": r.get("promoter_zscore"),
                    "enhancer_zscore": r.get("enhancer_zscore"),
                    "ctcf_zscore": r.get("ctcf_zscore"),
                    "k4me3_max": info.get("k4me3max"),
                    "k27ac_max": info.get("k27acmax"),
                    "ctcf_max": info.get("ctcfmax"),
                }
            )
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "assembly": assembly,
                "region": f"{self._norm_chrom(chrom)}:{start}-{end}",
                "count": len(results),
                "element_type_filter": element_type,
                "source": "ENCODE SCREEN Registry of cCREs",
            },
        }

    def _get_ccre(self, args: Dict[str, Any]) -> Dict[str, Any]:
        accession = args.get("accession")
        if not accession:
            return {
                "status": "error",
                "error": "Missing required parameter: accession (e.g. 'EH38E2666166')",
            }
        accessions = accession if isinstance(accession, list) else [str(accession)]
        assembly = args.get("assembly", "GRCh38")

        query = """
        query A($a:String!,$acc:[String!]){
          cCREQuery(assembly:$a, accession:$acc){
            accession group rDHS ctcf_bound
            coordinates{ chromosome start end }
          }
        }
        """
        payload = self._post(query, {"a": assembly, "acc": accessions})
        if payload.get("errors"):
            return {"status": "error", "error": self._graphql_error(payload)}

        rows = (payload.get("data") or {}).get("cCREQuery") or []
        results = []
        for r in rows:
            coords = r.get("coordinates") or {}
            results.append(
                {
                    "accession": r.get("accession"),
                    "element_type": r.get("group"),
                    "rdhs": r.get("rDHS"),
                    "ctcf_bound": r.get("ctcf_bound"),
                    "chrom": coords.get("chromosome"),
                    "start": coords.get("start"),
                    "end": coords.get("end"),
                }
            )
        if not results:
            return {
                "status": "error",
                "error": f"No cCRE found for accession(s) {accessions} in assembly {assembly}",
            }
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "assembly": assembly,
                "requested": accessions,
                "count": len(results),
                "source": "ENCODE SCREEN Registry of cCREs",
            },
        }
