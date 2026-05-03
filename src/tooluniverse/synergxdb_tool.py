"""
SYNERGxDB Drug Combination Synergy Database Tool

Provides access to the SYNERGxDB REST API for querying drug combination
synergy screening data across multiple cancer cell line datasets.

SYNERGxDB integrates 22,507 unique drug combinations (1977 compounds)
screened against 151 cancer cell lines from 9 major studies including
NCI-ALMANAC, MERCK, MIT-MELANOMA, VISAGE, DECREASE, YALE-TNBC, YALE-PDAC, STANFORD, and CLOUD.

API base: https://synergxdb.ca/api/
No authentication required.

Reference: Seo et al., NAR 2020 (PMID: 32442307)
"""

import requests
from typing import Dict, Any, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool


SYNERGXDB_BASE_URL = "https://synergxdb.ca/api"


@register_tool("SYNERGxDBTool")
class SYNERGxDBTool(BaseTool):
    """
    Tool for querying the SYNERGxDB drug combination synergy database.

    SYNERGxDB is a comprehensive database integrating drug combination
    screening data from 9 major studies with synergy scores (Bliss, Loewe,
    HSA, ZIP) and pharmacogenomic biomarker associations.

    Supported operations:
    - search_combos: Search drug combination synergy scores
    - get_combo_matrix: Get dose-response matrix data
    - list_drugs: List all drugs in the database
    - get_drug: Get drug details by ID
    - list_cell_lines: List all cell lines
    - list_datasets: List all screening datasets
    - get_combo_stats: Get per-dataset combination statistics
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        self.session = requests.Session()
        self.timeout = 30

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the SYNERGxDB API tool with given arguments."""
        operation = arguments.get("operation")
        if not operation:
            # Infer operation from tool config (each tool has a fixed const operation)
            schema_op = (
                self.tool_config.get("parameter", {})
                .get("properties", {})
                .get("operation", {})
                .get("enum", [None])[0]
            )
            if schema_op:
                operation = schema_op
            else:
                return {
                    "status": "error",
                    "error": "Missing required parameter: operation",
                }

        operation_handlers = {
            "search_combos": self._search_combos,
            "get_combo_matrix": self._get_combo_matrix,
            "list_drugs": self._list_drugs,
            "get_drug": self._get_drug,
            "list_cell_lines": self._list_cell_lines,
            "list_datasets": self._list_datasets,
            "get_combo_stats": self._get_combo_stats,
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
            return {"status": "error", "error": "SYNERGxDB API request timed out"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to SYNERGxDB API"}
        except Exception as e:
            return {"status": "error", "error": f"SYNERGxDB operation failed: {str(e)}"}

    def _make_request(self, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        """Make GET request to SYNERGxDB API."""
        url = f"{SYNERGXDB_BASE_URL}/{endpoint}"
        response = self.session.get(url, params=params or {}, timeout=self.timeout)
        if response.status_code == 200:
            return {"ok": True, "data": response.json()}
        elif response.status_code == 404:
            # Feature-36A-04: 404 means no data for these params (a normal research outcome),
            # not a real error. Return ok=True with empty data so callers can handle it
            # as empty results (exit code 0) rather than a failure (exit code 1).
            return {"ok": True, "data": [], "no_data": True}
        elif response.status_code == 400:
            try:
                err = response.json()
                return {
                    "ok": False,
                    "error": err.get("error", err.get("message", "Bad request")),
                }
            except Exception:
                return {"ok": False, "error": "Bad request - check parameters"}
        else:
            return {
                "ok": False,
                "error": f"API request failed with status {response.status_code}",
                "detail": response.text[:500],
            }

    # Feature-37A-05: dataset name → ID mapping (from /api/datasets/)
    _DATASET_NAME_TO_ID = {
        "NCI-ALMANAC": 2,
        "MERCK": 1,
        "MIT-MELANOMA": 7,
        "VISAGE": 10,
        "DECREASE": 9,
        "YALE-TNBC": 5,
        "YALE-PDAC": 4,
        "STANFORD": 8,
        "CLOUD": 6,
    }

    # Feature-46B-05: Map common tissue aliases to SYNERGxDB tissue column values.
    # Valid SYNERGxDB tissue names (from /api/cell_lines/): "blood", "bone", "brain",
    # "breast", "cervix", "colorectal", "kidney", "liver", "lung", "mesothelioma",
    # "ovary", "pancreas", "prostate", "skin", "upper digestive tract", "gastric".
    # "colon" silently returns 0 results — must be "colorectal".
    # "melanoma" silently returns 0 results — must be "skin" (Feature-48B-07).
    # Feature-60B-002: API uses "brain" not "CNS" — CNS/glioma aliases must map to "brain".
    _TISSUE_ALIASES: Dict[str, str] = {
        "colon": "colorectal",
        "rectal": "colorectal",
        "crc": "colorectal",
        "colorectal cancer": "colorectal",
        "colon cancer": "colorectal",
        "leukemia": "blood",
        "lymphoma": "blood",
        "nsclc": "lung",
        "luad": "lung",
        "brca": "breast",
        "melanoma": "skin",  # Feature-48B-07: SYNERGxDB uses "skin" not "melanoma"
        "cns": "brain",  # Feature-60B-002: API column value is "brain" not "CNS"
        "gbm": "brain",
        "glioblastoma": "brain",
        "glioma": "brain",
        "upper gi": "upper digestive tract",
        "gastroesophageal": "upper digestive tract",
    }

    # Feature-45A-03: SYNERGxDB stores some drugs under IUPAC/chemical names instead of
    # common drug names. Map common synonyms to SYNERGxDB stored names.
    # Feature-52B-005: add common "5-FU" aliases for fluorouracil.
    _DRUG_SYNONYMS: Dict[str, str] = {
        "cisplatin": "diamminedichloroplatinum",
        "cis-platinum": "diamminedichloroplatinum",
        "platinol": "diamminedichloroplatinum",
        "carboplatin": "carboplat",  # DB00958 carboplatin
        "taxol": "paclitaxel",
        "taxotere": "docetaxel",
        "velcade": "bortezomib",
        "gleevec": "imatinib",
        "sprycel": "dasatinib",
        "iressa": "gefitinib",
        "tarceva": "erlotinib",
        "herceptin": "trastuzumab",
        "avastin": "bevacizumab",
        "rituxan": "rituximab",
        # Feature-52B-005: "5-FU" is the universal clinical shorthand for fluorouracil
        "5-fu": "fluorouracil",
        "5fu": "fluorouracil",
        "5-fluorouracil": "fluorouracil",
        "5 fluorouracil": "fluorouracil",
    }

    def _resolve_drug_id_by_name(self, name: str) -> Optional[int]:
        """Resolve a drug name to SYNERGxDB integer drug ID via client-side name matching.

        Returns the first matching drug ID, or None if not found.
        """
        result = self._make_request("drugs/")
        if not result.get("ok"):
            return None
        drugs = result.get("data", [])
        if not isinstance(drugs, list):
            return None
        name_lower = name.lower().strip()
        # Feature-45A-03: check synonym mapping first (e.g., "cisplatin" → "diamminedichloroplatinum")
        effective_name = self._DRUG_SYNONYMS.get(name_lower, name_lower)
        # Feature-47A-02: prefer exact match over substring match to avoid "Desmethyl Erlotinib"
        # matching before "Erlotinib" when drug_name_1="erlotinib" is requested.
        # Two-pass: pass 1 = exact, pass 2 = substring fallback.
        for drug in drugs:
            drug_name = str(drug.get("drug_name", drug.get("name", ""))).lower()
            if effective_name == drug_name:
                return drug.get("idDrug") or drug.get("drug_id") or drug.get("id")
        for drug in drugs:
            drug_name = str(drug.get("drug_name", drug.get("name", ""))).lower()
            if effective_name in drug_name:
                return drug.get("idDrug") or drug.get("drug_id") or drug.get("id")
        # If synonym lookup failed, try original name (exact then substring)
        if effective_name != name_lower:
            for drug in drugs:
                drug_name = str(drug.get("drug_name", drug.get("name", ""))).lower()
                if name_lower == drug_name:
                    return drug.get("idDrug") or drug.get("drug_id") or drug.get("id")
            for drug in drugs:
                drug_name = str(drug.get("drug_name", drug.get("name", ""))).lower()
                if name_lower in drug_name:
                    return drug.get("idDrug") or drug.get("drug_id") or drug.get("id")
        return None

    def _search_combos(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search drug combination synergy scores."""
        drug_id_1 = arguments.get("drug_id_1")
        drug_id_2 = arguments.get("drug_id_2")
        # Feature-45B-02: accept tissue_name and tissue as intuitive aliases for sample
        # Feature-55A-011: also accept cancer_type as alias (silently ignored before)
        sample = (
            arguments.get("sample")
            or arguments.get("tissue_name")
            or arguments.get("tissue")
            or arguments.get("cancer_type")
        )
        # Feature-46B-05: normalize common tissue aliases to SYNERGxDB column values
        if sample:
            sample = self._TISSUE_ALIASES.get(sample.lower(), sample)
            # Feature-59A-009: validate tissue at input — unrecognized tissue silently returns 0
            # results when both drugs are found, giving a misleading "not tested together" message.
            # Feature-60B-002/003: use actual API tissue values from /api/cell_lines/
            _valid_tissues = set(self._TISSUE_ALIASES.values())
            _valid_tissues.update(
                {
                    "blood",
                    "bone",
                    "brain",
                    "breast",
                    "cervix",
                    "colorectal",
                    "kidney",
                    "liver",
                    "lung",
                    "mesothelioma",
                    "ovary",
                    "pancreas",
                    "prostate",
                    "skin",
                    "upper digestive tract",
                    "gastric",
                }
            )
            if sample not in _valid_tissues and sample.lower() not in {
                t.lower() for t in _valid_tissues
            }:
                return {
                    "status": "error",
                    "error": (
                        f"Tissue/cancer type '{sample}' is not recognized in SYNERGxDB. "
                        f"Valid tissue names: {', '.join(sorted(_valid_tissues))}. "
                        "Remove the tissue filter to search across all tissues."
                    ),
                }
        dataset = arguments.get("dataset")
        page = arguments.get("page", 1)
        # Feature-59A-008/59B-005: accept "limit" (ToolUniverse convention) as alias for "per_page"
        per_page = arguments.get("limit") or arguments.get("per_page", 20)

        # Feature-43A-01/02: accept drug_name_1/drug_name_2 (and intuitive drug1/drug2 aliases)
        # that auto-resolve to integer drug IDs via the /drugs/ endpoint.
        for id_key, name_key in (
            ("drug_id_1", "drug_name_1"),
            ("drug_id_1", "drug1"),
            ("drug_id_2", "drug_name_2"),
            ("drug_id_2", "drug2"),
        ):
            name_val = arguments.get(name_key)
            if name_val and not arguments.get(id_key):
                resolved = self._resolve_drug_id_by_name(str(name_val))
                if resolved is None:
                    return {
                        "status": "error",
                        "error": f"Drug '{name_val}' not found in SYNERGxDB. "
                        "SYNERGxDB covers cytotoxic chemotherapy combinations from 9 published "
                        "screening studies; most targeted therapies (BRAF/MEK/KRAS inhibitors) "
                        "and biologics (monoclonal antibodies) are not included. "
                        "Use SYNERGxDB_list_drugs with a query to search available drugs.",
                    }
                if id_key == "drug_id_1":
                    drug_id_1 = resolved
                else:
                    drug_id_2 = resolved

        # Feature-37A-05: accept dataset as string name and convert to integer ID
        if dataset is not None and isinstance(dataset, str) and not dataset.isdigit():
            mapped = self._DATASET_NAME_TO_ID.get(dataset.upper())
            if mapped is not None:
                dataset = mapped
            else:
                available = ", ".join(self._DATASET_NAME_TO_ID.keys())
                return {
                    "status": "error",
                    "error": f"Unknown dataset name '{dataset}'. Available: {available}. "
                    "You can also pass the integer dataset ID directly.",
                }

        if not drug_id_1 and not drug_id_2 and not dataset:
            return {
                "status": "error",
                "error": "At least one of drug_id_1, drug_id_2, drug_name_1, drug_name_2, or dataset is required. "
                "Use drug_name_1/drug_name_2 for automatic ID lookup (e.g., 'imatinib', 'gemcitabine'). "
                "To find drug IDs, use SYNERGxDB_list_drugs (filter by name with 'query' param). "
                "To find dataset names, use SYNERGxDB_list_datasets. ",
            }

        params = {"page": page, "perPage": per_page}
        if drug_id_1:
            params["drugId1"] = drug_id_1
        if drug_id_2:
            params["drugId2"] = drug_id_2
        if sample:
            params["sample"] = sample
        if dataset:
            params["dataset"] = dataset

        result = self._make_request("combos/", params)
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        data = result["data"]

        # Feature-50A-003: filter self-combination entries (drugA==drugB) when only one
        # drug is specified. These occur when the same drug appears as both partners.
        if (drug_id_1 or drug_id_2) and not (drug_id_1 and drug_id_2):
            if isinstance(data, list):
                data = [
                    x
                    for x in data
                    if not (
                        x.get("idDrug1") is not None
                        and x.get("idDrug1") == x.get("idDrug2")
                    )
                ]

        if result.get("no_data") or not data:
            # Feature-44A-03: distinguish "drug not in DB" vs "combo not tested" in the message
            if drug_id_1 and drug_id_2:
                # Feature-46B-04: note standard-of-care regimens that are absent from SYNERGxDB
                folfox_hint = ""
                # Oxaliplatin ID=80, Fluorouracil ID=41, Irinotecan ID=54 (approximate)
                # Rather than hardcoding IDs, check the drug names that were resolved
                drug_name_1_lower = str(
                    arguments.get("drug_name_1") or arguments.get("drug1") or ""
                ).lower()
                drug_name_2_lower = str(
                    arguments.get("drug_name_2") or arguments.get("drug2") or ""
                ).lower()
                _folfox_drugs = {
                    "oxaliplatin",
                    "fluorouracil",
                    "5-fu",
                    "5fu",
                    "leucovorin",
                }
                _folfiri_drugs = {
                    "irinotecan",
                    "fluorouracil",
                    "5-fu",
                    "5fu",
                    "leucovorin",
                }
                if (
                    drug_name_1_lower in _folfox_drugs
                    and drug_name_2_lower in _folfox_drugs
                ) or (
                    drug_name_1_lower in _folfiri_drugs
                    and drug_name_2_lower in _folfiri_drugs
                ):
                    folfox_hint = (
                        " Note: standard-of-care CRC regimens (FOLFOX, FOLFIRI, CAPOX) are not "
                        "represented in SYNERGxDB's 9 screening studies, which focus on pairwise "
                        "in vitro cytotoxicity rather than clinically-validated regimens."
                    )
                # Feature-61B-002: irinotecan→SN-38 hint for the two-drug failure path.
                _irinotecan_names = {
                    "irinotecan",
                    "camptosar",
                    "cpt-11",
                    "camptothecin-11",
                }
                _sn38_hint = ""
                if (
                    drug_name_1_lower in _irinotecan_names
                    or drug_name_2_lower in _irinotecan_names
                ):
                    _sn38_hint = (
                        " Note: Irinotecan is a prodrug; its active metabolite "
                        "SN-38 is stored in SYNERGxDB as 'SN 38 Lactone' (drug ID 87, "
                        "datasets: STANFORD, YALE-TNBC, MERCK, NCI-ALMANAC, YALE-PDAC). "
                        "Try replacing irinotecan with drug_name='SN 38 Lactone' in your query."
                    )
                # Feature-62A-005: when a tissue/dataset filter is active, probe whether the combo
                # exists without the filter — "not tested in any dataset" is false if the combo
                # exists in other tissues. Show actual available tissues for the two-drug combo.
                if sample or dataset:
                    combo_probe = self._make_request(
                        "combos/",
                        {
                            "drugId1": drug_id_1,
                            "drugId2": drug_id_2,
                            "page": 1,
                            "perPage": 100,
                        },
                    )
                    if combo_probe.get("ok") and combo_probe.get("data"):
                        probe_data = combo_probe["data"]
                        tissues = sorted(
                            {x.get("tissue", "") for x in probe_data if x.get("tissue")}
                        )
                        filter_desc = (
                            f" for tissue='{sample}'"
                            if sample
                            else f" for dataset={dataset!r}"
                        )
                        tissue_str = (
                            ", ".join(f"'{t}'" for t in tissues)
                            if tissues
                            else "unknown"
                        )
                        msg = (
                            f"No combination data found for drug IDs {drug_id_1} and {drug_id_2}"
                            f"{filter_desc}. This combination IS tested in SYNERGxDB but not in "
                            f"the requested tissue/dataset. Available tissues for this combo: "
                            f"{tissue_str}. Remove the tissue filter to see all data."
                            + folfox_hint
                        )
                    else:
                        msg = (
                            f"No combination data found: drug IDs {drug_id_1} and {drug_id_2} were both "
                            "found in SYNERGxDB but this specific combination was not tested together in "
                            "any of the 9 integrated datasets (NCI-ALMANAC, MERCK, MIT-MELANOMA, VISAGE, "
                            "DECREASE, YALE-TNBC, YALE-PDAC, STANFORD, CLOUD). "
                            "Try SYNERGxDB_search_combos with only one drug_id to see what combinations "
                            "each drug has been tested in." + folfox_hint + _sn38_hint
                        )
                else:
                    msg = (
                        f"No combination data found: drug IDs {drug_id_1} and {drug_id_2} were both "
                        "found in SYNERGxDB but this specific combination was not tested together in "
                        "any of the 9 integrated datasets (NCI-ALMANAC, MERCK, MIT-MELANOMA, VISAGE, "
                        "DECREASE, YALE-TNBC, YALE-PDAC, STANFORD, CLOUD). "
                        "Try SYNERGxDB_search_combos with only one drug_id to see what combinations "
                        "each drug has been tested in." + folfox_hint + _sn38_hint
                    )
            elif drug_id_1 or drug_id_2:
                found_id = drug_id_1 or drug_id_2
                id_param = "drugId1" if drug_id_1 else "drugId2"
                # Feature-49A-H2: if a tissue/dataset filter was active, probe what data the drug
                # actually has — "try removing filters" is misleading if the drug has no data
                # in any tissue. Show available tissues so the user knows the real situation.
                if sample or dataset:
                    probe = self._make_request(
                        "combos/", {id_param: found_id, "page": 1, "perPage": 1000}
                    )
                    if probe.get("ok") and probe.get("data"):
                        probe_data = probe["data"]
                        # Feature-51A-006: SYNERGxDB combo records use field "tissue" for
                        # tissue type (e.g., "breast"), NOT "sample" (which is absent).
                        tissues = sorted(
                            {x.get("tissue", "") for x in probe_data if x.get("tissue")}
                        )
                        sources = sorted(
                            {
                                x.get("sourceName", "")
                                for x in probe_data
                                if x.get("sourceName")
                            }
                        )
                        filter_desc = (
                            f" (tissue='{sample}')"
                            if sample
                            else f" (dataset={dataset!r})"
                        )
                        tissue_str = (
                            ", ".join(f"'{t}'" for t in tissues)
                            if tissues
                            else "none in first 1000 records"
                        )
                        source_str = ", ".join(sources) if sources else "unknown"
                        # Feature-52B-004/006: for irinotecan specifically, hint that its
                        # active metabolite SN-38 (stored as "SN 38 Lactone") may have
                        # data in tissues where irinotecan itself is absent.
                        drug_name_requested = str(
                            arguments.get("drug_name_1")
                            or arguments.get("drug1")
                            or arguments.get("drug_name_2")
                            or arguments.get("drug2")
                            or ""
                        ).lower()
                        metabolite_hint = ""
                        if drug_name_requested in {
                            "irinotecan",
                            "camptosar",
                            "cpt-11",
                            "camptothecin-11",
                        }:
                            metabolite_hint = (
                                " Note: Irinotecan is a prodrug; its active metabolite "
                                "SN-38 is stored in SYNERGxDB as 'SN 38 Lactone' (drug ID 87, "
                                "datasets: STANFORD, YALE-TNBC, MERCK, NCI-ALMANAC, YALE-PDAC). "
                                "Try SYNERGxDB_search_combos with drug_name_1='SN 38 Lactone' "
                                "for combination data across more tissues."
                            )
                        msg = (
                            f"No combination data found for drug ID {found_id}{filter_desc}. "
                            f"This drug has no data for the requested filter. "
                            f"Available tissues in the first 1000 records: {tissue_str} "
                            f"(sources: {source_str}). "
                            f"Run SYNERGxDB_search_combos with only {id_param}={found_id} "
                            f"(no tissue/dataset filter) to see all available combinations."
                            + metabolite_hint
                        )
                    else:
                        msg = (
                            f"No combination data found for drug ID {found_id} in SYNERGxDB. "
                            "This drug has no tested combinations in any of the 9 integrated "
                            "screening studies (NCI-ALMANAC, MERCK, MIT-MELANOMA, VISAGE, "
                            "DECREASE, YALE-TNBC, YALE-PDAC, STANFORD, CLOUD)."
                        )
                else:
                    msg = (
                        f"No combination data found for drug ID {found_id} in SYNERGxDB. "
                        "This drug may not have any tested combinations in the 9 integrated studies. "
                        "Use SYNERGxDB_list_datasets to see available data."
                    )
            else:
                # Feature-57A-003: add BCL2 inhibitor hint when relevant drug names are queried
                _drug_q = " ".join(
                    str(arguments.get(k, ""))
                    for k in (
                        "drug_name_1",
                        "drug1",
                        "drug_name_2",
                        "drug2",
                        "drug_name",
                    )
                ).lower()
                _bcl2_hint = ""
                if any(
                    kw in _drug_q
                    for kw in (
                        "venetoclax",
                        "navitoclax",
                        "bcl-2",
                        "bcl2",
                        "abt-199",
                        "abt-263",
                    )
                ):
                    _bcl2_hint = (
                        " Note: BCL2 inhibitors such as venetoclax (ABT-199) and navitoclax "
                        "(ABT-263) are not in the NCI-ALMANAC cytotoxic screen. "
                        "SYNERGxDB does not cover targeted agent combinations unless they appear "
                        "in one of the 9 integrated studies. Use CIViC or PharmacoDB for "
                        "clinical evidence on BCL2 inhibitor combinations."
                    )
                msg = (
                    "No combination data found for the given parameters. "
                    "SYNERGxDB covers cytotoxic chemotherapy combinations from 9 studies; "
                    "use SYNERGxDB_list_drugs to verify drug availability." + _bcl2_hint
                )
            return {
                "status": "success",
                "data": [],
                "count": 0,
                "message": msg,
            }
        return {
            "status": "success",
            "data": data,
            "count": len(data),
        }

    def _get_combo_matrix(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get dose-response matrix for a specific drug combination."""
        combo_id = arguments.get("combo_id")
        source_id = arguments.get("source_id")

        if not combo_id or not source_id:
            return {
                "status": "error",
                "error": "Both combo_id and source_id are required",
            }

        result = self._make_request(
            "combos/matrix",
            {
                "comboId": combo_id,
                "idSource": source_id,
            },
        )
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        data = result["data"]
        return {
            "status": "success",
            "data": data,
            "count": len(data),
        }

    def _list_drugs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List all drugs in the SYNERGxDB database."""
        result = self._make_request("drugs/")
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        data = result["data"]

        # Feature-35A-08: client-side name filtering if query/name/search is provided
        name_filter = (
            arguments.get("query") or arguments.get("name") or arguments.get("search")
        )
        synonym_used = None
        if name_filter and isinstance(data, list):
            name_lower = name_filter.lower()
            # Feature-53B-007: apply synonym expansion in list_drugs — _DRUG_SYNONYMS maps
            # common names to SYNERGxDB stored names (e.g., "cisplatin" →
            # "diamminedichloroplatinum"). Without this, list_drugs(query="cisplatin")
            # returned empty because the client-side filter ran against
            # "diamminedichloroplatinum" only. The synonym map was previously only used
            # in _resolve_drug_id_by_name (search_combos) but not in _list_drugs.
            effective_name = self._DRUG_SYNONYMS.get(name_lower, name_lower)
            if effective_name != name_lower:
                synonym_used = effective_name
            data = [
                d
                for d in data
                if name_lower in str(d.get("drug_name", "")).lower()
                or name_lower in str(d.get("name", "")).lower()
                or (
                    effective_name != name_lower
                    and (
                        effective_name in str(d.get("drug_name", "")).lower()
                        or effective_name in str(d.get("name", "")).lower()
                    )
                )
            ]

        result_count = len(data)
        out: Dict[str, Any] = {
            "status": "success",
            "data": data,
            "count": result_count,
        }
        if synonym_used:
            out["synonym_expanded"] = (
                f"Searched for '{synonym_used}' (SYNERGxDB stored name for '{name_filter}')."
            )
        # Feature-43A-06: when drug name search returns empty, add a helpful note about
        # database coverage so users understand why their targeted therapy is missing.
        if result_count == 0 and name_filter:
            out["note"] = (
                f"No drug matching '{name_filter}' found in SYNERGxDB. "
                "SYNERGxDB covers cytotoxic chemotherapy combinations from 9 published screening "
                "studies. Targeted therapies (KRAS inhibitors, BRAF/MEK inhibitors), immune "
                "checkpoint antibodies, and most biologics (monoclonal antibodies) are not included."
            )
        return out

    def _get_drug(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get drug details by ID."""
        drug_id = arguments.get("drug_id")
        if not drug_id:
            return {"status": "error", "error": "drug_id is required"}

        result = self._make_request(f"drugs/{drug_id}")
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        data = result["data"]
        # API returns a list with one element
        if isinstance(data, list) and len(data) == 1:
            data = data[0]
        return {
            "status": "success",
            "data": data,
        }

    def _list_cell_lines(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List all cell lines in the SYNERGxDB database."""
        result = self._make_request("cell_lines/")
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        data = result["data"]
        return {
            "status": "success",
            "data": data,
            "count": len(data),
        }

    def _list_datasets(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List all screening datasets in SYNERGxDB."""
        result = self._make_request("datasets/")
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        data = result["data"]
        return {
            "status": "success",
            "data": data,
            "count": len(data),
        }

    def _get_combo_stats(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get per-dataset combination statistics."""
        result = self._make_request("combos/stats")
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        data = result["data"]
        return {
            "status": "success",
            "data": data,
            "count": len(data),
        }
