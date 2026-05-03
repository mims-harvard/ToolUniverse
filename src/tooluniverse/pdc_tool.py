"""
PDC (Proteomics Data Commons) Tool - NCI Cancer Proteomics Database

Provides access to the PDC GraphQL API for querying cancer proteomics data
from programs like CPTAC, ICPC, APOLLO, HTAN, and others.

API: https://pdc.cancer.gov/graphql
Authentication: None required (free public API).
"""

import requests
from typing import Dict, Any, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

PDC_GRAPHQL_URL = "https://pdc.cancer.gov/graphql"


def _execute_graphql(
    query: str, variables: Optional[Dict] = None, timeout: int = 30
) -> Dict[str, Any]:
    """Execute a GraphQL query against PDC."""
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    try:
        response = requests.post(
            PDC_GRAPHQL_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=timeout,
        )
        if response.status_code != 200:
            return {
                "ok": False,
                "error": "PDC API returned HTTP %d" % response.status_code,
            }
        data = response.json()
        if "errors" in data:
            msgs = "; ".join(e.get("message", str(e)) for e in data["errors"])
            return {"ok": False, "error": "GraphQL error: %s" % msgs}
        return {"ok": True, "data": data.get("data", {})}
    except requests.exceptions.Timeout:
        return {"ok": False, "error": "PDC API request timed out"}
    except requests.exceptions.ConnectionError:
        return {"ok": False, "error": "Failed to connect to PDC API"}
    except Exception as e:
        return {"ok": False, "error": "Request failed: %s" % str(e)}


