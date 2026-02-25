"""
TIMER (Tumor Immune Estimation Resource) — cBioPortal Backend

TIMER2.0/3.0 (timer.cistrome.org) no longer provides a public REST API;
the server redirects to a Shiny web application (compbio.cn/timer3/).

This tool replicates TIMER functionality using the cBioPortal public REST API
(www.cbioportal.org/api) to query TCGA gene expression and survival data.

Operations:
  - immune_estimation : Proxy immune-cell infiltration from marker gene expression
  - gene_correlation   : Spearman correlation between two genes across TCGA samples
  - survival_association: Overall-survival log-rank test for high/low gene expression
"""

import time
import requests
from typing import Dict, Any, List, Optional, Tuple
from .base_tool import BaseTool
from .tool_registry import register_tool

CBIOPORTAL_BASE = "https://www.cbioportal.org/api"

# Map TCGA abbreviations → cBioPortal study IDs (Firehose Legacy datasets)
CANCER_STUDY_MAP: Dict[str, str] = {
    "BRCA": "brca_tcga",
    "LUAD": "luad_tcga",
    "LUSC": "lusc_tcga",
    "COAD": "coadread_tcga",
    "READ": "coadread_tcga",
    "SKCM": "skcm_tcga",
    "GBM": "gbm_tcga",
    "UCEC": "ucec_tcga",
    "KIRC": "kirc_tcga",
    "PRAD": "prad_tcga",
    "HNSC": "hnsc_tcga",
    "STAD": "stad_tcga",
    "BLCA": "blca_tcga",
    "THCA": "thca_tcga",
    "LIHC": "lihc_tcga",
    "CESC": "cesc_tcga",
    "OV": "ov_tcga",
    "PCPG": "pcpg_tcga",
    "SARC": "sarc_tcga",
    "ACC": "acc_tcga",
    "MESO": "meso_tcga",
    "UVM": "uvm_tcga",
    "TGCT": "tgct_tcga",
    "KICH": "kich_tcga",
    "KIRP": "kirp_tcga",
    "DLBC": "dlbc_tcga",
    "LAML": "laml_tcga",
    "LGG": "lgg_tcga",
}

# Canonical immune cell marker genes from the TIMER paper
IMMUNE_MARKERS: Dict[str, str] = {
    "B_cell": "CD19",
    "CD4_T_cell": "CD4",
    "CD8_T_cell": "CD8A",
    "Neutrophil": "FCGR3B",
    "Macrophage": "CD68",
    "Dendritic_cell": "ITGAX",
}


