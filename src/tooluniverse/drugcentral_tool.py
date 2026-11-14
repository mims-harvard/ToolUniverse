# drugcentral_tool.py
"""
DrugCentral data access tool for ToolUniverse.

DrugCentral (University of New Mexico) provides open-access drug information
including targets, indications, contraindications, and regulatory approvals.
DrugCentral's own REST API is down (confirmed Feb 2026), but its data is
available through MyChem.info (BioThings) which aggregates DrugCentral data.

This tool queries MyChem.info and extracts DrugCentral-specific fields:
- bioactivity: drug targets with UniProt IDs, activity types, and values
- drug_use: indications, contraindications, and off-label uses (SNOMED/UMLS)
- approval: FDA/EMA/PMDA approval dates and sponsors
- structures: InChIKey, SMILES, CAS RN, INN name
- xrefs: cross-references to ChEMBL, DrugBank, KEGG, PubChem, RxNorm, etc.

No authentication required.
"""

import math
import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

MYCHEM_BASE = "https://mychem.info/v1"

# DrugCentral stores bioactivity potency in "act_value" on the p-scale --
# -log10 of the molar potency (the pChEMBL convention) -- NOT as a
# concentration in nM or uM. Reporting that number next to an "IC50" label
# with no units reads as "IC50 = 4.01 (nM?)" when the underlying IC50 is
# 10^-4.01 M = ~96.8 uM, i.e. a ~5-order-of-magnitude misstatement
# (verified against ChEMBL: praziquantel/ABCB11 IC50 96800 nM, pchembl 4.01).
# These constants/helpers let the tool disclose the scale explicitly without
# changing the value it has always returned.
P_ACTIVITY_SCALE = (
    "pActivity: -log10 of the molar potency, not a concentration. "
    "Higher = more potent. Convert with nM = 10**(9 - value); "
    "e.g. 4.01 -> ~96800 nM (96.8 uM), 9.0 -> 1 nM."
)


