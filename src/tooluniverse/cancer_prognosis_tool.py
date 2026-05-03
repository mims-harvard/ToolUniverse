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
    "COADREAD": "coadread_tcga",  # Feature-38B-04: combined colon+rectal TCGA cohort alias
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

# Feature-53A-014: common cancer name aliases → TCGA abbreviation.
# Users often pass natural-language names like 'breast', 'colon', 'lung' instead of
# TCGA codes like 'BRCA', 'COAD', 'LUAD'. Map these to the most common TCGA study.
_CANCER_NAME_ALIASES: Dict[str, str] = {
    "BREAST": "BRCA",
    "BREAST CANCER": "BRCA",
    "COLON": "COAD",
    "COLORECTAL": "COADREAD",
    "COLON CANCER": "COAD",
    "COLORECTAL CANCER": "COADREAD",
    "RECTAL": "READ",
    "LUNG": "LUAD",
    "LUNG CANCER": "LUAD",
    "LUNG ADENOCARCINOMA": "LUAD",
    "LUAD": "LUAD",
    "NSCLC": "LUAD",
    "LUNG SQUAMOUS": "LUSC",
    "LUNG SQUAMOUS CELL": "LUSC",
    "LUSC": "LUSC",
    "GLIOBLASTOMA": "GBM",
    "GBM": "GBM",
    "OVARIAN": "OV",
    "OVARY": "OV",
    "OVARIAN CANCER": "OV",
    "PROSTATE": "PRAD",
    "PROSTATE CANCER": "PRAD",
    "PANCREATIC": "PAAD",
    "PANCREAS": "PAAD",
    "PANCREATIC CANCER": "PAAD",
    "PANCREATIC DUCTAL ADENOCARCINOMA": "PAAD",
    "PDAC": "PAAD",
    "BLADDER": "BLCA",
    "BLADDER CANCER": "BLCA",
    "UROTHELIAL": "BLCA",
    "MELANOMA": "SKCM",
    "SKIN MELANOMA": "SKCM",
    "KIDNEY": "KIRC",
    "RENAL CELL CARCINOMA": "KIRC",
    "RCC": "KIRC",
    "LIVER": "LIHC",
    "HEPATOCELLULAR": "LIHC",
    "HCC": "LIHC",
    "STOMACH": "STAD",
    "GASTRIC": "STAD",
    "GASTRIC CANCER": "STAD",
    "ENDOMETRIAL": "UCEC",
    "UTERINE": "UCEC",
    "ENDOMETRIAL CANCER": "UCEC",
    "THYROID": "THCA",
    "THYROID CANCER": "THCA",
    "CERVICAL": "CESC",
    "CERVICAL CANCER": "CESC",
    "HEAD AND NECK": "HNSC",
    "HNSC": "HNSC",
    "GLIOMA": "LGG",
    "LOW GRADE GLIOMA": "LGG",
    "ACUTE MYELOID LEUKEMIA": "LAML",
    "AML": "LAML",
    "SARCOMA": "SARC",
    "TESTICULAR": "TGCT",
    # Feature-57A-004: lymphoma aliases — DLBCL is the most common TCGA lymphoma study
    "DLBCL": "DLBC",
    "DLBC": "DLBC",
    "DIFFUSE LARGE B-CELL LYMPHOMA": "DLBC",
    "DIFFUSE LARGE B CELL LYMPHOMA": "DLBC",
    "LARGE CELL LYMPHOMA": "DLBC",
    "LYMPHOMA": "DLBC",
    "B-CELL LYMPHOMA": "DLBC",
    "B CELL LYMPHOMA": "DLBC",
    "FOLLICULAR LYMPHOMA": "DLBC",  # no FL-specific TCGA study; DLBC is closest proxy
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
        # Infer operation from tool config enum (each CancerPrognosis tool has
        # a single fixed const value in the schema, e.g., "get_survival_data")
        if not operation:
            schema_op = (
                self.parameter.get("properties", {})
                .get("operation", {})
                .get("enum", [None])[0]
            )
            if schema_op:
                operation = schema_op
            else:
                return {
                    "status": "error",
                    "error": "Missing required parameter: operation. Use one of: get_survival_data, get_gene_expression, search_studies, get_study_summary",
                }

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
        # Feature-53A-014: try common cancer name aliases (e.g., 'breast' → 'BRCA' → 'brca_tcga')
        tcga_code = _CANCER_NAME_ALIASES.get(upper)
        if tcga_code and tcga_code in TCGA_STUDY_MAP:
            return TCGA_STUDY_MAP[tcga_code]
        # Already a full cBioPortal study ID (e.g., 'brca_mapk_hp_msk_2021')
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

    def _get_expression_units(self, profile_id, profile_name=None):
        # type: (str, Optional[str]) -> str
        """Feature-49A-M1: Infer expression data type/units from the cBioPortal profile.
        Feature-54A-002: Prefer the actual profile name from the API (e.g., 'mRNA expression
        (log2 RNA Seq RPKM)') over ID-based inference, since some studies use misleading
        ID suffixes (e.g., aml_ohsu_2022 uses _rna_seq_v2_mrna but stores log2 RPKM).
        """
        if profile_name:
            return profile_name
        pid = profile_id.lower()
        if "rna_seq_v2_mrna" in pid:
            return "RSEM (RNA Seq V2 normalized expected read counts)"
        if "rna_seq_mrna" in pid:
            return "RPKM (RNA-seq reads per kilobase per million)"
        if "mrna_median_all_sample" in pid or "mrna_median" in pid:
            return "median mRNA expression (microarray or RNA-seq)"
        if "_zscores" in pid:
            return "z-scores (relative expression normalized within study)"
        if "mrna" in pid:
            return "mRNA expression"
        return "expression values"

    def _get_mrna_profile(self, study_id):
        # type: (str) -> Optional[Tuple[str, str]]
        """Find the best mRNA expression profile for a study.
        Returns (profile_id, profile_name) tuple, or None if not found.
        Feature-54A-002: also return the human-readable profile name so _get_expression_units
        can use the actual description instead of inferring from the profile ID string.
        """
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
                    return (pid, p.get("name", ""))
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
        # Feature-62B-001: warn on unrecognized parameters that will be silently ignored.
        # CancerPrognosis_get_survival_data only supports cancer/cancer_type/study_id and limits.
        # Gene and subtype filtering is not supported — explicitly warn the user.
        _known_survival_params = {
            "cancer",
            "cancer_type",
            "study_id",
            "limit",
            "max_patients",
            "operation",
        }
        _unknown_survival = [k for k in arguments if k not in _known_survival_params]
        if _unknown_survival:
            return {
                "status": "error",
                "error": (
                    f"Unrecognized parameter(s) for get_survival_data: {', '.join(_unknown_survival)}. "
                    "Supported parameters: cancer (TCGA abbreviation or cBioPortal study ID), "
                    "cancer_type (alias), study_id (alias), max_patients (output limit). "
                    "Note: gene-stratified survival (high vs low expressors) and subtype filtering "
                    "are not supported by this tool — use CancerPrognosis_get_gene_expression "
                    "to get expression values per sample, then stratify externally."
                ),
            }

        cancer = (
            arguments.get("cancer")
            or arguments.get("cancer_type")
            or arguments.get("study_id")  # Feature-40A-05: study_id alias
        )
        if not cancer:
            return {
                "status": "error",
                "error": "cancer is required (TCGA abbreviation like 'BRCA' or cBioPortal study ID). "
                "Also accepted: cancer_type, study_id.",
            }

        study_id = self._resolve_study(cancer)
        # Feature-61A-002: `limit` used to be passed directly as the cBioPortal API pageSize,
        # causing severely truncated results when users passed limit=10 expecting max 10
        # patients returned (not 10 raw clinical records fetched). Now: pageSize is always
        # 10000 (enough to cover any study); `limit` is treated as alias for `max_patients`
        # (output-level control), consistent with how other tools use `limit`.
        _page_size = 10000  # internal fetch size — not user-configurable
        if arguments.get("limit") is not None:
            # Redirect user-facing limit to max_patients output control
            if "max_patients" not in arguments:
                arguments = dict(arguments)
                arguments["max_patients"] = arguments["limit"]

        # Feature-47B-01: cBioPortal clinical-data endpoint does not paginate automatically.
        # Large studies (e.g., BRCA with 50,926 clinical records) may have OS data for only a
        # fraction of the pageSize=10000 chunk. We set pageSize conservatively; callers
        # should be aware that n_patients_with_os_data may undercount the full cohort.
        data = self._api_get(
            "/studies/{}/clinical-data".format(study_id),
            params={
                "clinicalDataType": "PATIENT",
                "projection": "SUMMARY",
                "pageSize": _page_size,
            },
            timeout=60,
        )
        if data is None:
            tcga_types = sorted(TCGA_STUDY_MAP.keys())
            return {
                "status": "error",
                "error": (
                    "Study '{}' not found or no clinical data available (resolved to study_id='{}')."
                    " If this is a TCGA cancer type, use one of the 33 supported codes: {}."
                    " For non-TCGA cancers, use CancerPrognosis_search_studies(keyword='{}') to find"
                    " available studies and confirm they include survival data."
                ).format(cancer, study_id, ", ".join(tcga_types), cancer.lower()),
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

        # Create DFS patient-level list
        dfs_records = []
        for pid in dfs_patients[:max_patients]:
            rec = {
                "patient_id": pid,
                "dfs_months": dfs_months[pid],
                "dfs_status": dfs_status[pid],
                "event": 1
                if "Recurred" in dfs_status[pid] or dfs_status[pid].startswith("1:")
                else 0,
            }
            dfs_records.append(rec)

        # Feature-60A-005: detect when study uses non-standard survival attribute names.
        # Consortium studies (CPTAC, ICGC, etc.) often store survival data under
        # different field names — the tool silently returns 0 patients in that case.
        nonstandard_warning = ""
        if len(all_patients) == 0 and data:
            present_attrs = {rec.get("clinicalAttributeId", "") for rec in data}
            _survival_indicators = {
                "VITAL_STATUS",
                "OVERALL_SURVIVAL",
                "SURVIVAL_STATUS",
                "PATH_DIAG_TO_DEATH_DAYS",
                "PATH_DIAG_TO_LAST_CONTACT_DAYS",
                "DAYS_TO_DEATH",
                "DAYS_TO_LAST_FOLLOWUP",
                "DAYS_TO_LAST_CONTACT",
            }
            found = sorted(_survival_indicators & present_attrs)
            if found:
                nonstandard_warning = (
                    " WARNING: This study has {} clinical records but no standard"
                    " OS_MONTHS/OS_STATUS fields. It uses non-standard survival"
                    " attributes ({}) that this tool does not currently support."
                    " Use CancerPrognosis_search_studies to verify study content,"
                    " or query the cBioPortal API directly for this study."
                ).format(len(data), ", ".join(found))

        # Feature-47B-01: detect possible truncation — clinical data API returns a single page.
        # If we retrieved exactly 10,000 records total, there may be more data in the study.
        truncation_warning = (
            " WARNING: This study may have more clinical data than retrieved. "
            "The cBioPortal API returns a single page of up to 10,000 clinical records; "
            "for large cohorts (e.g., BRCA), this may cover fewer than 50% of patients. "
            "OS patient count may undercount the full cohort."
            if len(data) >= 10000
            else ""
        )
        result = {
            "status": "success",
            "data": {
                "study_id": study_id,
                "cancer": cancer.upper()
                if cancer.upper() in TCGA_STUDY_MAP
                else cancer,
                "total_patients": len(all_patients),
                "overall_survival": {
                    "total_patients_with_os_data": len(os_patients),
                    "n_patients": len(os_records),
                    "n_events": sum(1 for r in os_records if r["event"] == 1),
                    "patients": os_records,
                },
                "disease_free_survival": {
                    "total_patients_with_dfs_data": len(dfs_patients),
                    "n_patients": len(dfs_records),
                    "n_events": sum(1 for r in dfs_records if r["event"] == 1),
                    "patients": dfs_records,
                },
                "note": "Use Survival_kaplan_meier or Survival_log_rank_test tools for analysis of this data."
                + truncation_warning
                + nonstandard_warning,
            },
        }

        return result

    def _get_gene_expression(self, arguments):
        # type: (Dict[str, Any]) -> Dict[str, Any]
        """Fetch gene expression values across samples in a study."""
        # Feature-53A-013: give explicit study_id priority when it looks like a full cBioPortal
        # study ID (contains underscores and is not a TCGA abbreviation). Previously,
        # 'cancer' or 'cancer_type' could silently override study_id because they appear
        # first in the or-chain — e.g., cancer='brca' + study_id='brca_mapk_hp_msk_2021'
        # would resolve to 'brca_tcga' instead of the specified study.
        study_id_arg = arguments.get("study_id")
        cancer_arg = arguments.get("cancer") or arguments.get("cancer_type")
        if (
            study_id_arg
            and "_" in str(study_id_arg)
            and str(study_id_arg).upper() not in TCGA_STUDY_MAP
            and str(study_id_arg).upper() not in _CANCER_NAME_ALIASES
        ):
            # Explicit full cBioPortal study ID (e.g., 'brca_mapk_hp_msk_2021') — use directly
            cancer = study_id_arg
        else:
            cancer = cancer_arg or study_id_arg  # Feature-40A-05
        gene = (
            arguments.get("gene")
            or arguments.get("gene_symbol")  # Feature-47A-03
            or arguments.get("gene_name")
        )

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

        # Feature-53A-013: explicit study_id tracking for study_note message (Feature-54A-004)
        study_was_explicit = (
            cancer == study_id_arg and study_id_arg and "_" in str(study_id_arg)
        )
        study_id = self._resolve_study(cancer)
        # Feature-54A-002: _get_mrna_profile now returns (profile_id, profile_name) tuple
        profile_result = self._get_mrna_profile(study_id)
        if not profile_result:
            # Feature-58B-007: distinguish "not a TCGA type" from "study exists but no expression data".
            # Provide actionable guidance rather than a terse error.
            tcga_types = sorted(TCGA_STUDY_MAP.keys())
            return {
                "status": "error",
                "error": (
                    "No mRNA expression profile found for '{}' (resolved to study_id='{}')."
                    " If this is a TCGA cancer type, use one of the 33 supported codes: {}."
                    " For non-TCGA cancers, use CancerPrognosis_search_studies(keyword='{}') to find"
                    " available studies and confirm they include an mRNA expression profile."
                ).format(cancer, study_id, ", ".join(tcga_types), cancer.lower()),
            }
        profile_id, profile_name = profile_result

        entrez_id = self._get_gene_entrez_id(gene)
        if not entrez_id:
            return {
                "status": "error",
                "error": "Gene '{}' not found in cBioPortal".format(gene),
            }

        # Get samples
        # Feature-44A-02: max_samples is the desired *output* count, not the fetch limit.
        # Not every sample has expression data for every gene (especially low-expressed genes
        # or genes absent from array studies). Fetch up to 5x more samples than requested
        # so we have enough raw data to fill the requested output size.
        # Feature-61A-003: accept max_patients as alias for max_samples (consistent with
        # get_survival_data which uses max_patients as its output-size parameter).
        max_samples = min(
            int(arguments.get("max_samples") or arguments.get("max_patients") or 500),
            2000,
        )
        fetch_size = min(max(max_samples * 5, 500), 10000)
        samples = self._api_get(
            "/studies/{}/samples".format(study_id),
            params={"projection": "ID", "pageSize": fetch_size},
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

        # Feature-49A-M1: derive expression units from profile_id so users know the scale
        # Feature-54A-002: pass profile_name so actual API description is used instead of inference
        expression_units = self._get_expression_units(profile_id, profile_name)

        # Feature-49A-M3: detect patients with multiple samples (primary vs. recurrent aliquots).
        # TCGA samples are suffixed -01 (primary), -02 (recurrence), etc. Joining on patient_id
        # downstream will silently double-count these patients in survival analysis.
        patient_sample_counts: Dict[str, int] = {}
        for v in values:
            pid = v.get("patient_id", "")
            if pid:
                patient_sample_counts[pid] = patient_sample_counts.get(pid, 0) + 1
        multi_sample_patients = sorted(
            p for p, c in patient_sample_counts.items() if c > 1
        )
        multi_sample_note = ""
        # Feature-50B-001: structured duplicate_aliquot_warning field (in addition to note)
        # Feature-51A-004: clarify that detection covers ALL fetched samples, not just the
        # max_samples slice returned. This prevents confusion when the user sees the warning
        # but doesn't find the affected patients in the returned sample slice.
        duplicate_aliquot_warning = None
        if multi_sample_patients:
            multi_sample_note = (
                " WARNING: {} patient(s) have multiple samples (e.g., primary + recurrence) "
                "detected across all {} fetched expression records. "
                "Joining on patient_id will double-count these patients. "
                "Affected patients: {}.".format(
                    len(multi_sample_patients),
                    len(values),
                    ", ".join(multi_sample_patients[:5])
                    + (" ..." if len(multi_sample_patients) > 5 else ""),
                )
            )
            duplicate_aliquot_warning = {
                "n_affected_patients": len(multi_sample_patients),
                "detection_scope": "all_fetched_samples",
                "n_samples_checked": len(values),
                "affected_patient_ids": multi_sample_patients[:10],
                "message": "These patients have multiple samples (e.g., primary + recurrence aliquots) "
                "detected across all fetched expression records (not just the returned slice). "
                "Joining on patient_id will double-count them in survival analysis. "
                "Deduplicate by keeping only the primary tumor sample (-01 suffix) before merging.",
            }

        # Feature-53A-015 / Feature-56A-005: truncation is now surfaced at the top-level response via
        # `truncated` and `truncation_note` fields (see bottom of function). Do not embed it
        # in the note string to avoid duplicate information in two places.

        result_data: Dict[str, Any] = {
            "study_id": study_id,
            # Feature-51A-011: disclose auto-selected study so users know which of multiple
            # available studies was used. "OV" auto-resolves to ov_tcga (Firehose Legacy),
            # but ov_tcga_pan_can_atlas_2018 or hgsoc_tcga_gdc may be preferable.
            # Feature-54A-004: don't say "Auto-selected" when user explicitly specified study_id
            "study_note": (
                "Using explicitly specified study_id='{}'.".format(study_id)
                if study_was_explicit
                else "Auto-selected study_id='{}'. Use CancerPrognosis_search_studies "
                "to find alternative cohorts for this cancer type.".format(study_id)
            ),
            "gene": gene,
            "entrez_gene_id": entrez_id,
            "profile_id": profile_id,
            "expression_units": expression_units,
            "n_samples_with_expression_data": len(values),
            "n_samples_returned": len(values[:max_samples]),
            "expression_summary": {
                "mean": round(mean_val, 4),
                "median": round(median_val, 4),
                "min": round(sorted_vals[0], 4),
                "max": round(sorted_vals[-1], 4),
            },
            "samples": values[:max_samples],
            "note": "Values are from {} profile ({}). Use with Survival tools for expression-survival analysis.{}".format(
                profile_id, expression_units, multi_sample_note
            ),
        }
        if duplicate_aliquot_warning is not None:
            result_data["duplicate_aliquot_warning"] = duplicate_aliquot_warning

        # Feature-55A-006: add top-level truncated flag so callers immediately see the dataset
        # is incomplete without parsing the note string.
        response: Dict[str, Any] = {"status": "success", "data": result_data}
        if len(values) > max_samples:
            response["truncated"] = True
            response["truncation_note"] = (
                "Returning {ret} of {total} samples. Pass max_samples={total} "
                "(up to 2000) to retrieve the full dataset.".format(
                    ret=len(values[:max_samples]), total=len(values)
                )
            )
        return response

    def _search_studies(self, arguments):
        # type: (Dict[str, Any]) -> Dict[str, Any]
        """Search cBioPortal studies by keyword."""
        keyword = (
            arguments.get("keyword")
            or arguments.get("cancer_type")
            or arguments.get("cancer")
            or arguments.get("query")  # Feature-40A-07
        )
        if not keyword:
            return {
                "status": "error",
                "error": "keyword is required (e.g., 'breast', 'lung', 'TCGA'). Also accepted: cancer_type, cancer, query.",
            }

        limit = min(int(arguments.get("limit", 20)), 100)
        # cBioPortal /api/studies does not support keyword filtering — fetch all and filter locally
        # Use DETAILED projection to get accurate sample counts (SUMMARY returns allSampleCount=1)
        data = self._api_get(
            "/studies",
            params={"projection": "DETAILED", "pageSize": 1000},
        )
        if data is None:
            return {"status": "error", "error": "Failed to search cBioPortal studies"}

        keyword_lower = keyword.lower()
        studies = []
        for s in data:
            name = s.get("name", "") or ""
            description = s.get("description", "") or ""
            study_id = s.get("studyId", "") or ""
            cancer_type_id = s.get("cancerTypeId", "") or ""
            # Filter: keyword must appear in name, description, studyId, or cancerTypeId
            if (
                keyword_lower in name.lower()
                or keyword_lower in description.lower()
                or keyword_lower in study_id.lower()
                or keyword_lower in cancer_type_id.lower()
            ):
                studies.append(
                    {
                        "study_id": study_id,
                        "name": name,
                        "description": description[:200],
                        "cancer_type_id": cancer_type_id,
                        "sample_count": max(
                            s.get("allSampleCount") or 0,
                            s.get("sequencedSampleCount") or 0,
                            s.get("cnaSampleCount") or 0,
                        )
                        or None,
                        "reference_pmid": s.get("pmid"),
                    }
                )
            if len(studies) >= limit:
                break

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
        cancer = (
            arguments.get("cancer")
            or arguments.get("cancer_type")
            or arguments.get("study_id")  # Feature-40A-05
        )
        if not cancer:
            return {
                "status": "error",
                "error": "cancer is required (e.g., 'BRCA', 'LUAD'). Also accepted: cancer_type, study_id.",
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
                "sample_count": max(
                    study_info.get("allSampleCount") or 0,
                    study_info.get("sequencedSampleCount") or 0,
                    study_info.get("cnaSampleCount") or 0,
                )
                or None,
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
