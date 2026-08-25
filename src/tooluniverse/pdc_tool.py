"""
PDC (Proteomics Data Commons) Tool - NCI Cancer Proteomics Database

Provides access to the PDC GraphQL API for querying cancer proteomics data
from programs like CPTAC, ICPC, APOLLO, HTAN, and others.

API: https://pdc.cancer.gov/graphql
Authentication: None required (free public API).
"""

import json

import requests
from typing import Dict, Any, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

PDC_GRAPHQL_URL = "https://pdc.cancer.gov/graphql"

# Structured study-catalog fields that PDC_search_studies matches a query
# against, in the order they are reported back to the caller. Every entry is a
# curated PDC metadata field except ``submitter_id_name``, which is the free
# text study title. Keeping the title last means curated matches are listed
# first in each study's ``matched_fields``.
STUDY_SEARCH_FIELDS = (
    "disease_type",
    "primary_site",
    "analytical_fraction",
    "experiment_type",
    "program_name",
    "project_name",
    "submitter_id_name",
)

# Curated metadata fields the query is matched against. A hit on one of these
# is a controlled-vocabulary hit, as opposed to a coincidental study-title hit.
STUDY_SEARCH_CURATED_FIELDS = tuple(
    f for f in STUDY_SEARCH_FIELDS if f != "submitter_id_name"
)

# Page size used when pulling the PDC study catalog. PDC currently publishes a
# few hundred studies, so this normally takes a single request.
STUDY_CATALOG_PAGE_SIZE = 500

# Safety valve so a malformed ``total`` from the API cannot cause a runaway
# pagination loop.
STUDY_CATALOG_MAX_PAGES = 20


