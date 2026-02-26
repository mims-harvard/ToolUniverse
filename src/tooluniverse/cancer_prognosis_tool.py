"""
Cancer Prognosis Tool - cBioPortal-based survival and expression data retrieval.

Provides direct access to cancer genomics survival data through the cBioPortal
public REST API (www.cbioportal.org/api). Complements existing TIMER tools by
offering raw survival data retrieval and gene expression queries.

Operations:
  - get_survival_data    : Retrieve OS/DFS clinical survival data for a study
  - get_gene_expression  : Fetch gene expression across samples in a study
  - search_studies       : Search cBioPortal studies by keyword/cancer type
  - get_study_summary    : Get summary statistics for a cancer study
"""

import time
import requests
from typing import Dict, Any, List, Optional, Tuple
from .base_tool import BaseTool
from .tool_registry import register_tool

CBIOPORTAL_BASE = "https://www.cbioportal.org/api"

# Map TCGA abbreviations to cBioPortal study IDs (Firehose Legacy)
TCGA_STUDY_MAP = {
    "ACC": "acc_tcga",
    "BLCA": "blca_tcga",
    "BRCA": "brca_tcga",
    "CESC": "cesc_tcga",
    "CHOL": "chol_tcga",
    "COAD": "coadread_tcga",
    "DLBC": "dlbc_tcga",
    "ESCA": "esca_tcga",
    "GBM": "gbm_tcga",
    "HNSC": "hnsc_tcga",
    "KICH": "kich_tcga",
    "KIRC": "kirc_tcga",
    "KIRP": "kirp_tcga",
    "LAML": "laml_tcga",
    "LGG": "lgg_tcga",
    "LIHC": "lihc_tcga",
    "LUAD": "luad_tcga",
    "LUSC": "lusc_tcga",
    "MESO": "meso_tcga",
    "OV": "ov_tcga",
    "PAAD": "paad_tcga",
    "PCPG": "pcpg_tcga",
    "PRAD": "prad_tcga",
    "READ": "coadread_tcga",
    "SARC": "sarc_tcga",
    "SKCM": "skcm_tcga",
    "STAD": "stad_tcga",
    "TGCT": "tgct_tcga",
    "THCA": "thca_tcga",
    "THYM": "thym_tcga",
    "UCEC": "ucec_tcga",
    "UCS": "ucs_tcga",
    "UVM": "uvm_tcga",
}


