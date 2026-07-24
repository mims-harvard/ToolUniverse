"""
ISRCTN tools for ToolUniverse — ISRCTN clinical trial registry.

ISRCTN is a WHO-primary clinical-trials registry (UK-based, international scope),
a third trial source alongside ClinicalTrials.gov and the EU CTIS register. The
public query API returns XML; these tools parse it into structured records.

API: https://www.isrctn.com/api/query  (public, no authentication, XML)
"""

import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

ISRCTN_BASE = "https://www.isrctn.com/api/query"
_NS = {"i": "http://www.67bricks.com/isrctn"}


def _text(parent: Optional[ET.Element], path: str) -> Optional[str]:
    if parent is None:
        return None
    el = parent.find(path, _NS)
    return el.text.strip() if el is not None and el.text else None


def _texts(parent: Optional[ET.Element], path: str) -> List[str]:
    """Collect the text of every element matching ``path`` under ``parent``."""
    if parent is None:
        return []
    out = []
    for el in parent.findall(path, _NS):
        if el is not None and el.text and el.text.strip():
            out.append(el.text.strip())
    return out


def _parse_interventions(trial: Optional[ET.Element]) -> List[Dict[str, Any]]:
    container = trial.find("i:interventions", _NS) if trial is not None else None
    if container is None:
        return []
    out = []
    for iv in container.findall("i:intervention", _NS):
        out.append(
            {
                "intervention_type": _text(iv, "i:interventionType"),
                "phase": _text(iv, "i:phase"),
                "drug_names": _text(iv, "i:drugNames"),
                "description": _text(iv, "i:description"),
            }
        )
    return out


def _parse_outcomes(desc: Optional[ET.Element], group: str) -> List[Dict[str, Any]]:
    """Parse primaryOutcomes / secondaryOutcomes into a list of measures.

    These live under ``trial/trialDescription``. Each measure is an
    ``<outcomeMeasure>`` with ``<variable>`` (the measure), ``<method>``, and
    ``<timepoints>`` children.
    """
    container = desc.find(f"i:{group}", _NS) if desc is not None else None
    if container is None:
        return []
    out = []
    for outcome in container.findall("i:outcomeMeasure", _NS):
        measure = _text(outcome, "i:variable")
        method = _text(outcome, "i:method")
        timepoints = _text(outcome, "i:timepoints")
        if measure or method or timepoints:
            out.append(
                {
                    "measure": measure,
                    "method": method,
                    "timepoints": timepoints,
                }
            )
    return out


def _parse_parties(full_trial: ET.Element) -> Dict[str, Any]:
    """Sponsors, funders and contacts live at the <fullTrial> level."""
    sponsors = [
        {
            "organisation": _text(s, "i:organisation"),
            "sponsor_type": _text(s, "i:sponsorType"),
            "commercial_status": _text(s, "i:commercialStatus"),
            "ror_id": _text(s, "i:rorId"),
        }
        for s in full_trial.findall("i:sponsor", _NS)
    ]
    funders = [
        {"name": _text(f, "i:name"), "fund_ref": _text(f, "i:fundRef")}
        for f in full_trial.findall("i:funder", _NS)
    ]
    contacts = []
    for c in full_trial.findall("i:contact", _NS):
        name = " ".join(
            p for p in (_text(c, "i:forename"), _text(c, "i:surname")) if p
        ).strip()
        contacts.append(
            {
                "name": name or None,
                "contact_types": _texts(c, "i:contactTypes/i:contactType"),
            }
        )
    return {"sponsors": sponsors, "funders": funders, "contacts": contacts}


