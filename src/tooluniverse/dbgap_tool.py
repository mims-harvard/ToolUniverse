# dbgap_tool.py
"""
dbGaP (database of Genotypes and Phenotypes) tool for ToolUniverse.

dbGaP is NCBI's controlled-access archive of US genotype-phenotype
studies, the American counterpart to EGA. It dropped out of NCBI's
E-utilities entirely (the "gap" database no longer exists there) in favor
of a standards-based FHIR API, discovered by finding a "dbGaP FHIR" label
buried in the advanced-search page and following it to a live HAPI FHIR
server. Study metadata (title, condition, dataset/variable counts, release
date) is public even though the underlying genotype/phenotype data
requires Data Access Committee approval, mirroring EGA.

API: https://dbgap-api.ncbi.nlm.nih.gov/fhir/x1
No authentication required for metadata.
"""

from typing import Any, Dict, List

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

DBGAP_FHIR_URL = "https://dbgap-api.ncbi.nlm.nih.gov/fhir/x1"

_CONTENT_EXTENSION_SUFFIXES = {
    "NumPhenotypeDatasets": "phenotype_dataset_count",
    "NumMolecularDatasets": "molecular_dataset_count",
    "NumVariables": "variable_count",
    "NumDocuments": "document_count",
}


def _unique_texts(
    codeable_concepts: List[Dict[str, Any]], limit: int = 10
) -> List[str]:
    """Dedupe FHIR CodeableConcept.text values (MeSH synonym expansion
    otherwise produces dozens of near-duplicate entries per condition)."""
    seen: List[str] = []
    for concept in codeable_concepts or []:
        text = concept.get("text")
        if text and text not in seen:
            seen.append(text)
        if len(seen) >= limit:
            break
    return seen


def _extension_value(extensions: List[Dict[str, Any]], suffix: str) -> Any:
    for ext in extensions or []:
        if ext.get("url", "").endswith(suffix):
            for key in ("valueUrl", "valueDate", "valueString", "valueCount"):
                if key in ext:
                    value = ext[key]
                    return value.get("value") if isinstance(value, dict) else value
    return None


def _content_counts(extensions: List[Dict[str, Any]]) -> Dict[str, Any]:
    for ext in extensions or []:
        if ext.get("url", "").endswith("ResearchStudy-Content"):
            return {
                field: _extension_value(ext.get("extension") or [], suffix)
                for suffix, field in _CONTENT_EXTENSION_SUFFIXES.items()
            }
    return {field: None for field in _CONTENT_EXTENSION_SUFFIXES.values()}


@register_tool("DbGaPTool")
class DbGaPTool(BaseTool):
    """
    Tool for searching and resolving dbGaP study metadata via its FHIR API.

    Supports searching studies by title keyword, and fetching one study's
    full public metadata (condition, dataset/variable counts, consent
    groups, release date) by its phs accession.

    No authentication required for metadata.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "search_studies"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the dbGaP FHIR lookup."""
        try:
            if self.operation == "search_studies":
                return self._search_studies(arguments)
            if self.operation == "get_study":
                return self._get_study(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"dbGaP request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to dbGaP. Check network.",
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {"status": "error", "error": f"dbGaP returned HTTP {code}"}
        except ValueError:
            return {"status": "error", "error": "dbGaP returned a non-JSON response"}
        except Exception as e:
            return {"status": "error", "error": f"Error querying dbGaP: {str(e)}"}

    def _search_studies(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search dbGaP studies by title keyword."""
        query = (arguments.get("query") or "").strip()
        if not query:
            return {
                "status": "error",
                "error": "query is required, e.g. 'diabetes' or 'autism'.",
            }

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 25
        limit = min(limit, 100)

        response = requests.get(
            f"{DBGAP_FHIR_URL}/ResearchStudy",
            params={"title": query, "_count": limit},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        entries = payload.get("entry") or []

        if not entries:
            return {
                "status": "error",
                "error": f"No dbGaP studies matching '{query}'.",
            }

        rows = []
        for entry in entries:
            study = entry.get("resource") or {}
            rows.append(
                {
                    "phs_id": study.get("id"),
                    "title": study.get("title"),
                    "status": study.get("status"),
                    "conditions": _unique_texts(study.get("condition"), limit=5),
                }
            )

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "query": query,
                "total_matching": payload.get("total"),
                "returned": len(rows),
                "note": "phs_id is what get_study expects for the full "
                "record.",
                "source": "dbGaP (NCBI)",
            },
        }

    def _get_study(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch one dbGaP study's full public metadata by phs accession."""
        phs_id = (arguments.get("phs_id") or "").strip()
        if not phs_id:
            return {
                "status": "error",
                "error": "phs_id is required, e.g. 'phs000681'. Use "
                "search_studies to find one.",
            }

        response = requests.get(
            f"{DBGAP_FHIR_URL}/ResearchStudy/{phs_id}", timeout=self.timeout
        )
        if response.status_code == 404:
            return {
                "status": "error",
                "error": f"No dbGaP study with accession '{phs_id}'.",
            }
        response.raise_for_status()
        study = response.json()
        extensions = study.get("extension") or []

        return {
            "status": "success",
            "data": {
                "phs_id": study.get("id"),
                "title": study.get("title"),
                "status": study.get("status"),
                "description": study.get("description"),
                "conditions": _unique_texts(study.get("condition")),
                "study_overview_url": _extension_value(
                    extensions, "StudyOverviewUrl"
                ),
                "release_date": _extension_value(extensions, "ReleaseDate"),
                **_content_counts(extensions),
            },
            "metadata": {
                "phs_id": phs_id,
                "note": "Metadata only; the underlying genotype/phenotype "
                "data requires Data Access Committee approval.",
                "source": "dbGaP (NCBI)",
            },
        }
