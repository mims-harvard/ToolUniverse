# nci_evs_tool.py
"""
NCI EVS (Enterprise Vocabulary Services) terminology tool for ToolUniverse.

The same public API that backs the existing NCIThesaurusTool hosts over a
dozen other clinical and biomedical terminologies: CTCAE (adverse event
grading, the clinical-trial safety standard), ICD-10-CM/ICD-9-CM (US
diagnosis coding), RadLex (radiology), NDF-RT/MedRT (drug reference
terminology), CanMED, plus GO/ChEBI/HGNC/SNOMED CT/LOINC. None of the
non-NCIt terminologies were reachable anywhere in ToolUniverse before
this, and CTCAE/ICD-10-CM/ICD-9-CM/RadLex/NDF-RT/MedRT specifically have
no dedicated tool at all. Built as a sibling to NCIThesaurusTool rather
than modifying it, since that tool's contract is deliberately NCIt-only.

MedDRA is also listed in this API's terminology metadata but returns
HTTP 403 on every query (it is a separately licensed vocabulary); this
tool does not expose it. GO, ChEBI, HGNC, and SNOMED CT already have
dedicated ToolUniverse tools that may return richer data than this
generic interface; prefer those for those four vocabularies.

API: https://api-evsrest.nci.nih.gov/api/v1
No authentication required for the terminologies this tool exposes.
"""

from typing import Any, Dict, List

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

EVS_BASE_URL = "https://api-evsrest.nci.nih.gov/api/v1"

# MedDRA ("mdr") is listed in this API's own terminology metadata but
# returns HTTP 403 on every query -- a separately licensed vocabulary.
_BLOCKED_TERMINOLOGIES = {"mdr", "meddra"}


@register_tool("NCIEVSTool")
class NCIEVSTool(BaseTool):
    """
    Tool for searching NCI EVS clinical and biomedical terminologies other
    than NCIt (use NCIThesaurusTool for NCIt specifically).

    Supports CTCAE (adverse event grading), ICD-10-CM, ICD-9-CM, ICD-10,
    RadLex, NDF-RT, MedRT, CanMED, and more, via keyword search and
    direct code lookup.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "search_terminology"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the NCI EVS lookup."""
        try:
            if self.operation == "search_terminology":
                return self._search_terminology(arguments)
            if self.operation == "get_concept":
                return self._get_concept(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"NCI EVS request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to NCI EVS. Check network.",
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            if code == 403:
                return {
                    "status": "error",
                    "error": "NCI EVS returned HTTP 403: this terminology is "
                    "licensed and not openly queryable (e.g. MedDRA).",
                }
            return {"status": "error", "error": f"NCI EVS returned HTTP {code}"}
        except ValueError:
            return {"status": "error", "error": "NCI EVS returned a non-JSON response"}
        except Exception as e:
            return {"status": "error", "error": f"Error querying NCI EVS: {str(e)}"}

    @staticmethod
    def _check_terminology(terminology: str) -> Dict[str, Any]:
        if not terminology:
            return {
                "status": "error",
                "error": "terminology is required, e.g. 'ctcae5' (adverse "
                "events), 'icd10cm' (US diagnosis codes), 'radlex' "
                "(radiology).",
            }
        if terminology.lower() in _BLOCKED_TERMINOLOGIES:
            return {
                "status": "error",
                "error": "MedDRA is a separately licensed vocabulary; NCI "
                "EVS returns HTTP 403 for it. CTCAE concepts include a "
                "MedDRA_Code property as a free cross-reference instead.",
            }
        return {}

    def _search_terminology(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Keyword-search one NCI EVS terminology."""
        terminology = (arguments.get("terminology") or "").strip().lower()
        check = self._check_terminology(terminology)
        if check:
            return check

        term = (arguments.get("term") or "").strip()
        if not term:
            return {
                "status": "error",
                "error": "term is required, e.g. 'neutropenia' or 'diabetes'.",
            }

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 20
        limit = min(limit, 100)

        response = requests.get(
            f"{EVS_BASE_URL}/concept/{terminology}/search",
            params={"term": term, "type": "contains", "pageSize": limit},
            timeout=self.timeout,
        )
        if response.status_code == 404:
            return {
                "status": "error",
                "error": f"Unknown NCI EVS terminology '{terminology}'.",
            }
        response.raise_for_status()
        payload = response.json()
        concepts = payload.get("concepts") or []

        if not concepts:
            return {
                "status": "error",
                "error": f"No {terminology} concepts matching '{term}'.",
            }

        rows = [
            {
                "code": c.get("code"),
                "name": c.get("name"),
                "leaf": c.get("leaf"),
            }
            for c in concepts
        ]

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "terminology": terminology,
                "term": term,
                "total_matching": payload.get("total"),
                "returned": len(rows),
                "note": "code is what get_concept expects.",
                "source": "NCI EVS (Enterprise Vocabulary Services)",
            },
        }

    def _get_concept(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch one concept's full detail from an NCI EVS terminology."""
        terminology = (arguments.get("terminology") or "").strip().lower()
        check = self._check_terminology(terminology)
        if check:
            return check

        code = (arguments.get("code") or "").strip()
        if not code:
            return {
                "status": "error",
                "error": "code is required, e.g. 'C143481' (CTCAE5) or "
                "'E11.9' (ICD-10-CM).",
            }

        response = requests.get(
            f"{EVS_BASE_URL}/concept/{terminology}/{code}",
            params={"include": "summary"},
            timeout=self.timeout,
        )
        if response.status_code == 404:
            return {
                "status": "error",
                "error": f"No {terminology} concept with code '{code}'.",
            }
        response.raise_for_status()
        data = response.json()

        definitions = data.get("definitions") or []
        synonyms: List[Dict[str, Any]] = [
            {
                "name": s.get("name"),
                "type": s.get("termType"),
                "source": s.get("source"),
            }
            for s in data.get("synonyms") or []
        ]
        properties = {
            p.get("type"): p.get("value")
            for p in data.get("properties") or []
            if p.get("type")
        }

        return {
            "status": "success",
            "data": {
                "code": data.get("code"),
                "name": data.get("name"),
                "terminology": data.get("terminology") or terminology,
                "active": data.get("active"),
                "definition": definitions[0].get("definition") if definitions else None,
                "synonyms": synonyms[:20],
                "properties": properties,
            },
            "metadata": {
                "terminology": terminology,
                "code": code,
                "source": "NCI EVS (Enterprise Vocabulary Services)",
            },
        }
