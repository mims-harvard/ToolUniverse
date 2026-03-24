import json
from typing import Any, Dict
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from tooluniverse.tool_registry import register_tool


def _http_get(
    url: str,
    headers: Dict[str, str] | None = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    req = Request(url, headers=headers or {})
    with urlopen(req, timeout=timeout) as resp:
        data = resp.read()
        try:
            return json.loads(data.decode("utf-8", errors="ignore"))
        except Exception:
            return {"raw": data.decode("utf-8", errors="ignore")}


def _http_post(
    url: str,
    payload: Dict[str, Any],
    headers: Dict[str, str] | None = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    """POST request helper for GDC API."""
    headers = headers or {}
    headers["Content-Type"] = "application/json"
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, headers=headers, method="POST")
    with urlopen(req, timeout=timeout) as resp:
        response_data = resp.read()
        try:
            return json.loads(response_data.decode("utf-8", errors="ignore"))
        except Exception:
            return {"raw": response_data.decode("utf-8", errors="ignore")}


@register_tool(
    "GDCCasesTool",
    config={
        "name": "GDC_search_cases",
        "type": "GDCCasesTool",
        "description": "Search NCI GDC cases via /cases",
        "parameter": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "GDC project identifier (e.g., 'TCGA-BRCA')",
                },
                "size": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Number of results (1–100)",
                },
                "offset": {
                    "type": "integer",
                    "default": 0,
                    "minimum": 0,
                    "description": "Offset for pagination (0-based)",
                },
            },
        },
        "settings": {"base_url": "https://api.gdc.cancer.gov", "timeout": 30},
    },
)
class GDCCasesTool:
    def __init__(self, tool_config=None):
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]):
        base = self.tool_config.get("settings", {}).get(
            "base_url", "https://api.gdc.cancer.gov"
        )
        timeout = int(self.tool_config.get("settings", {}).get("timeout", 30))

        query: Dict[str, Any] = {}
        if arguments.get("project_id"):
            # Build filters JSON for project_id
            filters = {
                "op": "=",
                "content": {
                    "field": "project.project_id",
                    "value": [arguments["project_id"]],
                },
            }
            query["filters"] = json.dumps(filters)
        if arguments.get("size") is not None:
            query["size"] = int(arguments["size"])
        if arguments.get("offset") is not None:
            query["from"] = int(arguments["offset"])

        url = f"{base}/cases?{urlencode(query)}"
        try:
            data = _http_get(
                url, headers={"Accept": "application/json"}, timeout=timeout
            )
            return {
                "status": "success",
                "source": "GDC",
                "endpoint": "cases",
                "query": query,
                "data": data,
                "success": True,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "source": "GDC",
                "endpoint": "cases",
                "success": False,
            }


@register_tool(
    "GDCFilesTool",
    config={
        "name": "GDC_list_files",
        "type": "GDCFilesTool",
        "description": "List NCI GDC files via /files with optional data_type filter",
        "parameter": {
            "type": "object",
            "properties": {
                "data_type": {
                    "type": "string",
                    "description": "Data type filter (e.g., 'Gene Expression Quantification')",
                },
                "size": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Number of results (1–100)",
                },
                "offset": {
                    "type": "integer",
                    "default": 0,
                    "minimum": 0,
                    "description": "Offset for pagination (0-based)",
                },
            },
        },
        "settings": {"base_url": "https://api.gdc.cancer.gov", "timeout": 30},
    },
)
class GDCFilesTool:
    def __init__(self, tool_config=None):
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]):
        base = self.tool_config.get("settings", {}).get(
            "base_url", "https://api.gdc.cancer.gov"
        )
        timeout = int(self.tool_config.get("settings", {}).get("timeout", 30))

        query: Dict[str, Any] = {}
        if arguments.get("data_type"):
            filters = {
                "op": "=",
                "content": {
                    "field": "files.data_type",
                    "value": [arguments["data_type"]],
                },
            }
            query["filters"] = json.dumps(filters)
        if arguments.get("size") is not None:
            query["size"] = int(arguments["size"])
        if arguments.get("offset") is not None:
            query["from"] = int(arguments["offset"])

        url = f"{base}/files?{urlencode(query)}"
        try:
            data = _http_get(
                url, headers={"Accept": "application/json"}, timeout=timeout
            )
            return {
                "status": "success",
                "source": "GDC",
                "endpoint": "files",
                "query": query,
                "data": data,
                "success": True,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "source": "GDC",
                "endpoint": "files",
                "success": False,
            }


