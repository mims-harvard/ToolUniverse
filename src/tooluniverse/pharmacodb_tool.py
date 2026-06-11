"""
PharmacoDB Tool - Cancer Pharmacogenomics Database

Provides access to the PharmacoDB GraphQL API for querying integrated cancer
pharmacogenomics data across multiple datasets (CCLE, GDSC1, GDSC2, CTRPv2,
PRISM, NCI60, FIMM, gCSI, GRAY, UHNBreast).

API: https://pharmacodb.ca/graphql
Authentication: None required (free public API).
"""

import requests
from typing import Dict, Any, Optional, List
from .base_tool import BaseTool
from .tool_registry import register_tool

PHARMACODB_GRAPHQL_URL = "https://pharmacodb.ca/graphql"


def _execute_graphql(
    query: str, variables: Optional[Dict] = None, timeout: int = 30
) -> Dict[str, Any]:
    """Execute a GraphQL query against PharmacoDB."""
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    try:
        response = requests.post(
            PHARMACODB_GRAPHQL_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=timeout,
        )
        if response.status_code != 200:
            return {
                "ok": False,
                "error": "PharmacoDB API returned HTTP %d" % response.status_code,
            }
        data = response.json()
        if "errors" in data:
            msgs = "; ".join(e.get("message", str(e)) for e in data["errors"])
            return {"ok": False, "error": "GraphQL error: %s" % msgs}
        return {"ok": True, "data": data.get("data", {})}
    except requests.exceptions.Timeout:
        return {"ok": False, "error": "PharmacoDB API request timed out"}
    except requests.exceptions.ConnectionError:
        return {"ok": False, "error": "Failed to connect to PharmacoDB API"}
    except Exception as e:
        return {"ok": False, "error": "Request failed: %s" % str(e)}


