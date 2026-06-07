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


def _parse_trial(full_trial: ET.Element) -> Dict[str, Any]:
    trial = full_trial.find("i:trial", _NS)
    desc = trial.find("i:trialDescription", _NS) if trial is not None else None
    refs = trial.find("i:externalRefs", _NS) if trial is not None else None
    design = trial.find("i:trialDesign", _NS) if trial is not None else None
    isrctn_num = _text(trial, "i:isrctn")
    return {
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


@register_tool("ISRCTNSearchTool")
class ISRCTNSearchTool(_ISRCTNBase):
    """Search the ISRCTN clinical trial registry by free text."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = (arguments.get("query") or "").strip()
        if not query:
            return {
                "status": "error",
                "error": "'query' is required (e.g. 'cystic fibrosis')",
            }
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
            _parse_trial(ft) for ft in root.findall("i:fullTrial", _NS)
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
            "data": _parse_trial(first),
            "metadata": {
                "query_isrctn_id": f"ISRCTN{digits}",
                "source": "ISRCTN registry",
            },
        }
