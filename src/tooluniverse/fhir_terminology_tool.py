# fhir_terminology_tool.py
"""
FHIR Terminology Service tool for ToolUniverse.

tx.fhir.org is HL7's own public FHIR R4 terminology server, implementing
the standard Terminology Service operations (CodeSystem/$lookup,
ValueSet/$expand) across SNOMED CT, LOINC, RxNorm, ICD-10-CM, and UCUM in
one API. Its main value here is SNOMED CT, which ToolUniverse could
previously only reach as flat keyword search via the generic OLS wrapper:
this adds proper code-based $lookup (resolving a SNOMED code to its
display name and properties) and, more importantly, subsumption-based
hierarchy expansion -- finding every descendant/subtype of a SNOMED
concept, which nothing else in ToolUniverse does. LOINC, RxNorm, and
ICD-10-CM already have dedicated, richer ToolUniverse tools (LOINCTool,
RxNormTool, ICD10Tool); this generic interface still accepts them for
convenience, but prefer those three for those three vocabularies.

ConceptMap/$translate (cross-vocabulary code translation, e.g. SNOMED to
ICD-10-CM) is part of the same FHIR Terminology Service spec but returned
"No suitable ConceptMaps found" for every pairing tried against this
public server, so it is not exposed here.

API: https://tx.fhir.org/r4
No authentication required.
"""

from typing import Any, Dict, List

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

FHIR_TX_BASE_URL = "https://tx.fhir.org/r4"

_SYSTEM_ALIASES = {
    "snomed": "http://snomed.info/sct",
    "loinc": "http://loinc.org",
    "rxnorm": "http://www.nlm.nih.gov/research/umls/rxnorm",
    "icd10cm": "http://hl7.org/fhir/sid/icd-10-cm",
    "ucum": "http://unitsofmeasure.org",
}


def _resolve_system(system: str) -> str:
    """Accept a friendly alias ('snomed') or a full FHIR system URI."""
    return _SYSTEM_ALIASES.get(system.strip().lower(), system.strip())


def _flatten_parameters(params: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Flatten a FHIR Parameters resource's simple (non-repeating) values."""
    simple_types = (
        "valueString",
        "valueCode",
        "valueUri",
        "valueBoolean",
        "valueInteger",
        "valueDecimal",
    )
    flat: Dict[str, Any] = {}
    for p in params:
        name = p.get("name")
        if name in flat:
            continue
        for key in simple_types:
            if key in p:
                flat[name] = p[key]
                break
    return flat


def _designations(
    params: List[Dict[str, Any]], limit: int = 10
) -> List[Dict[str, Any]]:
    """Extract alternate names/synonyms from a $lookup response."""
    out = []
    for p in params:
        if p.get("name") != "designation":
            continue
        part = {d.get("name"): d for d in p.get("part") or []}
        value = (part.get("value") or {}).get("valueString")
        use = ((part.get("use") or {}).get("valueCoding") or {}).get("display")
        if value:
            out.append({"value": value, "use": use})
        if len(out) >= limit:
            break
    return out


@register_tool("FHIRTerminologyTool")
class FHIRTerminologyTool(BaseTool):
    """
    Tool for querying HL7's public FHIR Terminology Service.

    Supports resolving a code to its display name (primarily useful for
    SNOMED CT, which ToolUniverse otherwise only reaches via fuzzy text
    search), and expanding a value set -- including SNOMED CT's implicit
    subsumption value sets, which return every descendant of a concept.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "lookup_code"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the FHIR terminology lookup."""
        try:
            if self.operation == "lookup_code":
                return self._lookup_code(arguments)
            if self.operation == "expand_valueset":
                return self._expand_valueset(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"FHIR terminology request timed out after "
                f"{self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to the FHIR terminology server. "
                "Check network.",
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {
                "status": "error",
                "error": f"FHIR terminology server returned HTTP {code}",
            }
        except ValueError:
            return {
                "status": "error",
                "error": "FHIR terminology server returned a non-JSON response",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Error querying FHIR terminology server: {str(e)}",
            }

    def _lookup_code(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve one code to its display name and metadata."""
        system = (arguments.get("system") or "").strip()
        if not system:
            return {
                "status": "error",
                "error": "system is required: 'snomed' or a full FHIR "
                "system URI. LOINC/RxNorm/ICD-10-CM are also accepted "
                "but already have dedicated ToolUniverse tools.",
            }

        code = (arguments.get("code") or "").strip()
        if not code:
            return {
                "status": "error",
                "error": "code is required, e.g. '22298006' (SNOMED CT: "
                "Myocardial infarction).",
            }

        resolved_system = _resolve_system(system)
        response = requests.get(
            f"{FHIR_TX_BASE_URL}/CodeSystem/$lookup",
            params={"system": resolved_system, "code": code},
            timeout=self.timeout,
        )
        if response.status_code in (404, 422):
            outcome = response.json()
            detail = (
                (outcome.get("issue") or [{}])[0].get("details", {}).get("text")
            )
            return {
                "status": "error",
                "error": detail or f"No concept found for {system}:{code}.",
            }
        response.raise_for_status()
        payload = response.json()
        params = payload.get("parameter") or []
        flat = _flatten_parameters(params)

        return {
            "status": "success",
            "data": {
                "code": flat.get("code", code),
                "display": flat.get("display"),
                "system": flat.get("system", resolved_system),
                "system_version": flat.get("version"),
                "code_system_name": flat.get("name"),
                "inactive": flat.get("abstract"),
                "alternate_names": _designations(params),
            },
            "metadata": {
                "system": system,
                "code": code,
                "source": "HL7 FHIR Terminology Service (tx.fhir.org)",
            },
        }

    def _expand_valueset(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Expand a value set to its member codes.

        For SNOMED CT hierarchy traversal, use a value_set_url of the form
        'http://snomed.info/sct?fhir_vs=isa/<code>' to get every descendant
        of a concept.
        """
        value_set_url = (arguments.get("value_set_url") or "").strip()
        if not value_set_url:
            return {
                "status": "error",
                "error": "value_set_url is required, e.g. "
                "'http://snomed.info/sct?fhir_vs=isa/22298006' for every "
                "descendant of Myocardial infarction.",
            }

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 50
        limit = min(limit, 500)

        response = requests.get(
            f"{FHIR_TX_BASE_URL}/ValueSet/$expand",
            params={"url": value_set_url, "count": limit},
            timeout=self.timeout,
        )
        if response.status_code in (404, 422):
            outcome = response.json()
            detail = (
                (outcome.get("issue") or [{}])[0].get("details", {}).get("text")
            )
            return {
                "status": "error",
                "error": detail or f"No value set found for '{value_set_url}'.",
            }
        response.raise_for_status()
        payload = response.json()
        expansion = payload.get("expansion") or {}
        contains = expansion.get("contains") or []

        if not contains:
            return {
                "status": "error",
                "error": f"Value set '{value_set_url}' expanded to zero "
                "concepts.",
            }

        rows = [
            {
                "system": c.get("system"),
                "code": c.get("code"),
                "display": c.get("display"),
            }
            for c in contains
        ]

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "value_set_url": value_set_url,
                "total_matching": expansion.get("total"),
                "returned": len(rows),
                "source": "HL7 FHIR Terminology Service (tx.fhir.org)",
            },
        }