def _parse_trial(full_trial: ET.Element, detailed: bool = False) -> Dict[str, Any]:
    trial = full_trial.find("i:trial", _NS)
    desc = trial.find("i:trialDescription", _NS) if trial is not None else None
    refs = trial.find("i:externalRefs", _NS) if trial is not None else None
    design = trial.find("i:trialDesign", _NS) if trial is not None else None
    isrctn_num = _text(trial, "i:isrctn")
    record: Dict[str, Any] = {
        "isrctn_id": f"ISRCTN{isrctn_num}" if isrctn_num else None,
        "title": _text(desc, "i:title"),
        "scientific_title": _text(desc, "i:scientificTitle"),
        "acronym": _text(desc, "i:acronym"),
        "study_hypothesis": _text(desc, "i:studyHypothesis"),
        "primary_study_design": _text(design, "i:primaryStudyDesign"),
        "overall_end_date": _text(design, "i:overallEndDate"),
        "doi": _text(refs, "i:doi"),
        "eudract_number": _text(refs, "i:eudraCTNumber"),
        "clinicaltrials_gov_number": _text(refs, "i:clinicalTrialsGovNumber"),
    }
    if not detailed:
        return record

    participants = trial.find("i:participants", _NS) if trial is not None else None
    results = trial.find("i:results", _NS) if trial is not None else None
    misc = trial.find("i:miscellaneous", _NS) if trial is not None else None
    # IPD-sharing info lives under trial/miscellaneous/ipdSharingPlan and
    # trial/results/dataPolicies/dataPolicy.
    ipd_statement = _text(misc, "i:ipdSharingPlan") or _text(
        results, "i:dataPolicies/i:dataPolicy"
    )

    interventions = _parse_interventions(trial)
    phase = next((iv["phase"] for iv in interventions if iv.get("phase")), None)
    record.update(
        {
            "plain_english_summary": _text(desc, "i:plainEnglishSummary"),
            "secondary_study_design": _text(design, "i:secondaryStudyDesign"),
            "phase": phase,
            "conditions": _texts(
                trial.find("i:conditions", _NS) if trial is not None else None,
                "i:condition/i:description",
            )
            or _texts(
                trial.find("i:conditions", _NS) if trial is not None else None,
                "i:condition/i:diseaseClass1",
            ),
            "interventions": interventions,
            "drug_names": _texts(
                trial.find("i:interventions", _NS) if trial is not None else None,
                "i:intervention/i:drugNames",
            ),
            "primary_outcomes": _parse_outcomes(desc, "primaryOutcomes"),
            "secondary_outcomes": _parse_outcomes(desc, "secondaryOutcomes"),
            "eligibility": {
                "inclusion": _text(participants, "i:inclusion"),
                "exclusion": _text(participants, "i:exclusion"),
                "gender": _text(participants, "i:gender"),
                "age_range": _text(participants, "i:ageRange"),
                "lower_age_limit": _text(participants, "i:lowerAgeLimit"),
                "upper_age_limit": _text(participants, "i:upperAgeLimit"),
                "healthy_volunteers_allowed": _text(
                    participants, "i:healthyVolunteersAllowed"
                ),
            },
            "recruitment_countries": _texts(
                participants.find("i:recruitmentCountries", _NS)
                if participants is not None
                else None,
                "i:country",
            ),
            "recruitment_start": _text(participants, "i:recruitmentStart"),
            "recruitment_end": _text(participants, "i:recruitmentEnd"),
            "target_enrolment": _text(participants, "i:targetEnrolment"),
            "total_final_enrolment": _text(participants, "i:totalFinalEnrolment"),
            "ipd_sharing_statement": ipd_statement,
        }
    )
    record.update(_parse_parties(full_trial))
    return record