def _p_activity_to_nanomolar(act_value: Any, sig_figs: int = 4) -> "float | None":
    """Convert a -log10(molar) p-scale potency to nanomolar.

    Returns None when ``act_value`` is missing or does not parse as a finite
    float, so callers never see a fabricated concentration.
    """
    try:
        p_value = float(act_value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(p_value):
        return None
    try:
        nanomolar = 10.0 ** (9.0 - p_value)
    except OverflowError:
        return None
    if not math.isfinite(nanomolar) or nanomolar <= 0:
        return None
    # The p-value upstream carries ~2 decimals, so anything past a few
    # significant figures in the converted concentration is false precision.
    decimals = -math.floor(math.log10(nanomolar)) + (sig_figs - 1)
    return round(nanomolar, decimals)


def _p_activity_type(act_type: Any) -> "str | None":
    """Name the quantity actually reported, e.g. "IC50" -> "pIC50"."""
    if not isinstance(act_type, str) or not act_type.strip():
        return None
    act_type = act_type.strip()
    # Guard against upstream ever switching to already-p-prefixed labels.
    if act_type[0] in "pP" and act_type[1:2].isupper():
        return act_type
    return f"p{act_type}"

# DrugCentral ships a FAERS disproportionality row per MedDRA term -- 1,534 for
# metformin -- so they are ranked by log-likelihood ratio and capped, with the
# count and the cut disclosed. The rows are a signal measure, not a causal one.
SIGNALS_PER_DRUG = 50


def _signal_rows(records: Any) -> "tuple[list, int]":
    """FAERS disproportionality rows, strongest signal first.

    `llr` is the log-likelihood ratio and `llr_threshold` the value above which
    DrugCentral calls the pair a signal, so returning the one without the other
    says nothing. Both are strings upstream; the float is only for ordering.
    """
    if not isinstance(records, list):
        records = [records] if records else []
    rows = []
    for rec in records:
        if not isinstance(rec, dict):
            continue
        try:
            llr = float(rec.get("llr"))
        except (TypeError, ValueError):
            llr = None
        try:
            threshold = float(rec.get("llr_threshold"))
        except (TypeError, ValueError):
            threshold = None
        rows.append(
            {
                "meddra_term": rec.get("meddra_term"),
                "meddra_code": rec.get("meddra_code"),
                "meddra_level": rec.get("level"),
                "llr": rec.get("llr"),
                "llr_threshold": rec.get("llr_threshold"),
                "is_signal": (
                    None if llr is None or threshold is None else llr > threshold
                ),
                "reports_with_drug_and_event": rec.get("drug_ae"),
                "reports_with_drug_without_event": rec.get("drug_no_ae"),
                "reports_without_drug_with_event": rec.get("no_drug_ae"),
                "reports_without_drug_without_event": rec.get("no_drug_no_ar"),
                "_llr": llr,
            }
        )
    rows.sort(key=lambda row: (row["_llr"] is None, -(row["_llr"] or 0.0)))
    for row in rows:
        row.pop("_llr", None)
    return rows[:SIGNALS_PER_DRUG], len(rows)


def _pharmacologic_classes(node: Any) -> list:
    """The drug's classes, flattened across the systems that assign them.

    DrugCentral keys them by system -- `fda_epc` (FDA Established
    Pharmacologic Class), `mesh_pa` (MeSH pharmacologic action), `chebi`
    (ChEBI role) -- and a system holds either one class or a list.
    """
    if not isinstance(node, dict):
        return []
    out = []
    for system, value in node.items():
        entries = value if isinstance(value, list) else [value]
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            out.append(
                {
                    "system": system,
                    "code": entry.get("code"),
                    "name": entry.get("description"),
                }
            )
    return out


def _dosages(node: Any) -> list:
    """Approved dose, unit and route, as DrugCentral lists them."""
    entries = node if isinstance(node, list) else ([node] if node else [])
    return [
        {
            "dosage": entry.get("dosage"),
            "unit": entry.get("unit"),
            "route": entry.get("route"),
        }
        for entry in entries
        if isinstance(entry, dict)
    ]


# Fields to retrieve from MyChem for DrugCentral data
DC_ALL_FIELDS = "drugcentral"
DC_TARGET_FIELDS = "drugcentral.bioactivity"
DC_USE_FIELDS = (
    "drugcentral.drug_use,drugcentral.approval,drugcentral.structures,drugcentral.xrefs"
)


@register_tool("DrugCentralTool")
class DrugCentralTool(BaseTool):
    """
    Tool for accessing DrugCentral data via MyChem.info.

    Provides drug target information, indications, contraindications,
    off-label uses, regulatory approvals, and cross-references from
    DrugCentral's curated database.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get("operation", "search")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the DrugCentral data query."""
        try:
            if self.operation == "search":
                return self._search_drugs(arguments)
            elif self.operation == "get_drug":
                return self._get_drug(arguments)
            elif self.operation == "get_targets":
                return self._get_targets(arguments)
            else:
                return {
                    "status": "error",
                    "error": f"Unknown operation: {self.operation}",
                }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"MyChem.info request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to MyChem.info API"}
        except Exception as e:
            return {
                "status": "error",
                "error": f"Error querying DrugCentral data: {str(e)}",
            }

    def _search_drugs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for drugs with DrugCentral data via MyChem.info."""
        query = arguments.get("query", "") or arguments.get("q", "")
        if not query:
            return {
                "status": "error",
                "error": "query parameter is required (e.g., 'metformin', 'aspirin')",
            }

        size = min(int(arguments.get("size", 10)), 50)

        # Search MyChem specifically in drugcentral fields to avoid NDC noise.
        # Try drugcentral.structures.inn first (exact drug name match), then
        # fall back to a broader drugcentral-scoped search.
        dc_fields = (
            "drugcentral.structures.inn,drugcentral.structures.cas_rn,"
            "drugcentral.structures.smiles,drugcentral.structures.inchikey,"
            "drugcentral.approval,drugcentral.xrefs"
        )
        params = {
            "q": f"drugcentral.structures.inn:{query}",
            "fields": dc_fields,
            "size": size,
        }
        response = requests.get(
            f"{MYCHEM_BASE}/query", params=params, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        # If no results from INN search, try broader drugcentral scope
        if not data.get("hits"):
            params["q"] = (
                f"drugcentral.xrefs.drugbank_id:{query} OR drugcentral.structures.cas_rn:{query}"
            )
            response = requests.get(
                f"{MYCHEM_BASE}/query", params=params, timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

        # Last resort: general text search filtered to entries with drugcentral data
        if not data.get("hits"):
            params["q"] = f"{query} AND _exists_:drugcentral"
            response = requests.get(
                f"{MYCHEM_BASE}/query", params=params, timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

        hits = data.get("hits", [])
        results = []
        seen_ids = set()
        for hit in hits:
            dc = hit.get("drugcentral", {})
            if not dc:
                continue
            structures = dc.get("structures", {})
            # Biologics (e.g. monoclonal antibodies like pembrolizumab) have
            # no small-molecule structure and legitimately no InChIKey
            # upstream -- falling back to MyChem's internal "_id" here
            # silently mislabeled that unrelated identifier as "inchikey"
            # (confirmed live: e.g. "DPT0O3T46P", not a valid InChIKey).
            # Dedup on "_id" (always present, always unique per hit)
            # instead, and only ever report a real InChIKey or None.
            hit_id = hit.get("_id", "")
            if hit_id in seen_ids:
                continue
            seen_ids.add(hit_id)
            xrefs = dc.get("xrefs", {})
            results.append(
                {
                    "inchikey": structures.get("inchikey"),
                    "name": structures.get("inn"),
                    "cas_rn": structures.get("cas_rn"),
                    "smiles": structures.get("smiles"),
                    "approval": dc.get("approval"),
                    "drugbank_id": xrefs.get("drugbank_id"),
                    "chembl_id": xrefs.get("chembl_id"),
                    "pubchem_cid": xrefs.get("pubchem_cid"),
                    "cross_references": xrefs,
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "total_hits": data.get("total", 0),
                "returned": len(results),
                "query": query,
                "source": "DrugCentral via MyChem.info",
            },
        }

    def _resolve_name_to_id(self, name: str) -> str:
        """Resolve drug name to MyChem.info ID via search."""
        resp = requests.get(
            f"{MYCHEM_BASE}/query",
            params={
                "q": f'drugcentral.structures.inn:"{name}"',
                "fields": "_id",
                "size": 1,
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
        return hits[0]["_id"] if hits else ""

    def _get_drug(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed DrugCentral data for a drug by InChIKey, ChEMBL ID, or drug name."""
        chem_id = (
            arguments.get("chem_id", "")
            or arguments.get("inchikey", "")
            or arguments.get("drug_name", "")
        )
        if not chem_id:
            return {
                "status": "error",
                "error": "chem_id parameter is required (InChIKey, ChEMBL ID, or drug name).",
            }
        # If it looks like a drug name (no special chars), resolve to ID first
        if chem_id.isalpha() or " " in chem_id:
            resolved = self._resolve_name_to_id(chem_id)
            if resolved:
                chem_id = resolved
            # else try as-is

        params = {"fields": DC_ALL_FIELDS}
        response = requests.get(
            f"{MYCHEM_BASE}/chem/{chem_id}", params=params, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        dc = data.get("drugcentral", {})
        if not dc:
            return {
                "status": "error",
                "error": f"No DrugCentral data found for '{chem_id}'. Try using InChIKey format.",
            }

        structures = dc.get("structures", {})
        signals, signal_count = _signal_rows(dc.get("fda_adverse_event"))
        drug_use = dc.get("drug_use", {})
        indications = (
            drug_use.get("indication", []) if isinstance(drug_use, dict) else []
        )
        contras = (
            drug_use.get("contraindication", []) if isinstance(drug_use, dict) else []
        )
        off_label = (
            drug_use.get("off_label_use", []) if isinstance(drug_use, dict) else []
        )

        return {
            "status": "success",
            "data": {
                # MyChem's internal "_id" is not an InChIKey (confirmed live)
                # -- biologics with no small-molecule structure legitimately
                # have no InChIKey upstream; report that as None rather than
                # mislabeling _id as one.
                "inchikey": structures.get("inchikey"),
                "name": structures.get("inn"),
                "cas_rn": structures.get("cas_rn"),
                "smiles": structures.get("smiles"),
                "approval": dc.get("approval", []),
                "indications": [
                    {
                        "name": i.get("concept_name"),
                        "snomed_id": i.get("snomed_concept_id"),
                        "umls_cui": i.get("umls_cui"),
                    }
                    for i in (
                        indications if isinstance(indications, list) else [indications]
                    )
                ],
                "contraindications": [
                    {
                        "name": c.get("concept_name"),
                        "snomed_id": c.get("snomed_concept_id"),
                        "umls_cui": c.get("umls_cui"),
                    }
                    for c in (contras if isinstance(contras, list) else [contras])
                ],
                "off_label_uses": [
                    {
                        "name": o.get("concept_name"),
                        "snomed_id": o.get("snomed_concept_id"),
                        "umls_cui": o.get("umls_cui"),
                    }
                    for o in (off_label if isinstance(off_label, list) else [off_label])
                ],
                "cross_references": dc.get("xrefs", {}),
                "drugcentral_id": dc.get("id"),
                "synonyms": (
                    dc.get("synonyms")
                    if isinstance(dc.get("synonyms"), list)
                    else ([dc["synonyms"]] if dc.get("synonyms") else [])
                ),
                "pharmacologic_classes": _pharmacologic_classes(
                    dc.get("pharmacology_class")
                ),
                "dosages": _dosages(dc.get("drug_dosage")),
                "adverse_event_signals": signals,
                "adverse_event_signal_count": signal_count,
                "adverse_event_signals_truncated": signal_count > len(signals),
                "license": dc.get("_license"),
            },
            "metadata": {
                "query_id": chem_id,
                "source": "DrugCentral via MyChem.info",
                "signals_per_drug": SIGNALS_PER_DRUG,
                "adverse_event_signal_scale": (
                    "FAERS disproportionality: llr is a log-likelihood ratio and "
                    "is_signal reports llr > llr_threshold. A signal is a reporting "
                    "association, not evidence of causation."
                ),
            },
        }

    def _get_targets(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get drug targets from DrugCentral bioactivity data."""
        chem_id = (
            arguments.get("chem_id", "")
            or arguments.get("inchikey", "")
            or arguments.get("drug_name", "")
        )
        if chem_id and (chem_id.isalpha() or " " in chem_id):
            resolved = self._resolve_name_to_id(chem_id)
            if resolved:
                chem_id = resolved
        if not chem_id:
            return {
                "status": "error",
                "error": "chem_id parameter is required. Use InChIKey (e.g., 'XZWYZXLIPXDOLR-UHFFFAOYSA-N' for metformin) "
                "or ChEMBL ID (e.g., 'CHEMBL1431').",
            }

        params = {"fields": "drugcentral.bioactivity,drugcentral.structures.inn"}
        response = requests.get(
            f"{MYCHEM_BASE}/chem/{chem_id}", params=params, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        dc = data.get("drugcentral", {})
        if not dc:
            return {
                "status": "error",
                "error": f"No DrugCentral data found for '{chem_id}'. Try using InChIKey format.",
            }

        bioactivity = dc.get("bioactivity", [])
        if not isinstance(bioactivity, list):
            bioactivity = [bioactivity]

        drug_name = dc.get("structures", {}).get("inn")
        targets = []
        for ba in bioactivity:
            uniprot_info = ba.get("uniprot", [])
            if not isinstance(uniprot_info, list):
                uniprot_info = [uniprot_info]
            uniprot_ids = [
                u.get("uniprot_id") for u in uniprot_info if u.get("uniprot_id")
            ]
            gene_symbols = [
                u.get("gene_symbol") for u in uniprot_info if u.get("gene_symbol")
            ]
            swissprot_entries = [
                u.get("swissprot_entry")
                for u in uniprot_info
                if u.get("swissprot_entry")
            ]
            act_type = ba.get("act_type")
            act_value = ba.get("act_value")
            targets.append(
                {
                    "target_name": ba.get("target_name"),
                    "target_class": ba.get("target_class"),
                    "organism": ba.get("organism"),
                    "action_type": ba.get("action_type"),
                    # "activity_type"/"activity_value" are kept exactly as
                    # upstream reports them for backward compatibility; the
                    # three keys below disclose that the value is on the
                    # p-scale (-log10 M) rather than a nM/uM concentration.
                    "activity_type": act_type,
                    "activity_value": act_value,
                    "activity_type_reported": _p_activity_type(act_type),
                    "activity_value_scale": P_ACTIVITY_SCALE,
                    "activity_value_nM": _p_activity_to_nanomolar(act_value),
                    "is_moa": ba.get("moa") == "1",
                    "source": ba.get("act_source"),
                    "uniprot_ids": uniprot_ids,
                    "gene_symbols": gene_symbols,
                    "swissprot_entries": swissprot_entries,
                }
            )

        return {
            "status": "success",
            "data": {
                "drug_name": drug_name,
                "targets": targets,
            },
            "metadata": {
                "total_targets": len(targets),
                "query_id": chem_id,
                "source": "DrugCentral via MyChem.info",
            },
        }
