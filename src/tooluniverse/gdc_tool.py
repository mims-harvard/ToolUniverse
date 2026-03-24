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
                    "field": "projects.project_id",
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
        "description": "Get mutation frequency statistics for a gene across TCGA projects",
        "parameter": {
            "type": "object",
            "properties": {
                "gene_symbol": {
                    "type": "string",
                    "description": "Gene symbol (e.g., 'TP53', 'KRAS')",
                },
            },
            "required": ["gene_symbol"],
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

        gene_symbol = arguments.get("gene_symbol")
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