@register_tool("PDCTool")
class PDCTool(BaseTool):
    """
    Tool for querying the NCI Proteomics Data Commons (PDC).

    PDC houses annotated proteomics data from CPTAC, ICPC, APOLLO, CBTN,
    and other cancer research programs covering 19+ cancer types with
    160+ datasets.

    Provides access to:
    - Study search and metadata (disease type, analytical fraction, experiment type)
    - Gene/protein information with spectral counts across studies
    - Program and project listings (CPTAC, ICPC, APOLLO, etc.)
    - Detailed study summaries with file counts
    - Clinical data per study (demographics, diagnoses)
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a PDC query."""
        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        handlers = {
            "search_studies": self._search_studies,
            "get_gene_protein": self._get_gene_protein,
            "list_programs": self._list_programs,
            "get_study_summary": self._get_study_summary,
            "get_clinical_data": self._get_clinical_data,
        }

        handler = handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": "Unknown operation: %s" % operation,
                "available_operations": list(handlers.keys()),
            }

        try:
            return handler(arguments)
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "PDC API request timed out"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to PDC API"}
        except Exception as e:
            return {"status": "error", "error": "Operation failed: %s" % str(e)}

    def _search_studies(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search PDC studies by name/keyword."""
        query_text = arguments.get("query")
        if not query_text:
            return {
                "status": "error",
                "error": "query parameter is required for study search",
            }

        gql = """
        {
            studySearch(name: "%s") {
                studies {
                    study_id
                    name
                    pdc_study_id
                    submitter_id_name
                }
                total
            }
        }
        """ % query_text.replace('"', '\\"')

        result = _execute_graphql(gql, timeout=30)
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        search_data = result["data"].get("studySearch", {})
        studies = search_data.get("studies", [])

        return {
            "status": "success",
            "data": {
                "query": query_text,
                "studies": studies,
                "num_results": len(studies),
            },
        }

    def _get_gene_protein(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get protein information and study coverage for a gene symbol."""
        gene_name = arguments.get("gene_name")
        if not gene_name:
            return {
                "status": "error",
                "error": "gene_name parameter is required",
            }

        gql = """
        {
            geneSpectralCount(gene_name: "%s") {
                gene_id
                gene_name
                NCBI_gene_id
                authority
                description
                organism
                proteins
                spectral_counts {
                    study_id
                    pdc_study_id
                    project_id
                    spectral_count
                    distinct_peptide
                    unshared_peptide
                }
            }
        }
        """ % gene_name.replace('"', '\\"')

        result = _execute_graphql(gql, timeout=30)
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        gene_data = result["data"].get("geneSpectralCount", [])
        if not gene_data:
            return {
                "status": "error",
                "error": "Gene '%s' not found in PDC" % gene_name,
            }

        # The API returns a list but typically one entry for the gene
        gene_info = gene_data[0]

        # Parse protein accessions (semicolon-separated string)
        proteins_str = gene_info.get("proteins", "")
        protein_list = (
            [p.strip() for p in proteins_str.split(";") if p.strip()]
            if proteins_str
            else []
        )

        return {
            "status": "success",
            "data": {
                "gene_id": gene_info.get("gene_id"),
                "gene_name": gene_info.get("gene_name"),
                "ncbi_gene_id": gene_info.get("NCBI_gene_id"),
                "authority": gene_info.get("authority"),
                "description": gene_info.get("description"),
                "organism": gene_info.get("organism"),
                "proteins": protein_list,
                "num_proteins": len(protein_list),
                "spectral_counts": gene_info.get("spectral_counts", []),
                "num_studies": len(gene_info.get("spectral_counts", [])),
            },
        }

    def _list_programs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List all PDC programs and their projects."""
        gql = """
        {
            allPrograms {
                program_id
                name
                projects {
                    project_id
                    name
                }
            }
        }
        """

        result = _execute_graphql(gql, timeout=30)
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        programs = result["data"].get("allPrograms", [])

        return {
            "status": "success",
            "data": {
                "programs": programs,
                "num_programs": len(programs),
            },
        }

    def _get_study_summary(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed metadata for a specific study by PDC study ID."""
        pdc_study_id = arguments.get("pdc_study_id")
        if not pdc_study_id:
            return {
                "status": "error",
                "error": "pdc_study_id parameter is required (e.g., 'PDC000127')",
            }

        gql = """
        {
            study(pdc_study_id: "%s") {
                study_id
                study_name
                pdc_study_id
                disease_type
                primary_site
                analytical_fraction
                experiment_type
                cases_count
                aliquots_count
                program_name
                project_name
                embargo_date
                filesCount {
                    data_category
                    file_type
                    files_count
                }
            }
        }
        """ % pdc_study_id.replace('"', '\\"')

        result = _execute_graphql(gql, timeout=30)
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        study_data = result["data"].get("study", [])
        if not study_data:
            return {
                "status": "error",
                "error": "Study '%s' not found in PDC" % pdc_study_id,
            }

        study = study_data[0]

        return {
            "status": "success",
            "data": {
                "study_id": study.get("study_id"),
                "study_name": study.get("study_name"),
                "pdc_study_id": study.get("pdc_study_id"),
                "disease_type": study.get("disease_type"),
                "primary_site": study.get("primary_site"),
                "analytical_fraction": study.get("analytical_fraction"),
                "experiment_type": study.get("experiment_type"),
                "cases_count": study.get("cases_count"),
                "aliquots_count": study.get("aliquots_count"),
                "program_name": study.get("program_name"),
                "project_name": study.get("project_name"),
                "embargo_date": study.get("embargo_date"),
                "file_counts": study.get("filesCount", []),
            },
        }

    def _get_clinical_data(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get clinical metadata for samples in a study."""
        pdc_study_id = arguments.get("pdc_study_id")
        if not pdc_study_id:
            return {
                "status": "error",
                "error": "pdc_study_id parameter is required (e.g., 'PDC000127')",
            }

        offset = arguments.get("offset", 0)
        limit = arguments.get("limit", 20)

        gql = """
        {
            paginatedCaseDemographicsPerStudy(
                pdc_study_id: "%s",
                offset: %d,
                limit: %d
            ) {
                total
                caseDemographicsPerStudy {
                    case_id
                    case_submitter_id
                    disease_type
                    primary_site
                    demographics {
                        gender
                        ethnicity
                        race
                    }
                }
            }
        }
        """ % (pdc_study_id.replace('"', '\\"'), offset, limit)

        result = _execute_graphql(gql, timeout=30)
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        paginated = result["data"].get("paginatedCaseDemographicsPerStudy", {})
        cases = paginated.get("caseDemographicsPerStudy", [])
        total = paginated.get("total", 0)

        return {
            "status": "success",
            "data": {
                "pdc_study_id": pdc_study_id,
                "total_cases": total,
                "offset": offset,
                "limit": limit,
                "cases": cases,
                "num_returned": len(cases),
            },
        }