def _gql_string(value: str) -> str:
    """Render a Python string as a quoted GraphQL string literal.

    GraphQL string syntax is a subset of JSON string syntax, so ``json.dumps``
    escapes quotes, backslashes and control characters correctly.
    """
    return json.dumps(str(value))


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
            "get_quant_data_matrix": self._get_quant_data_matrix,
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

    def _fetch_study_catalog(self) -> Dict[str, Any]:
        """Fetch the full PDC study catalog with its structured metadata.

        Uses ``getPaginatedUIStudy``, which returns the curated study
        annotations (disease type, primary site, analytical fraction,
        experiment type, program and project) alongside the study title.
        The legacy ``studySearch(name:)`` endpoint only matches the title and
        silently truncates at 100 results, so it cannot back a search that
        claims to cover disease/program/fraction.
        """
        gql = """
        {
            getPaginatedUIStudy(offset: %d, limit: %d) {
                total
                uiStudies {
                    study_id
                    pdc_study_id
                    submitter_id_name
                    disease_type
                    primary_site
                    analytical_fraction
                    experiment_type
                    program_name
                    project_name
                }
            }
        }
        """

        studies: list = []
        total = 0
        for page in range(STUDY_CATALOG_MAX_PAGES):
            offset = page * STUDY_CATALOG_PAGE_SIZE
            result = _execute_graphql(
                gql % (offset, STUDY_CATALOG_PAGE_SIZE), timeout=60
            )
            if not result["ok"]:
                return {"ok": False, "error": result["error"]}

            paginated = result["data"].get("getPaginatedUIStudy") or {}
            page_studies = paginated.get("uiStudies") or []
            total = paginated.get("total") or total
            studies.extend(page_studies)

            if not page_studies or len(studies) >= total:
                break

        return {"ok": True, "studies": studies, "total": total or len(studies)}

    def _fetch_program_vocabulary_matches(self, query_text: str) -> Dict[str, Any]:
        """Resolve a query against PDC's controlled program vocabulary.

        PDC's ``program_name`` filter matches the program *short name* (e.g.
        "CPTAC", "APOLLO", "ICPC"), which does not appear in the long program
        name carried on each study ("Clinical Proteomic Tumor Analysis
        Consortium"). Substring matching over the catalog therefore cannot
        find every study belonging to a program, so the program acronym is
        resolved server-side and unioned into the results.

        Only ``program_name`` needs this: the values of disease_type,
        primary_site, analytical_fraction, experiment_type and project_name
        are carried verbatim on each catalog record, so substring matching
        over the catalog is already a superset of the server-side filter for
        those fields.

        Note: each filter must be sent as its own request. Combining several
        filtered ``getPaginatedUIStudy`` selections into one document via
        GraphQL aliases makes the API return results for the wrong filter.
        """
        gql = (
            '{ getPaginatedUIStudy(offset: 0, limit: %d, program_name: %s) '
            "{ uiStudies { pdc_study_id } } }"
            % (STUDY_CATALOG_PAGE_SIZE, _gql_string(query_text))
        )
        result = _execute_graphql(gql, timeout=60)
        if not result["ok"]:
            return {"ok": False, "error": result["error"]}

        paginated = result["data"].get("getPaginatedUIStudy") or {}
        return {
            "ok": True,
            "pdc_study_ids": {
                s.get("pdc_study_id")
                for s in (paginated.get("uiStudies") or [])
                if s.get("pdc_study_id")
            },
        }

    def _search_studies(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search PDC studies across their curated metadata fields.

        The query is matched case-insensitively as a substring against each
        field in ``STUDY_SEARCH_FIELDS`` - the curated disease type, primary
        site, analytical fraction, experiment type, program and project, plus
        the study title - and additionally resolved against PDC's controlled
        program vocabulary so program acronyms work. Every returned study
        reports which fields matched, so a title-only hit is never mistaken
        for a curated disease-type hit.
        """
        query_text = arguments.get("query")
        if not query_text or not str(query_text).strip():
            return {
                "status": "error",
                "error": "query parameter is required for study search",
            }

        query_text = str(query_text).strip()
        needle = query_text.casefold()

        catalog = self._fetch_study_catalog()
        if not catalog["ok"]:
            return {"status": "error", "error": catalog["error"]}

        all_studies = catalog["studies"]

        warnings = []
        program_matches = self._fetch_program_vocabulary_matches(query_text)
        if program_matches["ok"]:
            program_study_ids = program_matches["pdc_study_ids"]
        else:
            program_study_ids = set()
            warnings.append(
                "Could not resolve '%s' against PDC's controlled program "
                "vocabulary (%s); program matching fell back to text "
                "matching on the program and project names carried by each "
                "study, so studies in a program whose acronym does not "
                "appear in their metadata may be missing."
                % (query_text, program_matches["error"])
            )

        matches = []
        num_results_by_field = {field: 0 for field in STUDY_SEARCH_FIELDS}

        for study in all_studies:
            matched_fields = [
                field
                for field in STUDY_SEARCH_FIELDS
                if needle in str(study.get(field) or "").casefold()
            ]
            if (
                study.get("pdc_study_id") in program_study_ids
                and "program_name" not in matched_fields
            ):
                matched_fields.append("program_name")
                matched_fields.sort(key=STUDY_SEARCH_FIELDS.index)
            if not matched_fields:
                continue

            for field in matched_fields:
                num_results_by_field[field] += 1

            name = study.get("submitter_id_name")
            matches.append(
                {
                    "study_id": study.get("study_id"),
                    "pdc_study_id": study.get("pdc_study_id"),
                    # ``name`` is kept for backward compatibility; PDC's study
                    # catalog exposes the title as submitter_id_name only.
                    "name": name,
                    "submitter_id_name": name,
                    "disease_type": study.get("disease_type"),
                    "primary_site": study.get("primary_site"),
                    "analytical_fraction": study.get("analytical_fraction"),
                    "experiment_type": study.get("experiment_type"),
                    "program_name": study.get("program_name"),
                    "project_name": study.get("project_name"),
                    "matched_fields": matched_fields,
                    "matched_curated_metadata": any(
                        field in STUDY_SEARCH_CURATED_FIELDS
                        for field in matched_fields
                    ),
                }
            )

        fields_searched = list(STUDY_SEARCH_FIELDS)
        data = {
            "query": query_text,
            "fields_searched": fields_searched,
            "num_studies_searched": len(all_studies),
            "studies": matches,
            "num_results": len(matches),
            "num_results_by_field": num_results_by_field,
        }
        if warnings:
            data["warnings"] = warnings

        if not matches:
            data["note"] = (
                "No PDC study matched '%s'. The query was compared "
                "case-insensitively as a substring against %d PDC studies on "
                "these fields: %s. This is an empty result, not a failed "
                "request - PDC has no study annotated with this term. Try a "
                "broader term (e.g. 'Lung' instead of a specific subtype), a "
                "program name such as 'CPTAC' or 'APOLLO', or an analytical "
                "fraction such as 'Proteome' or 'Phosphoproteome'."
                % (query_text, len(all_studies), ", ".join(fields_searched))
            )

        return {"status": "success", "data": data}

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

    def _get_quant_data_matrix(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get the quantitative protein abundance matrix (gene x aliquot) for a study.

        Returns the actual CPTAC/PDC quantitative expression values (e.g. log2
        ratios) - the core proteomic output - rather than spectral counts. The
        full matrix can be very large (thousands of genes x hundreds of aliquots),
        so the gene rows are truncated to max_genes; the column header (aliquot
        identifiers) is always returned in full.
        """
        pdc_study_id = arguments.get("pdc_study_id")
        if not pdc_study_id:
            return {
                "status": "error",
                "error": "pdc_study_id parameter is required (e.g., 'PDC000127')",
            }

        data_type = arguments.get("data_type", "log2_ratio")
        max_genes = arguments.get("max_genes", 50)
        try:
            max_genes = int(max_genes)
        except (TypeError, ValueError):
            max_genes = 50
        if max_genes < 0:
            max_genes = 0

        # quantDataMatrix returns a 2D array: row 0 is the header
        # (first cell label + aliquot identifiers), each subsequent row is a
        # gene followed by its per-aliquot quantitative values.
        gql = '{ quantDataMatrix(pdc_study_id: "%s" data_type: "%s") }' % (
            pdc_study_id.replace('"', '\\"'),
            data_type.replace('"', '\\"'),
        )

        result = _execute_graphql(gql, timeout=30)
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        matrix = result["data"].get("quantDataMatrix")
        if not matrix or not isinstance(matrix, list):
            return {
                "status": "error",
                "error": "No quantitative matrix returned for study '%s' (data_type '%s'). "
                "Verify the PDC study ID and that data_type is valid "
                "(e.g. 'log2_ratio', 'unshared_log2_ratio', 'precursor_area')."
                % (pdc_study_id, data_type),
            }

        header = matrix[0] if matrix else []
        gene_rows = matrix[1:]
        num_genes = len(gene_rows)
        # Header is [row-label, aliquot_1, aliquot_2, ...]; aliquots are columns.
        aliquots = header[1:] if len(header) > 1 else []

        truncated = num_genes > max_genes
        returned_rows = gene_rows[:max_genes]

        return {
            "status": "success",
            "data": {
                "pdc_study_id": pdc_study_id,
                "data_type": data_type,
                "num_genes": num_genes,
                "num_aliquots": len(aliquots),
                "header": header,
                "aliquots": aliquots,
                "matrix": returned_rows,
                "num_genes_returned": len(returned_rows),
                "truncated": truncated,
                "max_genes": max_genes,
            },
        }