class _ISRCTNBase(BaseTool):
    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)

    def _query(self, params: Dict[str, Any]) -> Any:
        resp = requests.get(
            f"{ISRCTN_BASE}/format/default",
            params=params,
            headers={"Accept": "application/xml"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.text


# ISRCTN query-DSL field helpers -> the field token used in q=field:value.
_ISRCTN_FIELD_HELPERS = {
    "condition": "condition",
    "phase": "phase",
    "gender": "gender",
    "intervention": "intervention",
    "sponsor": "sponsor",
    "funder": "funder",
    "country": "recruitmentCountry",
    "drug_name": "drugName",
}


def _quote_dsl_value(value: str) -> str:
    """Wrap a value in quotes when it contains whitespace, for the ISRCTN DSL."""
    value = value.strip()
    if any(ch.isspace() for ch in value) and not (
        value.startswith('"') and value.endswith('"')
    ):
        return f'"{value}"'
    return value


def _build_fielded_query(arguments: Dict[str, Any]) -> str:
    """Assemble an ISRCTN field-scoped boolean query from helper arguments.

    A raw ``q``/``query`` is used verbatim (so callers can pass a full DSL such
    as ``gender:Female AND condition:asthma``); otherwise field helpers like
    ``condition``/``phase``/``gender`` are joined with AND.
    """
    raw = (arguments.get("q") or arguments.get("query") or "").strip()
    if raw:
        return raw
    clauses = []
    for arg_name, field_token in _ISRCTN_FIELD_HELPERS.items():
        val = arguments.get(arg_name)
        if val is None or (isinstance(val, str) and not val.strip()):
            continue
        clauses.append(f"{field_token}:{_quote_dsl_value(str(val))}")
    return " AND ".join(clauses)


@register_tool("ISRCTNSearchTool")
class ISRCTNSearchTool(_ISRCTNBase):
    """Search the ISRCTN clinical trial registry.

    Behavior is selected by the tool's configured ``name``: the
    ``ISRCTN_search_trials_fielded`` entry forwards a field-scoped boolean
    query DSL (``condition:diabetes``, ``phase:"Phase III"``,
    ``gender:Female AND condition:asthma``) to precisely scope the search,
    while every other entry performs the original free-text search.
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        fielded = (self.tool_config.get("name") or "").strip() == (
            "ISRCTN_search_trials_fielded"
        )
        if fielded:
            query = _build_fielded_query(arguments)
            empty_msg = (
                "Provide a field-scoped query 'q' (e.g. 'condition:diabetes', "
                "'gender:Female AND condition:asthma') or field helpers such as "
                "condition / phase / gender."
            )
        else:
            query = (arguments.get("query") or "").strip()
            empty_msg = "'query' is required (e.g. 'cystic fibrosis')"
        if not query:
            return {"status": "error", "error": empty_msg}

        try:
            size = max(1, min(int(arguments.get("limit") or 10), 100))
        except (TypeError, ValueError):
            size = 10
        try:
            xml = self._query({"q": query, "limit": size})
            root = ET.fromstring(xml)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"ISRCTN request timed out after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"ISRCTN request failed: {e}"}
        except ET.ParseError as e:
            return {"status": "error", "error": f"ISRCTN returned unparseable XML: {e}"}

        trials: List[Dict[str, Any]] = [
            _parse_trial(ft, detailed=fielded)
            for ft in root.findall("i:fullTrial", _NS)
        ]
        return {
            "status": "success",
            "data": trials,
            "metadata": {
                "total_available": root.get("totalCount"),
                "returned": len(trials),
                "query": query,
                "source": "ISRCTN registry",
            },
        }


@register_tool("ISRCTNGetTrialTool")
class ISRCTNGetTrialTool(_ISRCTNBase):
    """Retrieve a single ISRCTN trial by its ISRCTN id."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        trial_id = (arguments.get("isrctn_id") or "").strip()
        if not trial_id:
            return {
                "status": "error",
                "error": "'isrctn_id' is required (e.g. 'ISRCTN12336055')",
            }
        digits = trial_id.upper().replace("ISRCTN", "").strip()

        try:
            xml = self._query({"q": f"ISRCTN{digits}", "limit": 1})
            root = ET.fromstring(xml)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"ISRCTN request timed out after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"ISRCTN request failed: {e}"}
        except ET.ParseError as e:
            return {"status": "error", "error": f"ISRCTN returned unparseable XML: {e}"}

        first = root.find("i:fullTrial", _NS)
        if first is None:
            return {
                "status": "success",
                "data": {},
                "metadata": {
                    "query_isrctn_id": f"ISRCTN{digits}",
                    "note": "No ISRCTN trial found for that id.",
                },
            }
        return {
            "status": "success",
            "data": _parse_trial(first, detailed=True),
            "metadata": {
                "query_isrctn_id": f"ISRCTN{digits}",
                "source": "ISRCTN registry",
            },
        }