@register_tool(
    "GDCProjectsTool",
    config={
        "name": "GDC_list_projects",
        "type": "GDCProjectsTool",
        "description": "List GDC projects (TCGA, TARGET, etc.) with summary statistics",
        "parameter": {
            "type": "object",
            "properties": {
                "program": {
                    "type": "string",
                    "description": "Filter by program (e.g., 'TCGA', 'TARGET')",
                },
                "size": {
                    "type": "integer",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Number of results (1–100)",
                },
            },
        },
        "settings": {"base_url": "https://api.gdc.cancer.gov", "timeout": 30},
    },
)
class GDCProjectsTool:
    """List GDC projects including TCGA and TARGET cohorts."""

    def __init__(self, tool_config=None):
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]):
        base = self.tool_config.get("settings", {}).get(
            "base_url", "https://api.gdc.cancer.gov"
        )
        timeout = int(self.tool_config.get("settings", {}).get("timeout", 30))

        query: Dict[str, Any] = {
            "fields": "project_id,name,primary_site,disease_type,program.name,summary.case_count,summary.file_count",
        }

        if arguments.get("program"):
            filters = {
                "op": "=",
                "content": {
                    "field": "program.name",
                    "value": [arguments["program"]],
                },
            }
            query["filters"] = json.dumps(filters)

        if arguments.get("size") is not None:
            query["size"] = int(arguments["size"])

        url = f"{base}/projects?{urlencode(query)}"
        try:
            data = _http_get(
                url, headers={"Accept": "application/json"}, timeout=timeout
            )
            return {
                "status": "success",
                "source": "GDC",
                "endpoint": "projects",
                "data": data,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "source": "GDC",
                "endpoint": "projects",
            }


@register_tool(
    "GDCSSMTool",
    config={
        "name": "GDC_get_ssm_by_gene",
        "type": "GDCSSMTool",
        "description": "Get somatic mutations (SSMs) for a gene across TCGA/GDC projects",
        "parameter": {
            "type": "object",
            "properties": {
                "gene_symbol": {
                    "type": "string",
                    "description": "Gene symbol (e.g., 'TP53', 'EGFR', 'BRAF')",
                },
                "project_id": {
                    "type": "string",
                    "description": "Optional: Filter by project (e.g., 'TCGA-BRCA')",
                },
                "size": {
                    "type": "integer",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Number of results (1–100)",
                },
            },
            "required": ["gene_symbol"],
        },
        "settings": {"base_url": "https://api.gdc.cancer.gov", "timeout": 30},
    },
)
class GDCSSMTool:
    """Query somatic mutations from GDC/TCGA."""

    def __init__(self, tool_config=None):
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]):
        base = self.tool_config.get("settings", {}).get(
            "base_url", "https://api.gdc.cancer.gov"
        )
        timeout = int(self.tool_config.get("settings", {}).get("timeout", 30))

        gene_symbol = arguments.get("gene_symbol")
        if not gene_symbol:
            return {"status": "error", "error": "gene_symbol parameter is required"}

        # Build filters
        filter_content = [
            {
                "op": "in",
                "content": {
                    "field": "consequence.transcript.gene.symbol",
                    "value": [gene_symbol],
                },
            }
        ]

        if arguments.get("project_id"):
            filter_content.append(
                {
                    "op": "=",
                    "content": {
                        "field": "cases.project.project_id",
                        "value": [arguments["project_id"]],
                    },
                }
            )

        filters = {"op": "and", "content": filter_content}

        query = {
            "filters": json.dumps(filters),
            "fields": "ssm_id,genomic_dna_change,mutation_type,consequence.transcript.gene.symbol,consequence.transcript.aa_change,consequence.transcript.consequence_type",
            "size": arguments.get("size", 20),
        }

        url = f"{base}/ssms?{urlencode(query)}"
        try:
            data = _http_get(
                url, headers={"Accept": "application/json"}, timeout=timeout
            )
            return {
                "status": "success",
                "source": "GDC",
                "endpoint": "ssms",
                "gene": gene_symbol,
                "data": data,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "source": "GDC",
                "endpoint": "ssms",
            }


