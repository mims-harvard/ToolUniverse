"""
Ensembl VEP variant pathogenicity predictor tool for ToolUniverse.

The public Ensembl VEP (Variant Effect Predictor) REST endpoint can return
per-transcript missense pathogenicity predictions in a single no-key call:

  - AlphaMissense (DeepMind, 2023): am_pathogenicity (0-1) + am_class
    (likely_benign / ambiguous / likely_pathogenic)
  - SIFT: prediction (tolerated / deleterious) + numeric score
  - PolyPhen-2: prediction (benign / possibly_damaging / probably_damaging)
    + numeric score
  - Most-severe consequence term for the variant

The existing ToolUniverse EnsemblVEP_* tools return only basic consequence
terms and do NOT surface these predictor scores. This tool fills that gap,
giving "one call -> many predictor scores" for variant interpretation,
similar in spirit to MyVariant.info but sourced live from Ensembl with the
AlphaMissense plugin pre-enabled.

Key facts about the public endpoint:
- No authentication / API key required.
- GRCh38 host: https://rest.ensembl.org
- GRCh37 host: https://grch37.rest.ensembl.org  (AlphaMissense also available)
- content-type MUST be passed as a query parameter (?content-type=...), not a
  header, for this endpoint family.
- AlphaMissense=1 is the plugin flag that is server-enabled on the public REST
  service. CADD / dbNSFP plugin flags are NOT server-enabled and will error,
  so they are intentionally not exposed here (use the dedicated CADD tool for
  CADD scores).
- Transient HTTP 500 / non-JSON HTML responses can occur; these are caught and
  reported as a clean error rather than raising.

API documentation: https://rest.ensembl.org/documentation/info/vep_id
AlphaMissense: Cheng et al., Science 2023.
"""

import time
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

REST_HOSTS = {
    "GRCh38": "https://rest.ensembl.org",
    "GRCh37": "https://grch37.rest.ensembl.org",
}


