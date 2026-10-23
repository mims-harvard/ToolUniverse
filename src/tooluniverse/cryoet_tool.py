"""
CryoET Data Portal Tool

Provides access to the CZ BioHub CryoET Data Portal via GraphQL API.
No authentication required. Endpoint: https://graphql.cryoetdataportal.czscience.com/graphql
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

GRAPHQL_URL = "https://graphql.cryoetdataportal.czscience.com/graphql"


def _gql(query: str, variables: dict = None) -> Dict[str, Any]:
    """Execute a GraphQL query and return parsed JSON."""
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    resp = requests.post(
        GRAPHQL_URL,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


@register_tool("CryoETTool")
class CryoETTool(BaseTool):
    """
    CryoET Data Portal tool for browsing cryo-electron tomography datasets,
    runs, tomograms, and annotations from the CZ BioHub portal.
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments."""
        try:
            # Fix-R39A-1: "operation" is optional in the schema (each config
            # exposes exactly one valid value via enum+default), so a caller
            # who omits it must still resolve to that tool instance's own
            # operation -- the old bare "" fallback matched no dispatch
            # branch below and would silently mis-route every one of these
            # 7 tools.
            operation = arguments.get("operation") or self.get_schema_const_operation()

            if operation.startswith("list_"):
                props = self.tool_config.get("parameter", {}).get("properties", {})
                if "limit" in props:
                    limit = arguments.get("limit", props["limit"].get("default", 10))
                    maximum = props["limit"].get("maximum", 100)
                    if (
                        isinstance(limit, bool)
                        or not isinstance(limit, int)
                        or not 1 <= limit <= maximum
                    ):
                        return {
                            "status": "error",
                            "error": f"limit must be an integer between 1 and {maximum}",
                            "parameter": "limit",
                        }
                    offset = arguments.get("offset", 0)
                    if (
                        isinstance(offset, bool)
                        or not isinstance(offset, int)
                        or offset < 0
                    ):
                        return {
                            "status": "error",
                            "error": "offset must be a non-negative integer",
                            "parameter": "offset",
                        }
                    arguments = dict(arguments)
                    arguments["limit"] = limit
                    arguments["offset"] = offset

            if operation == "list_datasets":
                return self._list_datasets(arguments)
            elif operation == "get_dataset":
                return self._get_dataset(arguments)
            elif operation == "list_runs":
                return self._list_runs(arguments)
            elif operation == "list_tomograms":
                return self._list_tomograms(arguments)
            elif operation == "list_annotations":
                return self._list_annotations(arguments)
            elif operation == "list_tiltseries":
                return self._list_tiltseries(arguments)
            elif operation == "list_depositions":
                return self._list_depositions(arguments)
            else:
                return {
                    "status": "error",
                    "error": f"Unknown operation: {operation!r}. Valid operations: "
                    "list_datasets, get_dataset, list_runs, list_tomograms, "
                    "list_annotations, list_tiltseries, list_depositions",
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @staticmethod
    def _page_result(records, key, limit, offset, **context):
        """Return one evidence-based page using a limit+1 GraphQL lookahead."""
        records = records if isinstance(records, list) else []
        has_more = len(records) > limit
        page = records[:limit]
        returned = len(page)
        terminal_position_known = not has_more and (offset == 0 or returned > 0)
        return {
            "status": "success",
            "data": {**context, "count": returned, key: page},
            "metadata": {
                "returned": returned,
                "count_semantics": "records_on_current_page_not_total_results",
                "total_results": offset + returned if terminal_position_known else None,
                "total_results_is_exact": terminal_position_known,
                "matches_lower_bound": (
                    offset + returned + (1 if has_more else 0)
                    if returned or offset == 0
                    else None
                ),
                "total_results_upper_bound": (
                    offset if not has_more and not returned and offset > 0 else None
                ),
                "limit": limit,
                "offset": offset,
                "has_more": has_more,
                "next_offset": offset + returned if has_more else None,
                "truncated": offset > 0 or has_more,
                "result_set_complete": bool(offset == 0 and not has_more),
                "pagination_scope": "cryoet_graphql_limit_offset_lookahead",
            },
        }

    # ------------------------------------------------------------------ #
    # list_datasets
    # ------------------------------------------------------------------ #
    def _list_datasets(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List/search CryoET datasets with optional filters."""
        try:
            organism = arguments.get("organism_name")
            tissue = arguments.get("tissue_name")
            limit = arguments.get("limit", 10)
            offset = arguments.get("offset", 0)

            where_parts = []
            if organism:
                where_parts.append(f'organismName: {{_ilike: "%{organism}%"}}')
            if tissue:
                where_parts.append(f'tissueName: {{_ilike: "%{tissue}%"}}')

            where_clause = "{" + ", ".join(where_parts) + "}" if where_parts else "null"
            where_arg = f"where: {where_clause}, " if where_parts else ""

            query = f"""
            {{
              datasets(
                {where_arg}limitOffset: {{limit: {limit + 1}, offset: {offset}}}
              ) {{
                id
                title
                description
                organismName
                tissueName
                cellName
                sampleType
                depositionDate
                releaseDate
                relatedDatabaseEntries
                datasetPublications
                s3Prefix
                httpsPrefix
              }}
            }}
            """
            result = _gql(query)
            if "errors" in result:
                return {
                    "status": "error",
                    "error": str(result["errors"]),
                }
            datasets = result.get("data", {}).get("datasets", [])
            return self._page_result(datasets, "datasets", limit, offset)
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ------------------------------------------------------------------ #
    # get_dataset
    # ------------------------------------------------------------------ #
    def _get_dataset(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get full details for a specific dataset by numeric ID."""
        try:
            dataset_id = arguments.get("dataset_id")
            if dataset_id is None:
                return {
                    "status": "error",
                    "error": "dataset_id is required for get_dataset operation",
                }
            dataset_id = int(dataset_id)

            query = f"""
            {{
              datasets(where: {{id: {{_eq: {dataset_id}}}}}) {{
                id
                title
                description
                organismName
                organismTaxid
                tissueName
                tissueId
                cellName
                cellTypeId
                cellStrainName
                sampleType
                samplePreparation
                gridPreparation
                otherSetup
                depositionDate
                releaseDate
                lastModifiedDate
                datasetPublications
                relatedDatabaseEntries
                keyPhotoUrl
                s3Prefix
                httpsPrefix
                fileSize
              }}
            }}
            """
            result = _gql(query)
            if "errors" in result:
                return {"status": "error", "error": str(result["errors"])}
            datasets = result.get("data", {}).get("datasets", [])
            if not datasets:
                return {
                    "status": "error",
                    "error": f"Dataset {dataset_id} not found",
                }
            return {"status": "success", "data": {"dataset": datasets[0]}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ------------------------------------------------------------------ #
    # list_runs
    # ------------------------------------------------------------------ #
    def _list_runs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List experimental runs in a dataset."""
        try:
            dataset_id = arguments.get("dataset_id")
            if dataset_id is None:
                return {
                    "status": "error",
                    "error": "dataset_id is required for list_runs operation",
                }
            dataset_id = int(dataset_id)
            limit = arguments.get("limit", 20)
            offset = arguments.get("offset", 0)

            query = f"""
            {{
              runs(
                where: {{datasetId: {{_eq: {dataset_id}}}}},
                limitOffset: {{limit: {limit + 1}, offset: {offset}}}
              ) {{
                id
                name
                datasetId
                s3Prefix
                httpsPrefix
              }}
            }}
            """
            result = _gql(query)
            if "errors" in result:
                return {"status": "error", "error": str(result["errors"])}
            runs = result.get("data", {}).get("runs", [])
            return self._page_result(runs, "runs", limit, offset, dataset_id=dataset_id)
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ------------------------------------------------------------------ #
    # list_tomograms
    # ------------------------------------------------------------------ #
    def _list_tomograms(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List tomograms with voxel spacing and reconstruction info."""
        try:
            run_id = arguments.get("run_id")
            if run_id is None:
                return {
                    "status": "error",
                    "error": "run_id is required for list_tomograms operation",
                }
            run_id = int(run_id)
            limit = arguments.get("limit", 10)
            offset = arguments.get("offset", 0)

            query = f"""
            {{
              tomograms(
                where: {{runId: {{_eq: {run_id}}}}},
                limitOffset: {{limit: {limit + 1}, offset: {offset}}}
              ) {{
                id
                name
                runId
                voxelSpacing
                sizeX
                sizeY
                sizeZ
                reconstructionMethod
                processing
                processingSoftware
                reconstructionSoftware
                isPortalStandard
                isAuthorSubmitted
                isVisualizationDefault
                ctfCorrected
                s3OmezarrDir
                httpsMrcFile
                s3MrcFile
                depositionDate
                releaseDate
              }}
            }}
            """
            result = _gql(query)
            if "errors" in result:
                return {"status": "error", "error": str(result["errors"])}
            tomograms = result.get("data", {}).get("tomograms", [])
            return self._page_result(
                tomograms, "tomograms", limit, offset, run_id=run_id
            )
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ------------------------------------------------------------------ #
    # list_annotations
    # ------------------------------------------------------------------ #
    def _list_annotations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List annotations (segmentations) for a run."""
        try:
            run_id = arguments.get("run_id")
            if run_id is None:
                return {
                    "status": "error",
                    "error": "run_id is required for list_annotations operation",
                }
            run_id = int(run_id)
            limit = arguments.get("limit", 20)
            offset = arguments.get("offset", 0)
            curator_only = arguments.get("curator_recommended_only", False)

            where_parts = [f"runId: {{_eq: {run_id}}}"]
            if curator_only:
                where_parts.append("isCuratorRecommended: {_eq: true}")

            where_clause = "{" + ", ".join(where_parts) + "}"

            query = f"""
            {{
              annotations(
                where: {where_clause},
                limitOffset: {{limit: {limit + 1}, offset: {offset}}}
              ) {{
                id
                objectName
                objectId
                objectDescription
                objectState
                objectCount
                annotationMethod
                annotationSoftware
                groundTruthStatus
                isCuratorRecommended
                methodType
                depositionDate
                releaseDate
                annotationPublication
                s3MetadataPath
                httpsMetadataPath
              }}
            }}
            """
            result = _gql(query)
            if "errors" in result:
                return {"status": "error", "error": str(result["errors"])}
            annotations = result.get("data", {}).get("annotations", [])
            return self._page_result(
                annotations, "annotations", limit, offset, run_id=run_id
            )
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ------------------------------------------------------------------ #
    # list_tiltseries
    # ------------------------------------------------------------------ #
    def _list_tiltseries(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List tilt-series raw acquisition metadata, optionally filtered by run."""
        try:
            run_id = arguments.get("run_id")
            limit = arguments.get("limit", 10)
            offset = arguments.get("offset", 0)

            where_arg = ""
            if run_id is not None:
                where_arg = f"where: {{runId: {{_eq: {int(run_id)}}}}}, "

            query = f"""
            {{
              tiltseries(
                {where_arg}limitOffset: {{limit: {limit + 1}, offset: {offset}}}
              ) {{
                id
                runId
                microscopeManufacturer
                microscopeModel
                accelerationVoltage
                sphericalAberrationConstant
                tiltMin
                tiltMax
                tiltStep
                tiltAxis
                totalFlux
                cameraModel
                cameraManufacturer
                dataAcquisitionSoftware
                binningFromFrames
                pixelSpacing
                isAligned
                httpsMrcFile
                s3MrcFile
                httpsOmezarrDir
              }}
            }}
            """
            result = _gql(query)
            if "errors" in result:
                return {"status": "error", "error": str(result["errors"])}
            tiltseries = result.get("data", {}).get("tiltseries", [])
            return self._page_result(
                tiltseries,
                "tiltseries",
                limit,
                offset,
                run_id=int(run_id) if run_id is not None else None,
            )
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ------------------------------------------------------------------ #
    # list_depositions
    # ------------------------------------------------------------------ #
    def _list_depositions(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Browse top-level depositions, optionally filtered by deposition id."""
        try:
            deposition_id = arguments.get("deposition_id")
            limit = arguments.get("limit", 10)
            offset = arguments.get("offset", 0)

            where_arg = ""
            if deposition_id is not None:
                where_arg = f"where: {{id: {{_eq: {int(deposition_id)}}}}}, "

            query = f"""
            {{
              depositions(
                {where_arg}limitOffset: {{limit: {limit + 1}, offset: {offset}}}
              ) {{
                id
                title
                description
                depositionDate
                releaseDate
                lastModifiedDate
                relatedDatabaseEntries
                depositionPublications
                keyPhotoUrl
              }}
            }}
            """
            result = _gql(query)
            if "errors" in result:
                return {"status": "error", "error": str(result["errors"])}
            depositions = result.get("data", {}).get("depositions", [])
            return self._page_result(depositions, "depositions", limit, offset)
        except Exception as e:
            return {"status": "error", "error": str(e)}