@register_tool(
    "GDCGeneExpressionTool",
    config={
        "name": "GDC_get_gene_expression",
        "type": "GDCGeneExpressionTool",
        "description": "Query gene expression data availability from GDC/TCGA",
        "parameter": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "GDC project (e.g., 'TCGA-BRCA', 'TCGA-LUAD')",
                },
                "gene_id": {
                    "type": "string",
                    "description": "Ensembl gene ID (e.g., 'ENSG00000141510' for TP53)",
                },
                "size": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Number of results",
                },
            },
            "required": ["project_id"],
        },
        "settings": {"base_url": "https://api.gdc.cancer.gov", "timeout": 30},
    },
)
class GDCGeneExpressionTool:
    """Query gene expression files from GDC."""

    def __init__(self, tool_config=None):
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]):
        base = self.tool_config.get("settings", {}).get(
            "base_url", "https://api.gdc.cancer.gov"
        )
        timeout = int(self.tool_config.get("settings", {}).get("timeout", 30))

        project_id = arguments.get("project_id")
        if not project_id:
            return {"status": "error", "error": "project_id parameter is required"}

        # Build filters for gene expression files
        filters = {
            "op": "and",
            "content": [
                {
                    "op": "=",
                    "content": {
                        "field": "cases.project.project_id",
                        "value": [project_id],
                    },
                },
                {
                    "op": "=",
                    "content": {
                        "field": "data_type",
                        "value": ["Gene Expression Quantification"],
                    },
                },
                {
                    "op": "=",
                    "content": {
                        "field": "experimental_strategy",
                        "value": ["RNA-Seq"],
                    },
                },
            ],
        }

        query = {
            "filters": json.dumps(filters),
            "fields": "file_id,file_name,data_type,experimental_strategy,workflow_type,cases.case_id,cases.submitter_id",
            "size": arguments.get("size", 10),
        }

        url = f"{base}/files?{urlencode(query)}"
        try:
            data = _http_get(
                url, headers={"Accept": "application/json"}, timeout=timeout
            )
            return {
                "status": "success",
                "source": "GDC",
                "endpoint": "gene_expression",
                "project": project_id,
                "data": data,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "source": "GDC",
            }


@register_tool(
    "GDCCNVTool",
    config={
        "name": "GDC_get_cnv_data",
        "type": "GDCCNVTool",
        "description": "Query copy number variation (CNV) data from GDC/TCGA",
        "parameter": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "GDC project (e.g., 'TCGA-BRCA')",
                },
                "gene_symbol": {
                    "type": "string",
                    "description": "Optional: Gene symbol to filter CNVs",
                },
                "size": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Number of results",
                },
            },
            "required": ["project_id"],
        },
        "settings": {"base_url": "https://api.gdc.cancer.gov", "timeout": 30},
    },
)
class GDCCNVTool:
    """Query copy number variation data from GDC."""

    def __init__(self, tool_config=None):
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]):
        base = self.tool_config.get("settings", {}).get(
            "base_url", "https://api.gdc.cancer.gov"
        )
        timeout = int(self.tool_config.get("settings", {}).get("timeout", 30))

        project_id = arguments.get("project_id")
        if not project_id:
            return {"status": "error", "error": "project_id parameter is required"}

        # Build filters for CNV files
        filters = {
            "op": "and",
            "content": [
                {
                    "op": "=",
                    "content": {
                        "field": "cases.project.project_id",
                        "value": [project_id],
                    },
                },
                {
                    "op": "in",
                    "content": {
                        "field": "data_type",
                        "value": ["Copy Number Segment", "Gene Level Copy Number"],
                    },
                },
            ],
        }

        query = {
            "filters": json.dumps(filters),
            "fields": "file_id,file_name,data_type,experimental_strategy,workflow_type,cases.case_id",
            "size": arguments.get("size", 10),
        }

        url = f"{base}/files?{urlencode(query)}"
        try:
            data = _http_get(
                url, headers={"Accept": "application/json"}, timeout=timeout
            )
            return {
                "status": "success",
                "source": "GDC",
                "endpoint": "cnv",
                "project": project_id,
                "data": data,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "source": "GDC",
            }