@register_tool("VEPPathogenicityTool")
class VEPPathogenicityTool(BaseTool):
    """
    Query Ensembl VEP for missense pathogenicity predictor scores.

    Operations (selected via the `operation` field in the tool config):
      - predict_by_rsid:   input a dbSNP rsID (e.g. rs699)
      - predict_by_hgvs:   input HGVS notation (e.g. ENST00000269305.9:c.524G>A)
      - predict_by_region: input chrom + pos + alt allele (e.g. 7, 140753336, T)

    Each returns a list of per-transcript predictions plus the variant's
    most-severe consequence.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        fields = tool_config.get("fields", {})
        self.operation = fields.get("operation", "")
        # Ensembl REST via python-requests is markedly slower than curl; keep a
        # generous but bounded timeout (must stay <= 30s tool budget).
        self.timeout = fields.get("timeout", 30)

    # ------------------------------------------------------------------ run
    def run(self, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        arguments = arguments or {}
        operation = self.operation or arguments.get("operation")
        if not operation:
            # Single collapsed tool: route by whichever input was supplied.
            if arguments.get("rsid"):
                operation = "predict_by_rsid"
            elif arguments.get("hgvs_notation"):
                operation = "predict_by_hgvs"
            elif (
                arguments.get("chrom")
                and arguments.get("pos") is not None
                and arguments.get("alt")
            ):
                operation = "predict_by_region"
            else:
                return {
                    "status": "error",
                    "error": "Provide one of: 'rsid', 'hgvs_notation', "
                    "or ('chrom' + 'pos' + 'alt').",
                }

        handlers = {
            "predict_by_rsid": self._predict_by_rsid,
            "predict_by_hgvs": self._predict_by_hgvs,
            "predict_by_region": self._predict_by_region,
        }
        handler = handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}. "
                f"Valid operations: {sorted(handlers)}",
            }

        try:
            return handler(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": "Ensembl VEP request timed out (server slow or "
                "overloaded); please retry.",
            }
        except requests.exceptions.RequestException as exc:
            return {"status": "error", "error": f"Ensembl VEP request failed: {exc}"}
        except Exception as exc:  # pragma: no cover - defensive catch-all
            return {"status": "error", "error": f"Unexpected error: {exc}"}

    # ----------------------------------------------------------- assemblies
    @staticmethod
    def _resolve_host(arguments: Dict[str, Any]) -> Optional[str]:
        build = str(arguments.get("genome_build", "GRCh38")).strip()
        # Accept common aliases.
        aliases = {
            "hg38": "GRCh38",
            "grch38": "GRCh38",
            "hg19": "GRCh37",
            "grch37": "GRCh37",
        }
        build = aliases.get(build.lower(), build)
        return REST_HOSTS.get(build)

    # ----------------------------------------------------------- http call
    def _fetch_vep(self, host: str, path: str) -> Dict[str, Any]:
        """
        Call a VEP endpoint and return either {"records": [...]} on success or
        {"error": "..."} on failure. Path already includes the leading slash.
        """
        url = f"{host}{path}"
        sep = "&" if "?" in path else "?"
        url = f"{url}{sep}content-type=application/json&AlphaMissense=1"

        # The public Ensembl REST service intermittently returns HTTP 5xx under
        # load. Retry transient server errors a couple of times with a short
        # backoff before giving up. 4xx responses (bad rsID/HGVS) are NOT
        # retried since they are deterministic client errors.
        # Heavy variants (many overlapping transcripts) take ~7-12s via
        # python-requests against the public Ensembl REST service. Allow a
        # generous per-attempt timeout but keep at most 2 attempts plus a short
        # backoff so the worst case (2 x 14s + 1s) stays within the 30s budget.
        per_attempt = min(self.timeout, 14)
        max_attempts = 2
        resp = None
        for attempt in range(max_attempts):
            resp = requests.get(url, timeout=per_attempt)
            if resp.status_code < 500:
                break
            if attempt < max_attempts - 1:
                time.sleep(1.0)

        if resp.status_code >= 400:
            # Ensembl returns JSON errors for parse problems, HTML for 5xx.
            detail = resp.text[:200].replace("\n", " ")
            return {"error": f"Ensembl VEP HTTP {resp.status_code}: {detail}"}

        try:
            data = resp.json()
        except ValueError:
            return {"error": "Ensembl VEP returned a non-JSON response"}

        if not isinstance(data, list):
            return {"error": "Unexpected Ensembl VEP response (expected a list)"}
        return {"records": data}

    # ----------------------------------------------------------- parsing
    @staticmethod
    def _parse_consequences(tc_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        predictions: List[Dict[str, Any]] = []
        for tc in tc_list:
            am = tc.get("alphamissense") or {}
            predictions.append(
                {
                    "transcript_id": tc.get("transcript_id"),
                    "gene_symbol": tc.get("gene_symbol"),
                    "gene_id": tc.get("gene_id"),
                    "biotype": tc.get("biotype"),
                    "consequence_terms": tc.get("consequence_terms"),
                    "amino_acids": tc.get("amino_acids"),
                    "codons": tc.get("codons"),
                    "impact": tc.get("impact"),
                    "sift_prediction": tc.get("sift_prediction"),
                    "sift_score": tc.get("sift_score"),
                    "polyphen_prediction": tc.get("polyphen_prediction"),
                    "polyphen_score": tc.get("polyphen_score"),
                    "alphamissense_class": am.get("am_class"),
                    "alphamissense_pathogenicity": am.get("am_pathogenicity"),
                }
            )
        return predictions

    def _build_result(
        self, fetched: Dict[str, Any], query: str, host: str
    ) -> Dict[str, Any]:
        if "error" in fetched:
            return {"status": "error", "error": fetched["error"]}

        records = fetched["records"]
        if not records:
            return {
                "status": "success",
                "data": [],
                "metadata": {
                    "query": query,
                    "source": "Ensembl VEP",
                    "count": 0,
                    "note": "No VEP annotation returned for this input.",
                },
            }

        out: List[Dict[str, Any]] = []
        for rec in records:
            tc_list = rec.get("transcript_consequences", []) or []
            predictions = self._parse_consequences(tc_list)
            # Whether any AlphaMissense score is present for this variant.
            has_am = any(
                p.get("alphamissense_pathogenicity") is not None for p in predictions
            )
            out.append(
                {
                    "input": rec.get("input"),
                    "variant_id": rec.get("id"),
                    "assembly_name": rec.get("assembly_name"),
                    "seq_region_name": rec.get("seq_region_name"),
                    "start": rec.get("start"),
                    "end": rec.get("end"),
                    "allele_string": rec.get("allele_string"),
                    "most_severe_consequence": rec.get("most_severe_consequence"),
                    "has_alphamissense": has_am,
                    "predictions": predictions,
                }
            )

        return {
            "status": "success",
            "data": out,
            "metadata": {
                "query": query,
                "source": "Ensembl VEP",
                "host": host,
                "count": len(out),
                "predictors": ["AlphaMissense", "SIFT", "PolyPhen-2"],
            },
        }

    # ----------------------------------------------------------- operations
    def _predict_by_rsid(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        rsid = arguments.get("rsid") or arguments.get("variant_id")
        if not rsid:
            return {"status": "error", "error": "Missing required parameter: rsid"}
        host = self._resolve_host(arguments)
        if not host:
            return self._bad_build(arguments)
        rsid = str(rsid).strip()
        path = f"/vep/human/id/{quote(rsid, safe='')}"
        fetched = self._fetch_vep(host, path)
        return self._build_result(fetched, rsid, host)

    def _predict_by_hgvs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        hgvs = arguments.get("hgvs_notation") or arguments.get("hgvs")
        if not hgvs:
            return {
                "status": "error",
                "error": "Missing required parameter: hgvs_notation",
            }
        host = self._resolve_host(arguments)
        if not host:
            return self._bad_build(arguments)
        hgvs = str(hgvs).strip()
        path = f"/vep/human/hgvs/{quote(hgvs, safe='')}"
        fetched = self._fetch_vep(host, path)
        return self._build_result(fetched, hgvs, host)

    def _predict_by_region(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        chrom = arguments.get("chrom")
        pos = arguments.get("pos")
        alt = arguments.get("alt")
        if chrom is None or pos is None or not alt:
            return {
                "status": "error",
                "error": "Missing required parameters: chrom, pos, alt",
            }
        try:
            pos_int = int(pos)
        except (TypeError, ValueError):
            return {"status": "error", "error": f"pos must be an integer, got: {pos}"}

        host = self._resolve_host(arguments)
        if not host:
            return self._bad_build(arguments)

        chrom_norm = str(chrom).strip()
        if chrom_norm.lower().startswith("chr"):
            chrom_norm = chrom_norm[3:]
        alt = str(alt).strip().upper()

        # Ensembl region+allele VEP format: region/{chr}:{start}-{end}/{alt}
        region = f"{chrom_norm}:{pos_int}-{pos_int}"
        path = f"/vep/human/region/{quote(region, safe=':-')}/{quote(alt, safe='')}"
        fetched = self._fetch_vep(host, path)
        query = f"{chrom_norm}:{pos_int} {alt} ({host.split('//')[-1]})"
        return self._build_result(fetched, query, host)

    # ----------------------------------------------------------- helpers
    @staticmethod
    def _bad_build(arguments: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": "error",
            "error": f"Unsupported genome_build '{arguments.get('genome_build')}'. "
            f"Valid builds: {sorted(REST_HOSTS)}",
        }
