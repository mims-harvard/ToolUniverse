# fda_label_tool.py
"""
FDA Drug Label tool for ToolUniverse.

Queries the openFDA drug label API to retrieve official FDA-approved
prescribing information including indications, dosing, contraindications,
warnings, drug interactions, and pharmacology.

API: https://open.fda.gov/apis/drug/label/
No authentication required. Set the FDA_API_KEY env var to raise the
default ~40 req/min anonymous rate limit (https://open.fda.gov/apis/authentication/).
"""

import os
import re
import requests
from typing import Any

from .base_tool import BaseTool
from .tool_registry import register_tool

FDA_LABEL_URL = "https://api.fda.gov/drug/label.json"

# Evidence for the vaccine sentence below, measured on the live API: both
# `openfda.generic_name.exact:*VACCINE*` and `openfda.generic_name:vaccine`
# return nothing, and YF-VAX, TYPHIM VI, FLUZONE, SHINGRIX and GARDASIL are all
# absent as brand names.
_NO_MATCH_SUGGESTION = (
    "Nothing matched this as a brand or generic name. Check the spelling, try "
    "the generic name instead of the brand (or vice versa), or drop dosage form "
    "and strength qualifiers. Note that vaccines and most other biologics are "
    "licensed under a BLA and are not published on the openFDA drug label "
    "endpoint at all."
)

# Placeholder values users sometimes leave in FDA_API_KEY; treat as "unset".
_API_KEY_PLACEHOLDERS = {"none", "null", "your_fda_key_here", "your_key_here"}

# Per-section character budget, by query_type.
#
# openFDA label sections are unbounded prose. Measured against the live API:
# a complete Prograf (tacrolimus) label is ~103,000 characters of section text,
# Humira ~86,000 and a warfarin label ~47,000; the single largest section seen
# was 28,292 characters (Prograf adverse_reactions).
#
# A section longer than the applied budget is cut, and every cut is disclosed
# at the top level of the response via `truncated` / `truncation_note`; callers
# override the budget with the `max_section_chars` argument (0 = no limit).
DEFAULT_SECTION_CHARS = {
    # FDA_get_drug_label advertises the *complete* prescribing information for
    # one drug, so its budget has to hold a whole clinical section. 25,000
    # characters keeps every section of the labels measured above intact except
    # Prograf's outsized adverse_reactions, and bounds one label at a few
    # hundred KB instead of being unbounded.
    "get": 25000,
    # FDA_search_drug_labels returns up to 20 records at once, so it stays a
    # deliberately compact summary view -- it just says so now instead of
    # presenting cut prose as complete.
    "search": 2000,
}
_FALLBACK_SECTION_CHARS = 2000

# Extracted record keys that hold free-text clinical prose and are therefore
# subject to the per-section budget. Identifier/metadata keys are not.
_SECTION_FIELDS = (
    "boxed_warning",
    "indications_and_usage",
    "dosage_and_administration",
    "dosage_forms_and_strengths",
    "contraindications",
    "warnings_and_precautions",
    "adverse_reactions",
    "drug_interactions",
    "use_in_specific_populations",
    "clinical_pharmacology",
    "mechanism_of_action",
)


def _phrase(field: str, text: str) -> str:
    """Bind `text` to `field` as a single quoted phrase.

    The escaping is the point: an unescaped quote in `text` closes the phrase
    early and turns the remainder into free-text terms OR-ed across the whole
    document. Measured on the live API, `indications_and_usage:"pain"` matches
    24,135 labels while `indications_and_usage:"pain" OR "x"` matches 57,661.
    Every query built from caller-supplied text goes through here.
    """
    escaped = text.strip().replace("\\", "\\\\").replace('"', '\\"')
    return f'{field}:"{escaped}"'


def _name_queries(field: str, drug_name: str) -> list[str]:
    """Build openFDA queries for `drug_name`, most precise first.

    Every term stays bound to `field`, which is what keeps a miss a miss.
    openFDA speaks Elasticsearch query_string syntax, where a bare field prefix
    binds to the FIRST token only: `openfda.generic_name:yellow fever vaccine`
    searches generic_name for "yellow", then searches the WHOLE document for
    "fever" and "vaccine" and OR-s the three together. Measured on the live API
    that matches 87,153 of the 261,639 labels in the corpus -- a third of it --
    and its top hit is naproxen, so an unbound query cannot be used to look up
    a drug by name.

    Two bound forms are tried:

    1. Exact phrase. Because openFDA analyses these name fields, a phrase also
       covers salt forms -- "tofacitinib" matches "TOFACITINIB CITRATE" (29
       labels, identical to the unquoted form) and "mefloquine" matches
       "MEFLOQUINE HYDROCHLORIDE".
    2. Every token AND-ed, each still bound to `field`. This recovers names
       written with different connectors or token order -- "amoxicillin
       clavulanate" finds the 166 "AMOXICILLIN AND CLAVULANATE POTASSIUM"
       labels that the phrase form misses -- while still guaranteeing that a
       hit contains all the search terms in the name field it matched. It is
       skipped for a single token, where it is identical to the phrase query.
    """
    queries = [_phrase(field, drug_name)]
    # Tokens come out of an alphanumeric-only split, so they need no escaping.
    tokens = [t for t in re.split(r"[^0-9A-Za-z]+", drug_name) if t]
    if len(tokens) > 1:
        anded = " AND ".join(f'"{t}"' for t in tokens)
        queries.append(f"{field}:({anded})")
    return queries


