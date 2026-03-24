# progenetix_tool.py
"""
Progenetix Beacon v2 API tool for ToolUniverse.

Progenetix is a cancer genomics resource providing genome-wide
copy number variation (CNV) profiles from over 100,000 tumor samples.
It implements the GA4GH Beacon v2 protocol for querying cancer
genomics data by disease type, genomic region, or sample characteristics.

API: https://beacon.progenetix.org/beacon/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

PROGENETIX_BASE_URL = "https://beacon.progenetix.org/beacon"


@register_tool("ProgenetixTool")
class ProgenetixTool(BaseTool):
    """
    Tool for querying the Progenetix cancer CNV database via GA4GH Beacon v2.

    Progenetix contains genome-wide CNV profiles from 100,000+ tumor samples
    across hundreds of cancer types, classified using NCIt ontology codes.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "biosamples")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Progenetix Beacon API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Progenetix API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to Progenetix API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"Progenetix API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying Progenetix: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate Progenetix endpoint."""
        if self.endpoint == "biosamples":
            return self._get_biosamples(arguments)
        elif self.endpoint == "individuals":
            return self._get_individuals(arguments)
        elif self.endpoint == "filtering_terms":
            return self._get_filtering_terms(arguments)
        elif self.endpoint == "cohorts":
            return self._get_cohorts(arguments)
        elif self.endpoint == "cnv_search":
            return self._cnv_search(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _get_biosamples(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search biosamples (tumor samples) by NCIt disease code or other filters."""
        filters = arguments.get("filters", "")
        if not filters:
            return {
                "status": "error",
                "error": "filters parameter is required. Use NCIt codes like 'NCIT:C3058' (Glioblastoma) or 'NCIT:C4017' (Breast Cancer).",
            }

        limit = arguments.get("limit", 10)
        params = {"filters": filters, "limit": limit}
        skip = arguments.get("skip", None)
        if skip is not None:
            params["skip"] = skip

        url = f"{PROGENETIX_BASE_URL}/biosamples"
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        resp_data = response.json()

        result_sets = resp_data.get("response", {}).get("resultSets", [])
        samples = []
        total_count = 0

        for rs in result_sets:
            total_count += rs.get("resultsCount", 0)
            for s in rs.get("results", []):
                sample = {
                    "id": s.get("id"),
                    "biosample_status": s.get("biosampleStatus", {}).get("label"),
                    "histological_diagnosis": s.get("histologicalDiagnosis", {}).get(
                        "label"
                    ),
                    "histological_diagnosis_id": s.get("histologicalDiagnosis", {}).get(
                        "id"
                    ),
                    "pathological_stage": s.get("pathologicalStage", {}).get("label"),
                    "pathological_tnm": s.get("pathologicalTnmFinding", [{}])[0].get(
                        "label"
                    )
                    if s.get("pathologicalTnmFinding")
                    else None,
                    "sample_origin_type": s.get("sampleOriginType", {}).get("label"),
                    "external_references": [
                        {"id": er.get("id"), "label": er.get("label")}
                        for er in s.get("externalReferences", [])[:5]
                    ],
                }
                samples.append(sample)

        return {
            "status": "success",
            "data": {
                "filters": filters,
                "total_count": total_count,
                "returned_count": len(samples),
                "biosamples": samples,
            },
            "metadata": {
                "source": "Progenetix Beacon v2",
                "query_filters": filters,
            },
        }

    def _get_individuals(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search individuals (patients) by NCIt disease code or other filters."""
        filters = arguments.get("filters", "")
        if not filters:
            return {
                "status": "error",
                "error": "filters parameter is required. Use NCIt codes like 'NCIT:C9145' (AML) or 'NCIT:C3058' (Glioblastoma).",
            }

        limit = arguments.get("limit", 10)
        params = {"filters": filters, "limit": limit}

        url = f"{PROGENETIX_BASE_URL}/individuals"
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        resp_data = response.json()

        result_sets = resp_data.get("response", {}).get("resultSets", [])
        individuals = []
        total_count = 0

        for rs in result_sets:
            total_count += rs.get("resultsCount", 0)
            for ind in rs.get("results", []):
                individual = {
                    "id": ind.get("id"),
                    "sex": ind.get("sex", {}).get("label"),
                    "index_disease": ind.get("indexDisease", {})
                    .get("diseaseCode", {})
                    .get("label"),
                    "index_disease_id": ind.get("indexDisease", {})
                    .get("diseaseCode", {})
                    .get("id"),
                    "onset_age": ind.get("indexDisease", {})
                    .get("onset", {})
                    .get("age"),
                    "external_references": [
                        {"id": er.get("id"), "label": er.get("label")}
                        for er in ind.get("externalReferences", [])[:5]
                    ],
                }
                individuals.append(individual)

        return {
            "status": "success",
            "data": {
                "filters": filters,
                "total_count": total_count,
                "returned_count": len(individuals),
                "individuals": individuals,
            },
            "metadata": {
                "source": "Progenetix Beacon v2",
                "query_filters": filters,
            },
        }

    def _get_filtering_terms(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List available filtering terms (ontology codes) in Progenetix."""
        prefixes = arguments.get("prefixes", "NCIT")
        limit = arguments.get("limit", 25)

        params = {"prefixes": prefixes, "limit": limit}

        url = f"{PROGENETIX_BASE_URL}/filtering_terms"
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        resp_data = response.json()

        filtering_terms = resp_data.get("response", {}).get("filteringTerms", [])
        # Filter client-side by prefix (API does not reliably honor this param)
        if prefixes:
            prefix_upper = prefixes.upper()
            filtering_terms = [
                ft
                for ft in filtering_terms
                if str(ft.get("id", "")).upper().startswith(prefix_upper + ":")
            ]
        terms = [
            {
                "id": ft.get("id"),
                "label": ft.get("label"),
                "count": ft.get("count"),
                "type": ft.get("type"),
            }
            for ft in filtering_terms[:limit]
        ]

        return {
            "status": "success",
            "data": {
                "prefixes": prefixes,
                "total_terms": len(filtering_terms),
                "terms": terms,
            },
            "metadata": {
                "source": "Progenetix Beacon v2",
                "query_prefixes": prefixes,
            },
        }

    def _get_cohorts(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List available cohorts in Progenetix."""
        limit = arguments.get("limit", 10)

        url = f"{PROGENETIX_BASE_URL}/cohorts"
        params = {"limit": limit}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        resp_data = response.json()

        collections = resp_data.get("response", {}).get("collections", [])
        cohorts = []
        for c in collections[:limit]:
            cohorts.append(
                {
                    "id": c.get("id"),
                    "name": c.get("name"),
                    "cohort_size": c.get("cohortSize"),
                    "cohort_type": c.get("cohortType"),
                    "data_types": [dt.get("id") for dt in c.get("cohortDataTypes", [])],
                }
            )

        return {
            "status": "success",
            "data": {
                "total_cohorts": len(collections),
                "cohorts": cohorts,
            },
            "metadata": {
                "source": "Progenetix Beacon v2",
            },
        }

    def _cnv_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for biosamples with CNVs in a specific genomic region."""
        filters = arguments.get("filters", "")
        reference_name = arguments.get("reference_name", "")
        start = arguments.get("start")
        end = arguments.get("end")
        variant_type = arguments.get("variant_type", "")

        if not reference_name or start is None or end is None:
            return {
                "status": "error",
                "error": "reference_name, start, and end are required. Example: reference_name='refseq:NC_000007.14', start=55019017, end=55211628",
            }

        limit = arguments.get("limit", 10)
        params = {
            "referenceName": reference_name,
            "start": start,
            "end": end,
            "limit": limit,
        }
        if variant_type:
            params["variantType"] = variant_type
        if filters:
            params["filters"] = filters

        url = f"{PROGENETIX_BASE_URL}/biosamples"
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        resp_data = response.json()

        result_sets = resp_data.get("response", {}).get("resultSets", [])
        samples = []
        total_count = 0

        for rs in result_sets:
            total_count += rs.get("resultsCount", 0)
            for s in rs.get("results", []):
                sample = {
                    "id": s.get("id"),
                    "biosample_status": s.get("biosampleStatus", {}).get("label"),
                    "histological_diagnosis": s.get("histologicalDiagnosis", {}).get(
                        "label"
                    ),
                    "histological_diagnosis_id": s.get("histologicalDiagnosis", {}).get(
                        "id"
                    ),
                    "external_references": [
                        {"id": er.get("id")}
                        for er in s.get("externalReferences", [])[:3]
                    ],
                }
                samples.append(sample)

        return {
            "status": "success",
            "data": {
                "region": f"{reference_name}:{start}-{end}",
                "variant_type": variant_type or "any",
                "filters": filters or "none",
                "total_count": total_count,
                "returned_count": len(samples),
                "biosamples": samples,
            },
            "metadata": {
                "source": "Progenetix Beacon v2",
                "query_region": f"{reference_name}:{start}-{end}",
            },
        }