@register_tool(
    "GDCMutationFrequencyTool",
    config={
        "name": "GDC_get_mutation_frequency",
        "type": "GDCMutationFrequencyTool",
        "description": (
            "Get pan-cancer mutation frequency statistics for a gene across all TCGA projects. "
            "Returns overall and per-project mutation rates. Note: this tool is pan-cancer only "
            "and does not support filtering by cancer type."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "gene_symbol": {
                    "type": "string",
                    "description": "Gene symbol (e.g., 'TP53', 'KRAS')",
                },
                "gene": {
                    "type": "string",
                    "description": "Gene symbol alias — alternative to gene_symbol",
                },
            },
            "required": [],
        },
        "settings": {"base_url": "https://api.gdc.cancer.gov", "timeout": 30},
    },
)
class GDCMutationFrequencyTool:
    """Get mutation frequency for a gene across cancer types."""

    def __init__(self, tool_config=None):
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]):
        base = self.tool_config.get("settings", {}).get(
            "base_url", "https://api.gdc.cancer.gov"
        )
        timeout = int(self.tool_config.get("settings", {}).get("timeout", 30))

        gene_symbol = arguments.get("gene_symbol") or arguments.get("gene")
        if not gene_symbol:
            return {"status": "error", "error": "gene_symbol parameter is required"}

        # Step 1: Get gene metadata
        gene_filters = json.dumps(
            {"op": "=", "content": {"field": "symbol", "value": [gene_symbol]}}
        )
        gene_url = f"{base}/genes?{urlencode({'filters': gene_filters, 'fields': 'symbol,name,gene_id,biotype,description,is_cancer_gene_census'})}"

        gene_info = {}
        try:
            gene_data = _http_get(
                gene_url, headers={"Accept": "application/json"}, timeout=timeout
            )
            hits = gene_data.get("data", {}).get("hits", [])
            if hits:
                gene_info = hits[0]
        except Exception:
            pass

        # Step 2: Get SSM occurrence count via /ssm_occurrences with gene filter + project facet
        # Feature-81A-003: /ssm_occurrences requires the nested "ssm." prefix;
        # /ssms uses "consequence.transcript.gene.symbol" directly.
        ssm_filters = json.dumps(
            {
                "op": "in",
                "content": {
                    "field": "ssm.consequence.transcript.gene.symbol",
                    "value": [gene_symbol],
                },
            }
        )
        # Feature-83A-004: /ssm_occurrences does not support facets on
        # cases.project.project_id (returns warnings and empty aggregations).
        # Use size=0 for a count-only query.
        ssm_query = {"filters": ssm_filters, "size": 0}
        ssm_url = f"{base}/ssm_occurrences?{urlencode(ssm_query)}"

        try:
            ssm_data = _http_get(
                ssm_url, headers={"Accept": "application/json"}, timeout=timeout
            )
            pagination = ssm_data.get("data", {}).get("pagination", {})
            total_ssm_occurrences = pagination.get("total", 0)

            return {
                "status": "success",
                "source": "GDC",
                "gene": gene_symbol,
                "data": {
                    "gene_info": gene_info,
                    "total_ssm_occurrences": total_ssm_occurrences,
                    "is_cancer_gene_census": gene_info.get(
                        "is_cancer_gene_census", None
                    ),
                },
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "source": "GDC",
            }


