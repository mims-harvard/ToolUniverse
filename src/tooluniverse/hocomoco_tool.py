"""
HOCOMOCO v14 Tool - Transcription Factor Binding Motifs

Provides access to the HOCOMOCO (HOmo sapiens COmprehensive MOdel COllection)
database for transcription factor binding motif data. HOCOMOCO contains
high-quality TF binding models derived from ChIP-Seq data for human and mouse.

API base: https://hocomoco14.autosome.org
No authentication required.

Reference: Kulakovskiy et al., Nucl. Acids Res. 2018
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool


HOCOMOCO_BASE = "https://hocomoco14.autosome.org"


@register_tool("HocomocoTool")
class HocomocoTool(BaseTool):
    """
    Tool for querying HOCOMOCO v14 transcription factor binding motif database.

    Supported operations:
    - search_motifs: Search for TF motifs by gene/protein name
    - get_motif: Get detailed motif information including PWM and quality
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = 30
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "search_motifs"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the HOCOMOCO API call."""
        try:
            if self.endpoint_type == "search_motifs":
                return self._search_motifs(arguments)
            elif self.endpoint_type == "get_motif":
                return self._get_motif(arguments)
            else:
                return {
                    "status": "error",
                    "error": f"Unknown endpoint type: {self.endpoint_type}",
                }
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "HOCOMOCO API request timed out"}
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to HOCOMOCO API",
            }
        except Exception as e:
            return {"status": "error", "error": f"HOCOMOCO API error: {str(e)}"}

    def _search_motifs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for TF motifs by gene/protein name."""
        query = arguments.get("query") or arguments.get("gene_name", "")
        if not query:
            return {"status": "error", "error": "Missing required parameter: query"}

        try:
            offset = max(0, int(arguments.get("offset", 0)))
            limit = min(max(1, int(arguments.get("limit", 10))), 25)
        except (TypeError, ValueError):
            return {
                "status": "error",
                "error": "offset and limit must be integers",
            }

        url = f"{HOCOMOCO_BASE}/search.json"
        resp = requests.get(url, params={"query": query}, timeout=self.timeout)
        resp.raise_for_status()

        motif_ids = resp.json()
        if not motif_ids:
            return {
                "status": "success",
                "data": [],
                "metadata": {
                    "query": query,
                    "total": 0,
                    "returned": 0,
                    "offset": offset,
                    "limit": limit,
                    "has_more": False,
                    "next_offset": None,
                    "failed_motif_ids": [],
                },
            }

        # The search endpoint returns every matching motif ID in one response.
        # Page that list before making the per-motif detail requests so every
        # hit is reachable without silently limiting all callers to the first
        # ten IDs.
        motif_page = motif_ids[offset : offset + limit]
        results = []
        failed_motif_ids = []
        for motif_id in motif_page:
            detail = self._fetch_motif_summary(motif_id)
            if detail:
                results.append(detail)
            else:
                failed_motif_ids.append(motif_id)

        consumed_through = offset + len(motif_page)
        has_more = consumed_through < len(motif_ids)

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "query": query,
                "total": len(motif_ids),
                "returned": len(results),
                "offset": offset,
                "limit": limit,
                "has_more": has_more,
                "next_offset": consumed_through if has_more else None,
                "failed_motif_ids": failed_motif_ids,
            },
        }

    def _fetch_motif_summary(self, motif_id: str) -> Dict[str, Any] | None:
        """Fetch summary info for a single motif."""
        try:
            url = f"{HOCOMOCO_BASE}/motif/{motif_id}.json"
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code != 200:
                return None
            data = resp.json()
            return {
                "motif_id": data.get("full_name"),
                "gene_name_human": data.get("gene_name_human"),
                "gene_name_mouse": data.get("gene_name_mouse"),
                "quality": data.get("quality"),
                "consensus": data.get("consensus"),
                "model_length": data.get("model_length"),
                "uniprot_ac_human": data.get("uniprot_ac_human"),
                "uniprot_ac_mouse": data.get("uniprot_ac_mouse"),
                "tfclass": data.get("tfclass"),
            }
        except Exception:
            return None

    def _get_motif(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed motif information including PWM."""
        motif_id = arguments.get("motif_id", "")
        if not isinstance(motif_id, str) or not motif_id.strip():
            return {"status": "error", "error": "Missing required parameter: motif_id"}
        motif_id = motif_id.strip()
        include_pwm = arguments.get("include_pwm", False)
        if not isinstance(include_pwm, bool):
            return {
                "status": "error",
                "error": "include_pwm must be a boolean",
                "parameter": "include_pwm",
            }

        # Fetch motif detail
        url = f"{HOCOMOCO_BASE}/motif/{motif_id}.json"
        resp = requests.get(url, timeout=self.timeout)
        if resp.status_code == 404:
            return {"status": "error", "error": f"Motif not found: {motif_id}"}
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict) or not data.get("full_name"):
            return {
                "status": "error",
                "error": "HOCOMOCO returned malformed motif metadata",
            }
        if data["full_name"] != motif_id:
            return {
                "status": "error",
                "error": (
                    "HOCOMOCO motif identity mismatch: requested "
                    f"{motif_id}, received {data['full_name']}"
                ),
            }

        pwm = None
        if include_pwm:
            pwm_url = f"{HOCOMOCO_BASE}/motif/{motif_id}/pwm.json"
            pwm_resp = requests.get(pwm_url, timeout=self.timeout)
            if pwm_resp.status_code != 200:
                return {
                    "status": "error",
                    "error": (
                        f"PWM was requested for {motif_id}, but HOCOMOCO returned "
                        f"HTTP {pwm_resp.status_code}; motif metadata without the requested "
                        "matrix was not returned"
                    ),
                    "pwm_requested": True,
                    "pwm_retrieved": False,
                    "url": pwm_url,
                }
            try:
                pwm = pwm_resp.json()
            except ValueError as exc:
                return {
                    "status": "error",
                    "error": f"PWM was requested for {motif_id}, but the response was not JSON: {exc}",
                    "pwm_requested": True,
                    "pwm_retrieved": False,
                    "url": pwm_url,
                }
            model_length = data.get("model_length")
            valid_rows = isinstance(pwm, list) and all(
                isinstance(row, list)
                and len(row) == 4
                and all(
                    isinstance(value, (int, float)) and not isinstance(value, bool)
                    for value in row
                )
                for row in pwm
            )
            if not valid_rows or (
                isinstance(model_length, int) and len(pwm) != model_length
            ):
                return {
                    "status": "error",
                    "error": (
                        f"HOCOMOCO returned a malformed PWM for {motif_id}; expected "
                        f"{model_length} rows of four numeric values"
                    ),
                    "pwm_requested": True,
                    "pwm_retrieved": False,
                    "url": pwm_url,
                }

        result = {
            "motif_id": data.get("full_name"),
            "gene_name_human": data.get("gene_name_human"),
            "gene_name_mouse": data.get("gene_name_mouse"),
            "gene_synonyms_human": data.get("gene_synonyms_human"),
            "gene_synonyms_mouse": data.get("gene_synonyms_mouse"),
            "quality": data.get("quality"),
            "consensus": data.get("consensus"),
            "model_length": data.get("model_length"),
            "data_sources": data.get("data_sources"),
            "motif_subtype": data.get("motif_subtype"),
            "uniprot_id_human": data.get("uniprot_id_human"),
            "uniprot_id_mouse": data.get("uniprot_id_mouse"),
            "uniprot_ac_human": data.get("uniprot_ac_human"),
            "uniprot_ac_mouse": data.get("uniprot_ac_mouse"),
            "hgnc_ids": data.get("hgnc_ids"),
            "entrezgene_ids_human": data.get("entrezgene_ids_human"),
            "entrezgene_ids_mouse": data.get("entrezgene_ids_mouse"),
            "tfclass": data.get("tfclass"),
            "motif_cluster": data.get("motif_cluster"),
            "quality_metrics": data.get("quality_metrics"),
            "previous_names": data.get("previous_names"),
            "retracted": data.get("retracted"),
            "pwm_requested": include_pwm,
            "pwm_status": "available" if include_pwm else "not_requested",
        }
        if pwm is not None:
            result["pwm"] = pwm

        return {"status": "success", "data": result}