@register_tool("PharmacoDBTool")
class PharmacoDBTool(BaseTool):
    """
    Tool for querying the PharmacoDB cancer pharmacogenomics database.

    PharmacoDB integrates drug sensitivity data across 10 major datasets:
    CCLE, CTRPv2, FIMM, GDSC1, GDSC2, GRAY, NCI60, PRISM, UHNBreast, gCSI.

    Provides access to:
    - Compound/drug information with annotations and targets
    - Cell line information with tissue classification
    - Drug sensitivity experiments with dose-response curves
    - Pharmacological profiles (IC50, AAC, EC50, DSS scores)
    - Gene-compound biomarker associations
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a PharmacoDB query."""
        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        handlers = {
            "search": self._search,
            "get_compound": self._get_compound,
            "get_cell_line": self._get_cell_line,
            "get_experiments": self._get_experiments,
            "list_datasets": self._list_datasets,
            "get_biomarker_associations": self._get_biomarker_associations,
            "get_drug_targets": self._get_drug_targets,
            "get_molecular_profiling": self._get_molecular_profiling,
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
            return {"status": "error", "error": "PharmacoDB API request timed out"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to PharmacoDB API"}
        except Exception as e:
            return {"status": "error", "error": "Operation failed: %s" % str(e)}

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search across compounds, cell lines, tissues, and genes."""
        query_text = arguments.get("query")
        if not query_text:
            return {
                "status": "error",
                "error": "query parameter is required for search",
            }

        gql = """
        query Search($input: String!) {
            search(input: $input) {
                id
                value
                type
            }
        }
        """
        result = _execute_graphql(gql, {"input": query_text})
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        items = result["data"].get("search", [])
        return {
            "status": "success",
            "data": {
                "query": query_text,
                "results": items,
                "num_results": len(items),
            },
        }

    def _get_compound(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get compound details with annotations and targets."""
        compound_name = arguments.get("compound_name")
        compound_id = arguments.get("compound_id")

        if not compound_name and compound_id is None:
            return {
                "status": "error",
                "error": "Either compound_name or compound_id is required",
            }

        # Build GraphQL arguments
        args = []
        variables = {}
        if compound_name:
            args.append("compoundName: $compoundName")
            variables["compoundName"] = compound_name
        if compound_id is not None:
            args.append("compoundId: $compoundId")
            variables["compoundId"] = compound_id

        var_defs = []
        if "compoundName" in variables:
            var_defs.append("$compoundName: String")
        if "compoundId" in variables:
            var_defs.append("$compoundId: Int")

        gql = """
        query GetCompound(%s) {
            compound(%s) {
                compound {
                    id
                    name
                    uid
                    annotation {
                        smiles
                        inchikey
                        pubchem
                        fda_status
                        chembl
                        reactome
                    }
                    datasets {
                        name
                    }
                }
                targets {
                    target_id
                    target_name
                    genes {
                        id
                        name
                    }
                }
            }
        }
        """ % (", ".join(var_defs), ", ".join(args))

        result = _execute_graphql(gql, variables)
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        compound_data = result["data"].get("compound")
        if not compound_data:
            return {"status": "error", "error": "Compound not found"}

        return {
            "status": "success",
            "data": compound_data,
        }

    def _get_cell_line(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get cell line details including tissue, synonyms, and diseases."""
        cell_name = arguments.get("cell_name")
        cell_id = arguments.get("cell_id")

        if not cell_name and cell_id is None:
            return {
                "status": "error",
                "error": "Either cell_name or cell_id is required",
            }

        args = []
        variables = {}
        if cell_name:
            args.append("cellName: $cellName")
            variables["cellName"] = cell_name
        if cell_id is not None:
            args.append("cellId: $cellId")
            variables["cellId"] = cell_id

        var_defs = []
        if "cellName" in variables:
            var_defs.append("$cellName: String")
        if "cellId" in variables:
            var_defs.append("$cellId: Int")

        gql = """
        query GetCellLine(%s) {
            cell_line(%s) {
                id
                name
                uid
                tissue {
                    id
                    name
                }
                synonyms {
                    name
                    dataset {
                        name
                    }
                }
                diseases
                accession_id
            }
        }
        """ % (", ".join(var_defs), ", ".join(args))

        result = _execute_graphql(gql, variables)
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        cell_data = result["data"].get("cell_line")
        if not cell_data:
            return {"status": "error", "error": "Cell line not found"}

        return {
            "status": "success",
            "data": cell_data,
        }

    def _get_experiments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get drug sensitivity experiments with dose-response data and profiles."""
        compound_name = arguments.get("compound_name")
        cell_line_name = arguments.get("cell_line_name")
        dataset_name = arguments.get("dataset_name")
        per_page = arguments.get("per_page", 10)

        if not compound_name and not cell_line_name:
            return {
                "status": "error",
                "error": "At least one of compound_name or cell_line_name is required",
            }

        args = []
        variables = {}
        var_defs = []

        if compound_name:
            args.append("compoundName: $compoundName")
            variables["compoundName"] = compound_name
            var_defs.append("$compoundName: String")
        if cell_line_name:
            args.append("cellLineName: $cellLineName")
            variables["cellLineName"] = cell_line_name
            var_defs.append("$cellLineName: String")
        if per_page:
            args.append("per_page: $perPage")
            variables["perPage"] = per_page
            var_defs.append("$perPage: Int")

        gql = """
        query GetExperiments(%s) {
            experiments(%s) {
                id
                cell_line {
                    id
                    name
                }
                tissue {
                    id
                    name
                }
                compound {
                    id
                    name
                }
                dataset {
                    id
                    name
                }
                profile {
                    HS
                    Einf
                    EC50
                    AAC
                    IC50
                    DSS1
                    DSS2
                    DSS3
                }
                dose_response {
                    dose
                    response
                }
            }
        }
        """ % (", ".join(var_defs), ", ".join(args))

        result = _execute_graphql(gql, variables, timeout=60)
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        experiments = result["data"].get("experiments", [])

        # If dataset_name filter requested, apply post-filter
        if dataset_name and experiments:
            experiments = [
                e
                for e in experiments
                if e.get("dataset", {}).get("name", "").lower() == dataset_name.lower()
            ]

        return {
            "status": "success",
            "data": {
                "experiments": experiments,
                "num_experiments": len(experiments),
                "filters_applied": {
                    "compound_name": compound_name,
                    "cell_line_name": cell_line_name,
                    "dataset_name": dataset_name,
                },
            },
        }

    def _list_datasets(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List all available pharmacogenomics datasets."""
        gql = """
        query ListDatasets {
            datasets {
                id
                name
            }
        }
        """
        result = _execute_graphql(gql)
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        datasets = result["data"].get("datasets", [])
        return {
            "status": "success",
            "data": {
                "datasets": datasets,
                "num_datasets": len(datasets),
            },
        }

    def _resolve_compound_id(self, compound_name: str) -> Optional[int]:
        """Resolve a compound name to its PharmacoDB database ID."""
        gql = """
        query ResolveCompound($name: String!) {
            compound(compoundName: $name) {
                compound {
                    id
                }
            }
        }
        """
        result = _execute_graphql(gql, {"name": compound_name})
        if result["ok"]:
            comp = result["data"].get("compound", {})
            if comp and comp.get("compound"):
                return comp["compound"]["id"]
        return None

    def _get_biomarker_associations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get gene-compound biomarker associations across tissues and datasets."""
        compound_name = arguments.get("compound_name")
        compound_id = arguments.get("compound_id")
        gene_name = arguments.get("gene_name")
        tissue_name = arguments.get("tissue_name")
        mdata_type = arguments.get("mdata_type")
        per_page = arguments.get("per_page", 20)

        if not compound_name and compound_id is None:
            return {
                "status": "error",
                "error": "compound_name or compound_id is required",
            }

        # The biomarker endpoint requires compoundId (name resolution needed)
        if compound_id is None and compound_name:
            compound_id = self._resolve_compound_id(compound_name)
            if compound_id is None:
                return {
                    "status": "error",
                    "error": "Could not resolve compound name '%s' to an ID"
                    % compound_name,
                }

        args = []
        variables = {}
        var_defs = []

        args.append("compoundId: $compoundId")
        variables["compoundId"] = compound_id
        var_defs.append("$compoundId: Int")
        if gene_name:
            args.append("geneName: $geneName")
            variables["geneName"] = gene_name
            var_defs.append("$geneName: String")
        if tissue_name:
            args.append("tissueName: $tissueName")
            variables["tissueName"] = tissue_name
            var_defs.append("$tissueName: String")
        if mdata_type:
            args.append("mDataType: $mDataType")
            variables["mDataType"] = mdata_type
            var_defs.append("$mDataType: String")
        args.append("per_page: $perPage")
        variables["perPage"] = per_page
        var_defs.append("$perPage: Int")

        gql = """
        query GetBiomarkerAssociations(%s) {
            gene_compound_tissue_dataset(%s) {
                id
                gene {
                    id
                    name
                }
                compound {
                    id
                    name
                }
                tissue {
                    id
                    name
                }
                dataset {
                    id
                    name
                }
                estimate
                pvalue_analytic
                fdr_analytic
                sens_stat
                mDataType
                n
            }
        }
        """ % (", ".join(var_defs), ", ".join(args))

        result = _execute_graphql(gql, variables, timeout=60)
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        assocs = result["data"].get("gene_compound_tissue_dataset", [])
        return {
            "status": "success",
            "data": {
                "associations": assocs,
                "num_associations": len(assocs),
                "filters_applied": {
                    "compound_name": compound_name,
                    "compound_id": compound_id,
                    "gene_name": gene_name,
                    "tissue_name": tissue_name,
                    "mdata_type": mdata_type,
                },
            },
        }

    def _get_drug_targets(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Query PharmacoDB drug-target relationships.

        Supports three directions:
        - gene -> targets (single_gene_target) via gene_name/gene_id
        - compound -> targets (single_compound_target) via compound_name/compound_id
        - full cross-database drug-target table (all_compound_targets) when no
          gene/compound is given (client-side paginated by page/per_page).
        """
        gene_name = arguments.get("gene_name")
        gene_id = arguments.get("gene_id")
        compound_name = arguments.get("compound_name")
        compound_id = arguments.get("compound_id")

        # Direction 1: gene -> targets/compounds
        if gene_name or gene_id is not None:
            args = []
            variables = {}
            var_defs = []
            if gene_name:
                args.append("geneName: $geneName")
                variables["geneName"] = gene_name
                var_defs.append("$geneName: String")
            if gene_id is not None:
                args.append("geneId: $geneId")
                variables["geneId"] = gene_id
                var_defs.append("$geneId: Int")

            gql = """
            query GeneTargets(%s) {
                single_gene_target(%s) {
                    gene_id
                    gene_name
                    targets {
                        target_id
                        target_name
                    }
                }
            }
            """ % (", ".join(var_defs), ", ".join(args))

            result = _execute_graphql(gql, variables)
            if not result["ok"]:
                return {"status": "error", "error": result["error"]}
            gene_data = result["data"].get("single_gene_target")
            if not gene_data:
                return {
                    "status": "error",
                    "error": "No target data found for the requested gene",
                }
            targets = gene_data.get("targets") or []
            return {
                "status": "success",
                "data": {
                    "direction": "single_gene_target",
                    "gene_id": gene_data.get("gene_id"),
                    "gene_name": gene_data.get("gene_name"),
                    "targets": targets,
                    "num_targets": len(targets),
                },
            }

        # Direction 2: compound -> targets
        if compound_name or compound_id is not None:
            args = []
            variables = {}
            var_defs = []
            if compound_name:
                args.append("compoundName: $compoundName")
                variables["compoundName"] = compound_name
                var_defs.append("$compoundName: String")
            if compound_id is not None:
                args.append("compoundId: $compoundId")
                variables["compoundId"] = compound_id
                var_defs.append("$compoundId: Int")

            gql = """
            query CompoundTargets(%s) {
                single_compound_target(%s) {
                    compound_id
                    compound_name
                    targets {
                        target_id
                        target_name
                    }
                }
            }
            """ % (", ".join(var_defs), ", ".join(args))

            result = _execute_graphql(gql, variables)
            if not result["ok"]:
                return {"status": "error", "error": result["error"]}
            comp_data = result["data"].get("single_compound_target")
            if not comp_data:
                return {
                    "status": "error",
                    "error": "No target data found for the requested compound",
                }
            targets = comp_data.get("targets") or []
            return {
                "status": "success",
                "data": {
                    "direction": "single_compound_target",
                    "compound_id": comp_data.get("compound_id"),
                    "compound_name": comp_data.get("compound_name"),
                    "targets": targets,
                    "num_targets": len(targets),
                },
            }

        # Direction 3: full cross-database drug-target table.
        # The API ignores server-side per_page for this field (returns the full
        # table), so paginate client-side for a manageable response.
        page = arguments.get("page", 1)
        per_page = arguments.get("per_page", 20)
        try:
            page = max(1, int(page))
            per_page = max(1, min(int(per_page), 200))
        except (TypeError, ValueError):
            return {
                "status": "error",
                "error": "page and per_page must be integers",
            }

        gql = """
        query AllCompoundTargets {
            all_compound_targets {
                compound_id
                compound_name
                targets {
                    target_id
                    target_name
                }
            }
        }
        """
        result = _execute_graphql(gql, timeout=60)
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}
        all_rows = result["data"].get("all_compound_targets") or []
        total = len(all_rows)
        start = (page - 1) * per_page
        rows = all_rows[start : start + per_page]
        return {
            "status": "success",
            "data": {
                "direction": "all_compound_targets",
                "compound_targets": rows,
                "num_returned": len(rows),
                "total_available": total,
                "page": page,
                "per_page": per_page,
            },
        }

    def _get_molecular_profiling(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Per-cell-line molecular profiling inventory (which omics layers exist)."""
        cell_line_name = arguments.get("cell_line_name") or arguments.get("cell_name")
        cell_line_id = arguments.get("cell_line_id")
        if cell_line_id is None:
            cell_line_id = arguments.get("cell_id")

        if not cell_line_name and cell_line_id is None:
            return {
                "status": "error",
                "error": "Either cell_line_name or cell_line_id is required",
            }

        args = []
        variables = {}
        var_defs = []
        if cell_line_name:
            args.append("cellLineName: $cellLineName")
            variables["cellLineName"] = cell_line_name
            var_defs.append("$cellLineName: String")
        if cell_line_id is not None:
            args.append("cellLineId: $cellLineId")
            variables["cellLineId"] = cell_line_id
            var_defs.append("$cellLineId: Int")

        gql = """
        query MolecularProfiling(%s) {
            molecular_profiling(%s) {
                cell_line {
                    id
                    name
                }
                dataset {
                    id
                    name
                }
                mDataType
                num_prof
            }
        }
        """ % (", ".join(var_defs), ", ".join(args))

        result = _execute_graphql(gql, variables, timeout=60)
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        profiling = result["data"].get("molecular_profiling")
        if not profiling:
            return {
                "status": "error",
                "error": "No molecular profiling data found for the requested cell line",
            }

        return {
            "status": "success",
            "data": {
                "cell_line_name": cell_line_name,
                "cell_line_id": cell_line_id,
                "profiling": profiling,
                "num_records": len(profiling),
            },
        }
