# orphadata_tool.py
"""
Orphadata Science REST API tool for ToolUniverse.

Orphadata is the machine-readable distribution of Orphanet, the reference
knowledge base for rare diseases, and a Global Core Biodata Resource. It
provides ORPHAcode identifiers, cross-references to OMIM/ICD-10/ICD-11/MeSH/
UMLS/MedDRA, prevalence estimates, and HPO phenotype annotations.

ToolUniverse already wraps Orphanet term lookup; this tool adds the
structured cross-referencing, epidemiology, and phenotype services that the
Orphadata API exposes separately.

API: https://api.orphadata.com
No authentication required.
"""

import requests
from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool

ORPHADATA_BASE_URL = "https://api.orphadata.com"


def _results(payload: Dict[str, Any]) -> Any:
    """Unwrap the {"data": {"results": ...}} envelope Orphadata returns."""
    data = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(data, dict):
        return data.get("results")
    return None


def _external_references(results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten Orphanet's ExternalReference list into id/source pairs."""
    refs = results.get("ExternalReference")
    out = []
    for ref in refs if isinstance(refs, list) else []:
        if not isinstance(ref, dict):
            continue
        out.append(
            {
                "source": ref.get("Source"),
                "reference": ref.get("Reference"),
                "relation": ref.get("DisorderMappingRelation"),
                "icd_relation": ref.get("DisorderMappingICDRelation"),
            }
        )
    return out


@register_tool("OrphadataTool")
class OrphadataTool(BaseTool):
    """
    Tool for querying Orphadata rare disease records.

    Supports lookup by ORPHAcode, search by disease name, prevalence and
    epidemiology retrieval, and HPO phenotype annotations.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        self.operation = tool_config.get("fields", {}).get("operation", "get_disorder")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Orphadata API call."""
        try:
            if self.operation == "get_disorder":
                return self._get_disorder(arguments)
            elif self.operation == "search_by_name":
                return self._search_by_name(arguments)
            elif self.operation == "get_epidemiology":
                return self._get_epidemiology(arguments)
            elif self.operation == "get_phenotypes":
                return self._get_phenotypes(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Orphadata request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to Orphadata. Check network.",
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {"status": "error", "error": f"Orphadata returned HTTP {code}"}
        except ValueError:
            return {
                "status": "error",
                "error": "Orphadata returned a non-JSON response",
            }
        except Exception as e:
            return {"status": "error", "error": f"Error querying Orphadata: {str(e)}"}

    def _fetch(self, path: str, lang: str) -> Any:
        """GET one Orphadata path, returning parsed results or None on 404."""
        url = f"{ORPHADATA_BASE_URL}/{path}"
        response = requests.get(url, params={"lang": lang}, timeout=self.timeout)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return _results(response.json())

    def _lang(self, arguments: Dict[str, Any]) -> str:
        lang = arguments.get("lang")
        return lang if lang else "en"

    def _get_disorder(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve a rare disease by ORPHAcode with its cross-references."""
        orphacode = arguments.get("orphacode")
        if orphacode is None or str(orphacode).strip() == "":
            return {
                "status": "error",
                "error": "orphacode is required, e.g. 558 (Marfan syndrome). "
                "Use Orphadata_search_by_name to find ORPHAcodes.",
            }

        code = str(orphacode).strip()
        results = self._fetch(
            f"rd-cross-referencing/orphacodes/{code}", self._lang(arguments)
        )
        if results is None:
            return {
                "status": "error",
                "error": f"No Orphanet disorder with ORPHAcode '{code}'.",
            }

        record = results[0] if isinstance(results, list) and results else results
        if not isinstance(record, dict):
            return {
                "status": "error",
                "error": f"Unexpected Orphadata response shape for ORPHAcode '{code}'.",
            }

        synonyms = record.get("Synonym")
        summaries = record.get("SummaryInformation")
        definition = None
        if isinstance(summaries, list) and summaries:
            first = summaries[0]
            if isinstance(first, dict):
                texts = first.get("Definition") or first.get("TextSection")
                definition = texts if isinstance(texts, str) else None

        return {
            "status": "success",
            "data": {
                "orphacode": record.get("ORPHAcode"),
                "preferred_term": record.get("Preferred term"),
                "synonyms": synonyms if isinstance(synonyms, list) else [],
                "disorder_group": record.get("DisorderGroup"),
                "typology": record.get("Typology"),
                "definition": definition,
                "orphanet_url": record.get("OrphanetURL"),
                "external_references": _external_references(record),
                "last_updated": record.get("Date"),
            },
            "metadata": {
                "orphacode": code,
                "source": "Orphadata / Orphanet — Global Core Biodata Resource",
            },
        }

    def _search_by_name(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Look up a rare disease by its name or a known synonym."""
        name = arguments.get("name")
        if not name:
            return {
                "status": "error",
                "error": "name is required, e.g. 'Marfan syndrome'. "
                "Orphanet matches on preferred terms and synonyms.",
            }

        results = self._fetch(
            "rd-cross-referencing/orphacodes/names/"
            f"{requests.utils.quote(name.strip())}",
            self._lang(arguments),
        )
        if results is None:
            return {
                "status": "error",
                "error": f"No Orphanet disorder matching name '{name}'. "
                "Try the full clinical name, e.g. 'Marfan syndrome'.",
            }

        records = results if isinstance(results, list) else [results]
        out = []
        for record in records:
            if not isinstance(record, dict):
                continue
            out.append(
                {
                    "orphacode": record.get("ORPHAcode"),
                    "preferred_term": record.get("Preferred term"),
                    "disorder_group": record.get("DisorderGroup"),
                    "orphanet_url": record.get("OrphanetURL"),
                }
            )

        return {
            "status": "success",
            "data": out,
            "metadata": {
                "query": name,
                "returned": len(out),
                "source": "Orphadata / Orphanet",
            },
        }

    def _get_epidemiology(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve prevalence and epidemiology estimates for a disorder."""
        orphacode = arguments.get("orphacode")
        if orphacode is None or str(orphacode).strip() == "":
            return {"status": "error", "error": "orphacode is required, e.g. 558."}

        code = str(orphacode).strip()
        results = self._fetch(
            f"rd-epidemiology/orphacodes/{code}", self._lang(arguments)
        )
        if results is None:
            return {
                "status": "error",
                "error": f"No Orphanet epidemiology data for ORPHAcode '{code}'.",
            }

        record = results[0] if isinstance(results, list) and results else results
        prevalences = record.get("Prevalence") if isinstance(record, dict) else None
        out = []
        for p in prevalences if isinstance(prevalences, list) else []:
            if not isinstance(p, dict):
                continue
            out.append(
                {
                    "prevalence_type": p.get("PrevalenceType"),
                    "prevalence_class": p.get("PrevalenceClass"),
                    "prevalence_qualification": p.get("PrevalenceQualification"),
                    "val_moy": p.get("ValMoy"),
                    "geographic_area": p.get("PrevalenceGeographic"),
                    "validation_status": p.get("PrevalenceValidationStatus"),
                    "source": p.get("Source"),
                }
            )

        return {
            "status": "success",
            "data": out,
            "metadata": {
                "orphacode": code,
                "preferred_term": (
                    record.get("Preferred term") if isinstance(record, dict) else None
                ),
                "returned": len(out),
                "source": "Orphadata / Orphanet",
            },
        }

    def _get_phenotypes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve HPO phenotype annotations for a disorder."""
        orphacode = arguments.get("orphacode")
        if orphacode is None or str(orphacode).strip() == "":
            return {"status": "error", "error": "orphacode is required, e.g. 558."}

        code = str(orphacode).strip()
        results = self._fetch(f"rd-phenotypes/orphacodes/{code}", self._lang(arguments))
        if results is None:
            return {
                "status": "error",
                "error": f"No Orphanet phenotype annotations for ORPHAcode '{code}'.",
            }

        record = results[0] if isinstance(results, list) and results else results
        # The phenotype service nests the associations one level deeper than
        # the cross-referencing service, under a "Disorder" key.
        disorder = record.get("Disorder") if isinstance(record, dict) else None
        if isinstance(disorder, list):
            disorder = disorder[0] if disorder else {}
        if not isinstance(disorder, dict):
            disorder = record if isinstance(record, dict) else {}
        assoc = disorder.get("HPODisorderAssociation")

        out = []
        for a in assoc if isinstance(assoc, list) else []:
            if not isinstance(a, dict):
                continue
            hpo = a.get("HPO") or {}
            if isinstance(hpo, list):
                hpo = hpo[0] if hpo else {}
            out.append(
                {
                    "hpo_id": hpo.get("HPOId") if isinstance(hpo, dict) else None,
                    "hpo_term": hpo.get("HPOTerm") if isinstance(hpo, dict) else None,
                    "frequency": a.get("HPOFrequency"),
                    "diagnostic_criteria": a.get("DiagnosticCriteria"),
                }
            )

        limit = arguments.get("limit")
        if isinstance(limit, int) and limit > 0:
            out = out[:limit]

        return {
            "status": "success",
            "data": out,
            "metadata": {
                "orphacode": code,
                "preferred_term": disorder.get("Preferred term"),
                "returned": len(out),
                "source": "Orphadata / Orphanet",
            },
        }