def _valid_api_key(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    v = value.strip()
    return bool(v) and v.lower() not in _API_KEY_PLACEHOLDERS


def _ok(data: Any, **metadata: Any) -> dict:
    """Wrap a successful result in the standard ToolUniverse envelope.

    Error paths already return {status: error, ...}; this keeps the success
    path consistent with the project-wide {status, data, metadata} contract.
    """
    metadata.setdefault("source", "openFDA drug label")
    if isinstance(data, list):
        metadata.setdefault("count", len(data))
    return {"status": "success", "data": data, "metadata": metadata}


def _disclose_truncation(
    response: dict, truncated_fields: list[str], max_chars: int | None
) -> dict:
    """Attach the top-level truncation disclosure to a success envelope.

    `truncated` is always present (False when nothing was cut) so callers can
    rely on the key existing; `truncated_fields` and `truncation_note` appear
    only when something really was cut. The note names the affected sections,
    the budget that was applied, and the argument to raise it -- a flag that
    says "there is more" without saying how to get it is only half a disclosure.
    """
    fields = sorted(set(truncated_fields))
    response["truncated"] = bool(fields)
    if fields:
        response["truncated_fields"] = fields
        response["truncation_note"] = (
            f"{len(fields)} label section(s) exceeded max_section_chars="
            f"{max_chars} and were cut mid-text: {', '.join(fields)}. "
            "Pass a larger max_section_chars (or max_section_chars=0 for no "
            "limit) to retrieve these sections in full."
        )
    return response


def _apply_section_limit(record: dict, max_chars: int | None) -> tuple[dict, list[str]]:
    """Cut every clinical section of an extracted record down to `max_chars`.

    Returns the limited record plus the names of the sections that were cut, so
    the caller can disclose them. `max_chars=None` means no limit.
    """
    if max_chars is None:
        return record, []
    truncated_fields: list[str] = []
    limited = dict(record)
    for key in _SECTION_FIELDS:
        text = record.get(key)
        if isinstance(text, str) and len(text) > max_chars:
            limited[key] = text[:max_chars]
            truncated_fields.append(key)
    return limited, truncated_fields


def _extract_label(
    result: dict, max_chars: int | None = None
) -> tuple[dict, list[str]]:
    """Extract key clinical sections from a raw openFDA label record.

    Returns the extracted record plus the names of the sections that had to be
    cut to fit `max_chars` (empty when `max_chars` is None, meaning no limit).
    """
    openfda = result.get("openfda", {})
    brand = openfda.get("brand_name", [])
    generic = openfda.get("generic_name", [])
    mfr = openfda.get("manufacturer_name", [])
    route = openfda.get("route", [])
    pharm = openfda.get("pharm_class_epc", [])
    rxcui = openfda.get("rxcui", [])

    def first(lst, sep=" / "):
        return sep.join(lst[:2]) if lst else None

    def section(key):
        val = result.get(key, [])
        return " ".join(val) if val else None

    record = {
        "brand_name": first(brand),
        "generic_name": first(generic),
        "manufacturer": first(mfr),
        "route": first(route),
        "pharm_class": first(pharm),
        "rxcui": rxcui[:5] if rxcui else None,
        "boxed_warning": section("boxed_warning"),
        "indications_and_usage": section("indications_and_usage"),
        "dosage_and_administration": section("dosage_and_administration"),
        "dosage_forms_and_strengths": section("dosage_forms_and_strengths"),
        "contraindications": section("contraindications"),
        "warnings_and_precautions": section("warnings_and_precautions")
        or section("warnings_and_cautions"),
        "adverse_reactions": section("adverse_reactions"),
        "drug_interactions": section("drug_interactions"),
        "use_in_specific_populations": section("use_in_specific_populations"),
        "clinical_pharmacology": section("clinical_pharmacology"),
        "mechanism_of_action": section("mechanism_of_action"),
        "spl_id": result.get("id"),
    }
    return _apply_section_limit(record, max_chars)


@register_tool("FDALabelTool")
class FDALabelTool(BaseTool):
    """
    Tool for querying FDA-approved drug label (prescribing information).

    Supports searching by drug name, indication, or listing drug classes.
    Returns official FDA clinical content: indications, dosing,
    contraindications, warnings, drug interactions, and adverse reactions.
    """

    def __init__(self, tool_config: dict[str, Any]):
        super().__init__(tool_config)
        self.query_type = tool_config.get("fields", {}).get("query_type", "search")
        self.api_key = os.getenv("FDA_API_KEY")

    def _params(self, **kwargs: Any) -> dict:
        """Build request params, adding api_key when a valid FDA_API_KEY is set.

        openFDA's anonymous tier is heavily rate-limited (~40 req/min); an
        API key raises that substantially. See https://open.fda.gov/apis/authentication/
        """
        if _valid_api_key(self.api_key):
            kwargs["api_key"] = self.api_key
        return kwargs

    def _max_section_chars(self, arguments: dict) -> int | None:
        """Resolve the per-section character budget for this call.

        Returns None when the caller asked for no limit (max_section_chars <= 0).
        """
        default = DEFAULT_SECTION_CHARS.get(self.query_type, _FALLBACK_SECTION_CHARS)
        raw = arguments.get("max_section_chars")
        if raw is None:
            return default
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return default
        return value if value > 0 else None

    def run(self, arguments: dict[str, Any]) -> Any:
        try:
            qt = self.query_type
            if qt == "search":
                return self._search(arguments)
            elif qt == "get":
                return self._get_label(arguments)
            elif qt == "list_classes":
                return self._list_classes(arguments)
            return {"status": "error", "error": f"Unknown query_type: {qt}"}
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "openFDA request timed out"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"openFDA request failed: {e}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {e}"}

    def _query_drug_fields(
        self, drug_name: str, limit: int, max_chars: int | None = None
    ) -> tuple[list[dict] | None, list[str]]:
        """Search generic_name then brand_name, exact phrase then all-tokens.

        Returns (extracted label results, truncated section names) on the first
        match, or (None, []) if no results found. See `_name_queries` for the
        query forms and why every term has to stay bound to the name field.
        """
        for field in ("openfda.generic_name", "openfda.brand_name"):
            for q in _name_queries(field, drug_name):
                resp = requests.get(
                    FDA_LABEL_URL,
                    params=self._params(search=q, limit=limit),
                    timeout=20,
                )
                if resp.status_code == 404:
                    continue
                resp.raise_for_status()
                results = resp.json().get("results", [])
                if results:
                    labels: list[dict] = []
                    truncated: list[str] = []
                    for r in results:
                        record, cut = _extract_label(r, max_chars)
                        labels.append(record)
                        truncated.extend(cut)
                    return labels, truncated
        return None, []

    def _search(self, arguments: dict) -> Any:
        drug_name = arguments.get("drug_name")
        indication = arguments.get("indication")
        limit = min(int(arguments.get("limit", 5)), 20)
        max_chars = self._max_section_chars(arguments)

        if not drug_name and not indication:
            return {"status": "error", "error": "Provide drug_name or indication"}

        if drug_name:
            labels, truncated = self._query_drug_fields(drug_name, limit, max_chars)
            response = _disclose_truncation(
                _ok(
                    labels or [],
                    query=drug_name,
                    query_field="drug_name",
                    max_section_chars=max_chars or 0,
                ),
                truncated,
                max_chars,
            )
            if not labels:
                response["suggestion"] = _NO_MATCH_SUGGESTION
            return response

        q = _phrase("indications_and_usage", indication)
        resp = requests.get(
            FDA_LABEL_URL,
            params=self._params(search=q, limit=limit),
            timeout=20,
        )
        labels = []
        truncated = []
        if resp.status_code != 404:
            resp.raise_for_status()
            for r in resp.json().get("results", []):
                record, cut = _extract_label(r, max_chars)
                labels.append(record)
                truncated.extend(cut)
        return _disclose_truncation(
            _ok(
                labels,
                query=indication,
                query_field="indication",
                max_section_chars=max_chars or 0,
            ),
            truncated,
            max_chars,
        )

    def _get_label(self, arguments: dict) -> Any:
        drug_name = arguments.get("drug_name", "")
        if not drug_name:
            return {"status": "error", "error": "drug_name is required"}

        max_chars = self._max_section_chars(arguments)

        # Fetch candidates untruncated so the best-match choice below is made on
        # complete records, and only the record we actually return gets cut --
        # otherwise the disclosure would name sections from discarded matches.
        results, _ = self._query_drug_fields(drug_name, limit=10, max_chars=None)
        if not results:
            return {
                "status": "error",
                "error": f"No FDA label found for '{drug_name}'",
                "suggestion": _NO_MATCH_SUGGESTION,
            }

        dn_upper = drug_name.upper()

        def _match_score(r):
            brand = (r.get("brand_name") or "").upper()
            generic = (r.get("generic_name") or "").upper()
            if brand == dn_upper or generic == dn_upper:
                return 0
            return len(brand) or 999

        results.sort(key=_match_score)
        label, truncated = _apply_section_limit(results[0], max_chars)
        return _disclose_truncation(
            _ok(label, query=drug_name, max_section_chars=max_chars or 0),
            truncated,
            max_chars,
        )

    def _list_classes(self, arguments: dict) -> Any:
        limit = min(int(arguments.get("limit", 20)), 100)
        resp = requests.get(
            FDA_LABEL_URL,
            params=self._params(
                count="openfda.pharm_class_epc.exact",
                limit=limit,
            ),
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        classes = [{"drug_class": r["term"], "count": r["count"]} for r in results]
        return _ok(classes)