@register_tool("TIMERTool")
class TIMERTool(BaseTool):
    """
    Replicates TIMER2.0 tumor immune estimation using cBioPortal TCGA data.

    Since TIMER3.0 no longer has a public REST API, this tool queries
    cBioPortal (www.cbioportal.org) for TCGA expression and survival data
    and computes equivalent statistics locally.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        operation_handlers = {
            "immune_estimation": self._immune_estimation,
            "gene_correlation": self._gene_correlation,
            "survival_association": self._survival_association,
        }

        handler = operation_handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}",
                "available_operations": list(operation_handlers.keys()),
            }

        try:
            return handler(arguments)
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "cBioPortal API request timed out"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to cBioPortal API"}
        except Exception as e:
            return {"status": "error", "error": f"Operation failed: {str(e)}"}

    # ── helpers ──────────────────────────────────────────────────────────────

    def _resolve_study(self, cancer: str) -> Tuple[Optional[str], Optional[str]]:
        study_id = CANCER_STUDY_MAP.get(cancer.upper())
        if not study_id:
            # Try lower-case fallback: e.g., "BRCA" → "brca_tcga"
            study_id = f"{cancer.lower()}_tcga"
        return study_id, None

    def _get_mrna_profile(self, study_id: str) -> Optional[str]:
        for attempt in range(3):
            try:
                r = requests.get(
                    f"{CBIOPORTAL_BASE}/studies/{study_id}/molecular-profiles",
                    params={"projection": "SUMMARY"},
                    timeout=20,
                )
                if r.status_code == 200:
                    break
            except requests.exceptions.RequestException:
                pass
            if attempt < 2:
                time.sleep(2**attempt)
        else:
            return None
        if r.status_code != 200:
            return None
        preferred_suffixes = [
            "_rna_seq_v2_mrna",
            "_rna_seq_mrna",
            "_mrna",
        ]
        profiles = r.json()
        for suffix in preferred_suffixes:
            for p in profiles:
                pid = p.get("molecularProfileId", "")
                if (
                    p.get("molecularAlterationType") == "MRNA_EXPRESSION"
                    and pid.endswith(suffix)
                    and not pid.endswith("_Zscores")
                ):
                    return pid
        return None

    def _get_samples(self, study_id: str, n: int = 200) -> List[str]:
        for attempt in range(3):
            try:
                r = requests.get(
                    f"{CBIOPORTAL_BASE}/studies/{study_id}/samples",
                    params={"projection": "ID", "pageSize": n},
                    timeout=20,
                )
                if r.status_code == 200:
                    return [s["sampleId"] for s in r.json()]
            except requests.exceptions.RequestException:
                pass
            if attempt < 2:
                time.sleep(2**attempt)
        return []

    def _get_gene_id(self, symbol: str) -> Optional[int]:
        r = requests.get(
            f"{CBIOPORTAL_BASE}/genes/{symbol.upper()}",
            params={"projection": "SUMMARY"},
            timeout=10,
        )
        if r.status_code == 200:
            return r.json().get("entrezGeneId")
        return None

    def _get_expression(
        self,
        profile_id: str,
        entrez_ids: List[int],
        sample_ids: List[str],
    ) -> List[Dict]:
        r = requests.post(
            f"{CBIOPORTAL_BASE}/molecular-data/fetch",
            params={"projection": "SUMMARY"},
            json={
                "entrezGeneIds": entrez_ids,
                "sampleMolecularIdentifiers": [
                    {"molecularProfileId": profile_id, "sampleId": sid}
                    for sid in sample_ids
                ],
            },
            timeout=60,
        )
        return r.json() if r.status_code == 200 else []

    def _get_os_data(self, study_id: str) -> Tuple[Dict[str, float], Dict[str, str]]:
        r = requests.get(
            f"{CBIOPORTAL_BASE}/studies/{study_id}/clinical-data",
            params={
                "clinicalDataType": "PATIENT",
                "projection": "SUMMARY",
                "pageSize": 100000,
            },
            timeout=60,
        )
        if r.status_code != 200:
            return {}, {}
        records = r.json()
        os_months: Dict[str, float] = {}
        os_status: Dict[str, str] = {}
        for rec in records:
            attr = rec.get("clinicalAttributeId")
            pid = rec.get("patientId", "")
            val = rec.get("value", "")
            if attr == "OS_MONTHS":
                try:
                    os_months[pid] = float(val)
                except ValueError:
                    pass
            elif attr == "OS_STATUS":
                os_status[pid] = val
        return os_months, os_status

    # ── operations ───────────────────────────────────────────────────────────

    def _immune_estimation(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        cancer = arguments.get("cancer")
        correlate_gene = arguments.get("gene")

        if not cancer:
            return {
                "status": "error",
                "error": "cancer is required (e.g., 'BRCA', 'LUAD')",
            }

        study_id, err = self._resolve_study(cancer)
        if err:
            return {"status": "error", "error": err}

        profile_id = self._get_mrna_profile(study_id)
        if not profile_id:
            return {
                "status": "error",
                "error": f"No mRNA expression profile found for {cancer} ({study_id})",
            }

        # Collect genes: immune markers + optional correlate gene
        marker_symbols = list(IMMUNE_MARKERS.values())
        all_symbols = marker_symbols + ([correlate_gene] if correlate_gene else [])

        # Resolve Entrez IDs
        entrez_ids = []
        symbol_to_entrez: Dict[str, int] = {}
        for sym in all_symbols:
            eid = self._get_gene_id(sym)
            if eid:
                entrez_ids.append(eid)
                symbol_to_entrez[sym] = eid

        sample_ids = self._get_samples(study_id, n=100)
        if not sample_ids:
            return {"status": "error", "error": f"No samples found for {cancer}"}

        records = self._get_expression(profile_id, entrez_ids, sample_ids)
        if not records:
            return {"status": "error", "error": "Expression data not available"}

        # Group by gene
        expr_by_entrez: Dict[int, List[float]] = {}
        for rec in records:
            eid = rec.get("entrezGeneId")
            val = rec.get("value")
            if eid and val is not None:
                expr_by_entrez.setdefault(eid, []).append(float(val))

        # Build immune infiltration summary
        immune_scores: Dict[str, Dict] = {}
        for cell_type, sym in IMMUNE_MARKERS.items():
            eid = symbol_to_entrez.get(sym)
            vals = expr_by_entrez.get(eid, []) if eid else []
            if vals:
                mean_val = sum(vals) / len(vals)
                sorted_vals = sorted(vals)
                n = len(sorted_vals)
                median_val = (
                    sorted_vals[n // 2]
                    if n % 2
                    else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
                )
                immune_scores[cell_type] = {
                    "marker_gene": sym,
                    "mean_expression": round(mean_val, 4),
                    "median_expression": round(median_val, 4),
                    "n_samples": n,
                }

        if correlate_gene:
            eid = symbol_to_entrez.get(correlate_gene)
            target_vals = expr_by_entrez.get(eid, []) if eid else []
            if target_vals:
                for cell_type, sym in IMMUNE_MARKERS.items():
                    m_eid = symbol_to_entrez.get(sym)
                    marker_vals = expr_by_entrez.get(m_eid, []) if m_eid else []
                    if marker_vals and target_vals:
                        n = min(len(marker_vals), len(target_vals))
                        try:
                            from scipy.stats import spearmanr

                            corr, pval = spearmanr(marker_vals[:n], target_vals[:n])
                            immune_scores[cell_type]["correlation_with_gene"] = {
                                "gene": correlate_gene,
                                "spearman_r": round(float(corr), 4),
                                "p_value": round(float(pval), 6),
                            }
                        except ImportError:
                            pass

        return {
            "status": "success",
            "data": {
                "cancer": cancer.upper(),
                "study_id": study_id,
                "profile_id": profile_id,
                "n_samples": len(sample_ids),
                "immune_infiltration": immune_scores,
                "method": "Marker gene expression (CD19, CD4, CD8A, FCGR3B, CD68, ITGAX) via cBioPortal TCGA data",
                "note": "TIMER2.0/3.0 API is unavailable; using cBioPortal TCGA expression as proxy",
            },
        }

    def _gene_correlation(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        cancer = arguments.get("cancer")
        gene1 = arguments.get("gene1")
        gene2 = arguments.get("gene2")

        if not cancer:
            return {"status": "error", "error": "cancer is required (e.g., 'BRCA')"}
        if not gene1 or not gene2:
            return {"status": "error", "error": "Both gene1 and gene2 are required"}

        study_id, err = self._resolve_study(cancer)
        if err:
            return {"status": "error", "error": err}

        profile_id = self._get_mrna_profile(study_id)
        if not profile_id:
            return {"status": "error", "error": f"No mRNA profile found for {cancer}"}

        eid1 = self._get_gene_id(gene1)
        eid2 = self._get_gene_id(gene2)
        if not eid1:
            return {
                "status": "error",
                "error": f"Gene '{gene1}' not found in cBioPortal",
            }
        if not eid2:
            return {
                "status": "error",
                "error": f"Gene '{gene2}' not found in cBioPortal",
            }

        sample_ids = self._get_samples(study_id, n=200)
        if not sample_ids:
            return {"status": "error", "error": f"No samples for {cancer}"}

        records = self._get_expression(profile_id, [eid1, eid2], sample_ids)
        if not records:
            return {"status": "error", "error": "Expression data unavailable"}

        # Build per-sample value maps
        vals1: Dict[str, float] = {}
        vals2: Dict[str, float] = {}
        for rec in records:
            sid = rec.get("sampleId")
            eid = rec.get("entrezGeneId")
            val = rec.get("value")
            if sid and val is not None:
                if eid == eid1:
                    vals1[sid] = float(val)
                elif eid == eid2:
                    vals2[sid] = float(val)

        # Paired samples only
        common = sorted(set(vals1) & set(vals2))
        if len(common) < 10:
            return {
                "status": "error",
                "error": f"Insufficient paired samples ({len(common)}) for correlation",
            }

        x = [vals1[s] for s in common]
        y = [vals2[s] for s in common]

        try:
            from scipy.stats import spearmanr

            corr, pval = spearmanr(x, y)
        except ImportError:
            # Manual rank correlation fallback
            def _rank(arr):
                s = sorted(range(len(arr)), key=lambda i: arr[i])
                ranks = [0.0] * len(arr)
                for rank, idx in enumerate(s):
                    ranks[idx] = float(rank + 1)
                return ranks

            rx, ry = _rank(x), _rank(y)
            n = len(rx)
            mx = sum(rx) / n
            my = sum(ry) / n
            num = sum((rx[i] - mx) * (ry[i] - my) for i in range(n))
            den = (
                sum((rx[i] - mx) ** 2 for i in range(n))
                * sum((ry[i] - my) ** 2 for i in range(n))
            ) ** 0.5
            corr = num / den if den else 0.0
            pval = None

        return {
            "status": "success",
            "data": {
                "cancer": cancer.upper(),
                "gene1": gene1,
                "gene2": gene2,
                "n_samples": len(common),
                "spearman_r": round(float(corr), 4),
                "p_value": round(float(pval), 6) if pval is not None else None,
                "profile_id": profile_id,
                "note": "TIMER2.0/3.0 API unavailable; correlation computed from cBioPortal TCGA expression",
            },
        }

    def _survival_association(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        cancer = arguments.get("cancer")
        gene = arguments.get("gene")

        if not cancer:
            return {"status": "error", "error": "cancer is required (e.g., 'BRCA')"}
        if not gene:
            return {"status": "error", "error": "gene is required (e.g., 'CD8A')"}

        study_id, err = self._resolve_study(cancer)
        if err:
            return {"status": "error", "error": err}

        profile_id = self._get_mrna_profile(study_id)
        if not profile_id:
            return {"status": "error", "error": f"No mRNA profile found for {cancer}"}

        eid = self._get_gene_id(gene)
        if not eid:
            return {"status": "error", "error": f"Gene '{gene}' not found"}

        # Get survival data
        os_months, os_status = self._get_os_data(study_id)
        if not os_months:
            return {"status": "error", "error": f"No survival data for {cancer}"}

        # Get expression for all available samples
        sample_ids = self._get_samples(study_id, n=1000)
        expr_records = self._get_expression(profile_id, [eid], sample_ids)
        if not expr_records:
            return {
                "status": "error",
                "error": f"Expression data unavailable for {gene}",
            }

        # Map sampleId → (patientId, expression) — sampleId has -01 suffix for primary tumor
        sample_to_expr: Dict[str, float] = {
            rec["sampleId"]: float(rec["value"])
            for rec in expr_records
            if rec.get("value") is not None
        }
        # Map patientId from sampleId (TCGA-XX-XXXX-01 → TCGA-XX-XXXX)
        patient_expr: Dict[str, float] = {}
        for sid, val in sample_to_expr.items():
            pid = "-".join(sid.split("-")[:3])  # TCGA-XX-XXXX
            patient_expr[pid] = val

        # Intersect with patients having OS data
        common_pids = sorted(set(patient_expr) & set(os_months) & set(os_status))
        if len(common_pids) < 20:
            return {
                "status": "error",
                "error": f"Insufficient patients with both expression and survival data ({len(common_pids)})",
            }

        # Median split
        expr_vals = [patient_expr[p] for p in common_pids]
        median_expr = sorted(expr_vals)[len(expr_vals) // 2]
        high_group = [p for p in common_pids if patient_expr[p] >= median_expr]
        low_group = [p for p in common_pids if patient_expr[p] < median_expr]

        def _parse_event(status_str: str) -> int:
            """1=event (deceased), 0=censored (living)."""
            s = str(status_str).upper()
            if "DECEASED" in s or s == "1" or s.startswith("1:"):
                return 1
            return 0

        high_t = [os_months[p] for p in high_group]
        high_e = [_parse_event(os_status[p]) for p in high_group]
        low_t = [os_months[p] for p in low_group]
        low_e = [_parse_event(os_status[p]) for p in low_group]

        # Log-rank test
        try:
            from scipy.stats import logrank, CensoredData

            x = CensoredData(
                uncensored=[t for t, e in zip(high_t, high_e) if e == 1],
                right=[t for t, e in zip(high_t, high_e) if e == 0],
            )
            y = CensoredData(
                uncensored=[t for t, e in zip(low_t, low_e) if e == 1],
                right=[t for t, e in zip(low_t, low_e) if e == 0],
            )
            result = logrank(x, y)
            logrank_stat = round(float(result.statistic), 4)
            logrank_pval = round(float(result.pvalue), 6)
        except Exception:
            logrank_stat = None
            logrank_pval = None

        def _median_survival(times, events):
            """Simple KM median survival."""
            paired = sorted(zip(times, events))
            at_risk = len(paired)
            surv = 1.0
            for t, e in paired:
                if e:
                    surv *= (at_risk - 1) / at_risk
                at_risk -= 1
                if surv <= 0.5:
                    return t
            return None

        return {
            "status": "success",
            "data": {
                "cancer": cancer.upper(),
                "gene": gene,
                "n_patients": len(common_pids),
                "median_expression_cutoff": round(float(median_expr), 4),
                "high_expression_group": {
                    "n": len(high_group),
                    "n_events": sum(high_e),
                    "median_survival_months": _median_survival(high_t, high_e),
                },
                "low_expression_group": {
                    "n": len(low_group),
                    "n_events": sum(low_e),
                    "median_survival_months": _median_survival(low_t, low_e),
                },
                "log_rank_statistic": logrank_stat,
                "log_rank_p_value": logrank_pval,
                "profile_id": profile_id,
                "note": "TIMER2.0/3.0 API unavailable; survival computed from cBioPortal TCGA data",
            },
        }