@register_tool("CancerPrognosisTool")
class CancerPrognosisTool(BaseTool):
    """
    Cancer prognosis data retrieval from cBioPortal.

    Queries the cBioPortal REST API for survival clinical data,
    gene expression values, and study information. Provides raw data
    that can be used with local Survival Analysis tools for custom
    Kaplan-Meier, log-rank, and Cox regression analyses.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        operation_handlers = {
            "get_survival_data": self._get_survival_data,
            "get_gene_expression": self._get_gene_expression,
            "search_studies": self._search_studies,
            "get_study_summary": self._get_study_summary,
        }

        handler = operation_handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": "Unknown operation: {}".format(operation),
                "available_operations": list(operation_handlers.keys()),
            }

        try:
            return handler(arguments)
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "cBioPortal API request timed out"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to cBioPortal API"}
        except Exception as e:
            return {"status": "error", "error": "Operation failed: {}".format(str(e))}

    # -- helpers -----------------------------------------------------------------

    def _resolve_study(self, cancer_or_study):
        # type: (str) -> str
        """Resolve TCGA abbreviation or study ID to a cBioPortal study ID."""
        upper = cancer_or_study.upper()
        if upper in TCGA_STUDY_MAP:
            return TCGA_STUDY_MAP[upper]
        # Already a study ID
        return cancer_or_study

    def _api_get(self, path, params=None, timeout=30):
        # type: (str, Optional[Dict], int) -> Optional[Any]
        """GET request to cBioPortal API with retry."""
        url = "{}{}".format(CBIOPORTAL_BASE, path)
        for attempt in range(3):
            try:
                r = self.session.get(url, params=params, timeout=timeout)
                if r.status_code == 200:
                    return r.json()
                if r.status_code == 404:
                    return None
            except requests.exceptions.RequestException:
                pass
            if attempt < 2:
                time.sleep(2**attempt)
        return None

    def _api_post(self, path, json_data, params=None, timeout=60):
        # type: (str, Any, Optional[Dict], int) -> Optional[Any]
        """POST request to cBioPortal API with retry."""
        url = "{}{}".format(CBIOPORTAL_BASE, path)
        for attempt in range(3):
            try:
                r = self.session.post(
                    url, json=json_data, params=params, timeout=timeout
                )
                if r.status_code == 200:
                    return r.json()
            except requests.exceptions.RequestException:
                pass
            if attempt < 2:
                time.sleep(2**attempt)
        return None

    def _get_mrna_profile(self, study_id):
        # type: (str) -> Optional[str]
        """Find the best mRNA expression profile for a study."""
        profiles = self._api_get(
            "/studies/{}/molecular-profiles".format(study_id),
            params={"projection": "SUMMARY"},
        )
        if not profiles:
            return None
        preferred = ["_rna_seq_v2_mrna", "_rna_seq_mrna", "_mrna"]
        for suffix in preferred:
            for p in profiles:
                pid = p.get("molecularProfileId", "")
                if (
                    p.get("molecularAlterationType") == "MRNA_EXPRESSION"
                    and pid.endswith(suffix)
                    and not pid.endswith("_Zscores")
                ):
                    return pid
        return None

    def _get_gene_entrez_id(self, symbol):
        # type: (str) -> Optional[int]
        """Resolve gene symbol to Entrez ID."""
        data = self._api_get(
            "/genes/{}".format(symbol.upper()),
            params={"projection": "SUMMARY"},
            timeout=10,
        )
        if data:
            return data.get("entrezGeneId")
        return None

    # -- operations --------------------------------------------------------------

    def _get_survival_data(self, arguments):
        # type: (Dict[str, Any]) -> Dict[str, Any]
        """Retrieve OS and DFS survival clinical data for a study."""
        cancer = arguments.get("cancer")
        if not cancer:
            return {
                "status": "error",
                "error": "cancer is required (TCGA abbreviation like 'BRCA' or cBioPortal study ID)",
            }

        study_id = self._resolve_study(cancer)
        limit = arguments.get("limit", 10000)

        data = self._api_get(
            "/studies/{}/clinical-data".format(study_id),
            params={
                "clinicalDataType": "PATIENT",
                "projection": "SUMMARY",
                "pageSize": min(limit, 100000),
            },
            timeout=60,
        )
        if data is None:
            return {
                "status": "error",
                "error": "Study '{}' not found or no clinical data available".format(
                    study_id
                ),
            }

        # Extract survival-related fields
        os_months = {}  # type: Dict[str, float]
        os_status = {}  # type: Dict[str, str]
        dfs_months = {}  # type: Dict[str, float]
        dfs_status = {}  # type: Dict[str, str]
        patient_ages = {}  # type: Dict[str, str]

        survival_attrs = {"OS_MONTHS", "OS_STATUS", "DFS_MONTHS", "DFS_STATUS", "AGE"}
        for rec in data:
            attr = rec.get("clinicalAttributeId")
            if attr not in survival_attrs:
                continue
            pid = rec.get("patientId", "")
            val = rec.get("value", "")
            if attr == "OS_MONTHS":
                try:
                    os_months[pid] = float(val)
                except (ValueError, TypeError):
                    pass
            elif attr == "OS_STATUS":
                os_status[pid] = val
            elif attr == "DFS_MONTHS":
                try:
                    dfs_months[pid] = float(val)
                except (ValueError, TypeError):
                    pass
            elif attr == "DFS_STATUS":
                dfs_status[pid] = val
            elif attr == "AGE":
                patient_ages[pid] = val

        # Build patient-level survival records
        all_patients = sorted(set(os_months.keys()) | set(dfs_months.keys()))
        os_patients = sorted(set(os_months.keys()) & set(os_status.keys()))
        dfs_patients = sorted(set(dfs_months.keys()) & set(dfs_status.keys()))

        # Create OS patient-level list (up to 500 for reasonable response size)
        max_patients = min(int(arguments.get("max_patients", 500)), 2000)
        os_records = []
        for pid in os_patients[:max_patients]:
            rec = {
                "patient_id": pid,
                "os_months": os_months[pid],
                "os_status": os_status[pid],
                "event": 1
                if (
                    "DECEASED" in os_status[pid].upper()
                    or os_status[pid].startswith("1:")
                )
                else 0,
            }
            if pid in patient_ages:
                rec["age"] = patient_ages[pid]
            os_records.append(rec)

        result = {
            "status": "success",
            "data": {
                "study_id": study_id,
                "cancer": cancer.upper()
                if cancer.upper() in TCGA_STUDY_MAP
                else cancer,
                "total_patients": len(all_patients),
                "overall_survival": {
                    "n_patients": len(os_patients),
                    "n_events": sum(
                        1
                        for pid in os_patients
                        if "DECEASED" in os_status[pid].upper()
                        or os_status[pid].startswith("1:")
                    ),
                    "patients": os_records,
                },
                "disease_free_survival": {
                    "n_patients": len(dfs_patients),
                    "n_events": sum(
                        1
                        for pid in dfs_patients
                        if "Recurred" in dfs_status[pid]
                        or dfs_status[pid].startswith("1:")
                    ),
                },
                "note": "Use Survival_kaplan_meier or Survival_log_rank_test tools for analysis of this data",
            },
        }

        return result

    def _get_gene_expression(self, arguments):
        # type: (Dict[str, Any]) -> Dict[str, Any]
        """Fetch gene expression values across samples in a study."""
        cancer = arguments.get("cancer")
        gene = arguments.get("gene")

        if not cancer:
            return {
                "status": "error",
                "error": "cancer is required (e.g., 'BRCA', 'LUAD')",
            }
        if not gene:
            return {
                "status": "error",
                "error": "gene is required (e.g., 'TP53', 'BRCA1')",
            }

        study_id = self._resolve_study(cancer)
        profile_id = self._get_mrna_profile(study_id)
        if not profile_id:
            return {
                "status": "error",
                "error": "No mRNA expression profile found for {} ({})".format(
                    cancer, study_id
                ),
            }

        entrez_id = self._get_gene_entrez_id(gene)
        if not entrez_id:
            return {
                "status": "error",
                "error": "Gene '{}' not found in cBioPortal".format(gene),
            }

        # Get samples
        max_samples = min(int(arguments.get("max_samples", 500)), 2000)
        samples = self._api_get(
            "/studies/{}/samples".format(study_id),
            params={"projection": "ID", "pageSize": max_samples},
        )
        if not samples:
            return {
                "status": "error",
                "error": "No samples found for {}".format(cancer),
            }

        sample_ids = [s["sampleId"] for s in samples]

        # Fetch expression data
        expr_data = self._api_post(
            "/molecular-data/fetch",
            json_data={
                "entrezGeneIds": [entrez_id],
                "sampleMolecularIdentifiers": [
                    {"molecularProfileId": profile_id, "sampleId": sid}
                    for sid in sample_ids
                ],
            },
            params={"projection": "SUMMARY"},
        )
        if not expr_data:
            return {
                "status": "error",
                "error": "Expression data unavailable for {} in {}".format(
                    gene, cancer
                ),
            }

        # Extract values
        values = []
        for rec in expr_data:
            val = rec.get("value")
            if val is not None:
                values.append(
                    {
                        "sample_id": rec.get("sampleId"),
                        "patient_id": rec.get("patientId"),
                        "value": round(float(val), 4),
                    }
                )

        if not values:
            return {
                "status": "error",
                "error": "No expression values returned for {}".format(gene),
            }

        expr_values = [v["value"] for v in values]
        sorted_vals = sorted(expr_values)
        n = len(sorted_vals)
        mean_val = sum(sorted_vals) / n
        median_val = (
            sorted_vals[n // 2]
            if n % 2
            else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
        )

        return {
            "status": "success",
            "data": {
                "study_id": study_id,
                "gene": gene,
                "entrez_gene_id": entrez_id,
                "profile_id": profile_id,
                "n_samples": len(values),
                "expression_summary": {
                    "mean": round(mean_val, 4),
                    "median": round(median_val, 4),
                    "min": round(sorted_vals[0], 4),
                    "max": round(sorted_vals[-1], 4),
                },
                "samples": values[:max_samples],
                "note": "Values are from {} profile. Use with Survival tools for expression-survival analysis.".format(
                    profile_id
                ),
            },
        }

    def _search_studies(self, arguments):
        # type: (Dict[str, Any]) -> Dict[str, Any]
        """Search cBioPortal studies by keyword."""
        keyword = arguments.get("keyword")
        if not keyword:
            return {
                "status": "error",
                "error": "keyword is required (e.g., 'breast', 'lung', 'TCGA')",
            }

        limit = min(int(arguments.get("limit", 20)), 100)
        data = self._api_get(
            "/studies",
            params={"keyword": keyword, "projection": "SUMMARY", "pageSize": limit},
        )
        if data is None:
            return {"status": "error", "error": "Failed to search cBioPortal studies"}

        studies = []
        for s in data:
            studies.append(
                {
                    "study_id": s.get("studyId"),
                    "name": s.get("name"),
                    "description": (s.get("description", "") or "")[:200],
                    "cancer_type_id": s.get("cancerTypeId"),
                    "sample_count": s.get("allSampleCount"),
                    "reference_pmid": s.get("pmid"),
                }
            )

        return {
            "status": "success",
            "data": {
                "keyword": keyword,
                "n_results": len(studies),
                "studies": studies,
            },
        }

    def _get_study_summary(self, arguments):
        # type: (Dict[str, Any]) -> Dict[str, Any]
        """Get summary statistics for a cancer study."""
        cancer = arguments.get("cancer")
        if not cancer:
            return {
                "status": "error",
                "error": "cancer is required (e.g., 'BRCA', 'LUAD')",
            }

        study_id = self._resolve_study(cancer)

        # Fetch study info
        study_info = self._api_get("/studies/{}".format(study_id))
        if not study_info:
            return {"status": "error", "error": "Study '{}' not found".format(study_id)}

        # Fetch molecular profiles
        profiles = (
            self._api_get(
                "/studies/{}/molecular-profiles".format(study_id),
                params={"projection": "SUMMARY"},
            )
            or []
        )

        profile_summary = []
        for p in profiles:
            profile_summary.append(
                {
                    "profile_id": p.get("molecularProfileId"),
                    "name": p.get("name"),
                    "type": p.get("molecularAlterationType"),
                }
            )

        # Fetch clinical attributes
        attrs = (
            self._api_get(
                "/studies/{}/clinical-attributes".format(study_id),
                params={"projection": "SUMMARY"},
            )
            or []
        )

        survival_attrs = [
            a
            for a in attrs
            if any(
                w in a.get("displayName", "").lower()
                for w in ["survival", "status", "month", "vital", "death", "recurrence"]
            )
        ]

        return {
            "status": "success",
            "data": {
                "study_id": study_id,
                "name": study_info.get("name"),
                "description": (study_info.get("description", "") or "")[:500],
                "cancer_type_id": study_info.get("cancerTypeId"),
                "sample_count": study_info.get("allSampleCount"),
                "pmid": study_info.get("pmid"),
                "molecular_profiles": profile_summary,
                "survival_attributes": [
                    {"id": a.get("clinicalAttributeId"), "name": a.get("displayName")}
                    for a in survival_attrs
                ],
                "total_clinical_attributes": len(attrs),
                "available_tcga_types": sorted(TCGA_STUDY_MAP.keys()),
            },
        }