@register_tool(
    "GDCClinicalDataTool",
    config={
        "name": "GDC_get_clinical_data",
        "type": "GDCClinicalDataTool",
        "description": (
            "Get detailed clinical data for cancer cases from NCI GDC/TCGA. "
            "Returns demographics (gender, race, vital_status, age_at_index), "
            "diagnoses (primary_diagnosis, tumor_stage, age_at_diagnosis, days_to_last_follow_up), "
            "and treatments (therapeutic_agents, treatment_type). "
            "Filter by project, primary_site, disease_type, or vital_status."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "GDC project identifier (e.g., 'TCGA-BRCA', 'TCGA-LUAD', 'TARGET-AML')",
                },
                "primary_site": {
                    "type": "string",
                    "description": "Primary anatomical site (e.g., 'Breast', 'Lung', 'Brain')",
                },
                "disease_type": {
                    "type": "string",
                    "description": "Disease type filter (e.g., 'Ductal and Lobular Neoplasms')",
                },
                "vital_status": {
                    "type": "string",
                    "description": "Vital status filter: 'Alive' or 'Dead'",
                    "enum": ["Alive", "Dead"],
                },
                "gender": {
                    "type": "string",
                    "description": "Gender filter: 'female' or 'male'",
                    "enum": ["female", "male"],
                },
                "size": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Number of cases to return (1-100)",
                },
                "offset": {
                    "type": "integer",
                    "default": 0,
                    "minimum": 0,
                    "description": "Pagination offset (0-based)",
                },
            },
        },
        "settings": {"base_url": "https://api.gdc.cancer.gov", "timeout": 30},
    },
)
class GDCClinicalDataTool:
    """Get detailed clinical data for GDC/TCGA cancer cases."""

    _CLINICAL_FIELDS = ",".join(
        [
            "case_id",
            "submitter_id",
            "project.project_id",
            "project.name",
            "primary_site",
            "disease_type",
        ]
    )

    _FILTER_MAP = {
        "project_id": "project.project_id",
        "primary_site": "primary_site",
        "disease_type": "disease_type",
        "vital_status": "demographic.vital_status",
        "gender": "demographic.gender",
    }

    def __init__(self, tool_config=None):
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]):
        base = self.tool_config.get("settings", {}).get(
            "base_url", "https://api.gdc.cancer.gov"
        )
        timeout = int(self.tool_config.get("settings", {}).get("timeout", 30))

        conditions = []
        for param, field in self._FILTER_MAP.items():
            value = arguments.get(param)
            if value:
                conditions.append(
                    {"op": "=", "content": {"field": field, "value": [value]}}
                )

        query: Dict[str, Any] = {
            "fields": self._CLINICAL_FIELDS,
            "expand": "diagnoses,demographic,treatments",
            "size": min(
                int(arguments.get("size") or arguments.get("limit") or 10), 100
            ),
            "from": int(arguments.get("offset", 0)),
        }

        if conditions:
            if len(conditions) == 1:
                query["filters"] = json.dumps(conditions[0])
            else:
                query["filters"] = json.dumps({"op": "and", "content": conditions})

        url = f"{base}/cases?{urlencode(query)}"
        try:
            raw = _http_get(
                url, headers={"Accept": "application/json"}, timeout=timeout
            )
            hits = raw.get("data", {}).get("hits", [])
            pagination = raw.get("data", {}).get("pagination", {})

            cases = []
            for hit in hits:
                demo = hit.get("demographic", {}) or {}
                diagnoses_raw = hit.get("diagnoses", []) or []
                treatments_raw = hit.get("treatments", []) or []
                project = hit.get("project", {}) or {}

                case_record = {
                    "case_id": hit.get("case_id"),
                    "submitter_id": hit.get("submitter_id"),
                    "project_id": project.get("project_id"),
                    "project_name": project.get("name"),
                    "primary_site": hit.get("primary_site"),
                    "disease_type": hit.get("disease_type"),
                    "gender": demo.get("gender"),
                    "race": demo.get("race"),
                    "ethnicity": demo.get("ethnicity"),
                    "vital_status": demo.get("vital_status"),
                    "age_at_index": demo.get("age_at_index"),
                    "days_to_birth": demo.get("days_to_birth"),
                    "days_to_death": demo.get("days_to_death"),
                    "year_of_death": demo.get("year_of_death"),
                    "diagnoses": [
                        {
                            "primary_diagnosis": dx.get("primary_diagnosis"),
                            "age_at_diagnosis": dx.get("age_at_diagnosis"),
                            "tumor_stage": dx.get("ajcc_pathologic_stage"),
                            "tumor_grade": dx.get("tumor_grade"),
                            "morphology": dx.get("morphology"),
                            "tissue_or_organ_of_origin": dx.get(
                                "tissue_or_organ_of_origin"
                            ),
                            "days_to_last_follow_up": dx.get("days_to_last_follow_up"),
                            "classification_of_tumor": dx.get(
                                "classification_of_tumor"
                            ),
                            "icd_10_code": dx.get("icd_10_code"),
                            "year_of_diagnosis": dx.get("year_of_diagnosis"),
                        }
                        for dx in diagnoses_raw
                    ],
                    "treatments": [
                        {
                            "treatment_type": tx.get("treatment_type"),
                            "therapeutic_agents": tx.get("therapeutic_agents"),
                            "treatment_or_therapy": tx.get("treatment_or_therapy"),
                        }
                        for tx in treatments_raw
                    ],
                }
                cases.append(case_record)

            return {
                "status": "success",
                "data": {
                    "cases": cases,
                    "pagination": {
                        "total": pagination.get("total", 0),
                        "count": pagination.get("count", 0),
                        "page": pagination.get("page", 0),
                        "pages": pagination.get("pages", 0),
                    },
                },
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


@register_tool(
    "GDCSurvivalTool",
    config={
        "name": "GDC_get_survival",
        "type": "GDCSurvivalTool",
        "description": (
            "Get Kaplan-Meier survival data for a GDC/TCGA cancer cohort. "
            "Returns time-to-event data with censoring status and survival estimates "
            "for each patient. Filter by project and optionally by gene mutation status. "
            "Use for overall survival analysis of TCGA cancer types."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "GDC project identifier (e.g., 'TCGA-BRCA', 'TCGA-LUAD', 'TCGA-GBM')",
                },
                "gene_symbol": {
                    "type": "string",
                    "description": "Optional: gene symbol to filter cases with mutations in this gene (e.g., 'TP53', 'KRAS')",
                },
            },
            "required": ["project_id"],
        },
        "settings": {"base_url": "https://api.gdc.cancer.gov", "timeout": 30},
    },
)
class GDCSurvivalTool:
    """Get Kaplan-Meier survival data for GDC/TCGA cohorts."""

    def __init__(self, tool_config=None):
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]):
        base = self.tool_config.get("settings", {}).get(
            "base_url", "https://api.gdc.cancer.gov"
        )
        timeout = int(self.tool_config.get("settings", {}).get("timeout", 30))

        project_id = arguments.get("project_id")
        if not project_id:
            return {"status": "error", "error": "project_id parameter is required"}

        # Build filter for project
        conditions = [
            {
                "op": "=",
                "content": {
                    "field": "project.project_id",
                    "value": project_id,
                },
            }
        ]

        gene_symbol = arguments.get("gene_symbol")
        if gene_symbol:
            conditions.append(
                {
                    "op": "in",
                    "content": {
                        "field": "gene.symbol",
                        "value": [gene_symbol],
                    },
                }
            )

        if len(conditions) == 1:
            filters = conditions[0]
        else:
            filters = {"op": "and", "content": conditions}

        query = {"filters": json.dumps(filters)}
        url = f"{base}/analysis/survival?{urlencode(query)}"

        try:
            raw = _http_get(
                url, headers={"Accept": "application/json"}, timeout=timeout
            )
            results = raw.get("results", [])
            if not results:
                return {
                    "status": "success",
                    "data": {
                        "project_id": project_id,
                        "gene_symbol": gene_symbol,
                        "total_donors": 0,
                        "donors": [],
                    },
                }

            donors = results[0].get("donors", [])
            # Summarize survival statistics
            alive_count = sum(1 for d in donors if d.get("censored"))
            dead_count = len(donors) - alive_count
            times = [d.get("time", 0) for d in donors]
            max_time = max(times) if times else 0
            median_time = sorted(times)[len(times) // 2] if times else 0

            return {
                "status": "success",
                "data": {
                    "project_id": project_id,
                    "gene_symbol": gene_symbol,
                    "total_donors": len(donors),
                    "alive_censored": alive_count,
                    "deceased": dead_count,
                    "max_follow_up_days": max_time,
                    "median_follow_up_days": median_time,
                    "donors": donors[:50],
                    "note": (
                        f"Showing first 50 of {len(donors)} donors. "
                        "Each donor has: time (days), censored (true=alive), survivalEstimate (KM estimate)."
                        if len(donors) > 50
                        else None
                    ),
                },
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
