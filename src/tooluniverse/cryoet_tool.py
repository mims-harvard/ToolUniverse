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
            operation = arguments.get("operation", "")

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
            else:
                return {
                    "status": "error",
                    "error": f"Unknown operation: {operation!r}. Valid operations: "
                    "list_datasets, get_dataset, list_runs, list_tomograms, list_annotations",
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ------------------------------------------------------------------ #
    # list_datasets
    # ------------------------------------------------------------------ #
    def _list_datasets(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List/search CryoET datasets with optional filters."""
        try:
            organism = arguments.get("organism_name")
            tissue = arguments.get("tissue_name")
            limit = int(arguments.get("limit", 10))
            offset = int(arguments.get("offset", 0))

            where_parts = []
            if organism:
                where_parts.append(f'organismName: {{_ilike: "%{organism}%"}}')
            if tissue:
                where_parts.append(f'tissueName: {{_ilike: "%{tissue}%"}}')

            where_clause = (
                "{" + ", ".join(where_parts) + "}" if where_parts else "null"
            )
            where_arg = f"where: {where_clause}, " if where_parts else ""

            query = f"""
            {{
              datasets(
                {where_arg}limitOffset: {{limit: {limit}, offset: {offset}}}
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
            return {
                "status": "success",
                "data": {
                    "count": len(datasets),
                    "datasets": datasets,
                },
            }
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
            limit = int(arguments.get("limit", 20))
            offset = int(arguments.get("offset", 0))

            query = f"""
            {{
              runs(
                where: {{datasetId: {{_eq: {dataset_id}}}}},
                limitOffset: {{limit: {limit}, offset: {offset}}}
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
            return {
                "status": "success",
                "data": {
                    "dataset_id": dataset_id,
                    "count": len(runs),
                    "runs": runs,
                },
            }
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
            limit = int(arguments.get("limit", 10))
            offset = int(arguments.get("offset", 0))

            query = f"""
            {{
              tomograms(
                where: {{runId: {{_eq: {run_id}}}}},
                limitOffset: {{limit: {limit}, offset: {offset}}}
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
            return {
                "status": "success",
                "data": {
                    "run_id": run_id,
                    "count": len(tomograms),
                    "tomograms": tomograms,
                },
            }
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
            limit = int(arguments.get("limit", 20))
            offset = int(arguments.get("offset", 0))
            curator_only = arguments.get("curator_recommended_only", False)

            where_parts = [f"runId: {{_eq: {run_id}}}"]
            if curator_only:
                where_parts.append("isCuratorRecommended: {_eq: true}")

            where_clause = "{" + ", ".join(where_parts) + "}"

            query = f"""
            {{
              annotations(
                where: {where_clause},
                limitOffset: {{limit: {limit}, offset: {offset}}}
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
            return {
                "status": "success",
                "data": {
                    "run_id": run_id,
                    "count": len(annotations),
                    "annotations": annotations,
                },
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
