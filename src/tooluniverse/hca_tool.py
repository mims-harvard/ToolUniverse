from typing import Dict, Any, List, Optional
import requests
import json
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("HCATool")
class HCATool(BaseTool):
    """
    Tool for interacting with the Human Cell Atlas (HCA) Data Coordination Platform (DCP) v2 API.
    Allows searching for projects and retrieving file manifests.
    """

    BASE_URL = "https://service.azul.data.humancellatlas.org"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the HCA tool action.

        Args:
            arguments (Dict[str, Any]): Dictionary containing the action and its parameters.
                Expected keys:
                - action (str): "search_projects" or "get_file_manifest"
                - organ (str, optional): Organ to filter by (for search_projects)
                - disease (str, optional): Disease to filter by (for search_projects)
                - project_id (str, optional): Project ID (for get_file_manifest)
                - limit (int, optional): Max results to return (default 10)

        Returns:
            Dict[str, Any]: The results of the action.
        """
        # Fix-R39A-3: "action" is optional in the schema (each config
        # exposes exactly one valid value via enum+default), so a caller
        # who omits it must still resolve to that tool instance's own
        # action -- there was previously no fallback at all, so an omitted
        # action fell straight through to "Unknown action: None".
        action = arguments.get("action") or (
            self.tool_config.get("parameter", {})
            .get("properties", {})
            .get("action", {})
            .get("default", "")
        )

        if action == "search_projects":
            return self.search_projects(
                organ=arguments.get("organ"),
                disease=arguments.get("disease"),
                limit=arguments.get("limit", 10),
            )
        elif action == "get_file_manifest":
            project_id = arguments.get("project_id")
            if not project_id:
                raise ValueError("project_id is required for get_file_manifest")
            return self.get_file_manifest(project_id, limit=arguments.get("limit", 10))
        else:
            raise ValueError(f"Unknown action: {action}")

    def search_projects(
        self,
        organ: Optional[str] = None,
        disease: Optional[str] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Search for projects in the HCA DCP.
        """
        url = f"{self.BASE_URL}/index/projects"
        filters = {}

        if organ:
            filters["organ"] = {"is": [organ]}

        if disease:
            # Azul's facet is "donorDisease", not "disease" -- the latter is
            # rejected outright with a 400 "Additional properties are not
            # allowed" error (confirmed live).
            filters["donorDisease"] = {"is": [disease]}

        params = {"size": limit, "filters": json.dumps(filters) if filters else "{}"}

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            projects = []
            for hit in data.get("hits", []):
                # organ/disease live under the nested specimens/donorOrganisms
                # arrays as plain string lists, not top-level "modelOrgan"/
                # "donorDisease" dict keys (confirmed live) -- those top-level
                # keys don't exist in the hit at all, so reading them always
                # silently returned None.
                specimens = hit.get("specimens") or [{}]
                donors = hit.get("donorOrganisms") or [{}]
                projects.append(
                    {
                        "entryId": hit.get("entryId"),
                        "projectTitle": hit.get("projects", [{}])[0].get(
                            "projectTitle"
                        ),
                        "organ": specimens[0].get("organ"),
                        "donorDisease": donors[0].get("disease"),
                    }
                )

            return {
                "total_hits": data.get("pagination", {}).get("total", 0),
                "projects": projects,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_file_manifest(self, project_id: str, limit: int = 10) -> Dict[str, Any]:
        """
        Get file download links for a project.
        """
        url = f"{self.BASE_URL}/index/files"
        filters = {"projectId": {"is": [project_id]}}

        params = {"size": limit, "filters": json.dumps(filters)}

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            files = []
            for hit in data.get("hits", []):
                for f in hit.get("files", []):
                    files.append(
                        {
                            "name": f.get("name"),
                            "format": f.get("format"),
                            "size": f.get("size"),
                            "url": f.get("azul_url"),
                        }
                    )

            return {
                "total_files": data.get("pagination", {}).get("total", 0),
                "files": files[
                    :limit
                ],  # Pagination applies to hits (bundles), but we extract files, so slice again to be safe
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
