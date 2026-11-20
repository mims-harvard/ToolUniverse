from typing import Dict, Any, List, Optional
import requests
import json
from .base_tool import BaseTool
from .tool_registry import register_tool


def _strings(value: Any) -> list:
    """Azul answers every facet as a list, even a one-value one."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v not in (None, "")]
    return [str(value)]


def _facet(records: list, key: str) -> list:
    """One facet across every nested record, de-duplicated, order kept."""
    out = []
    for record in records or []:
        if not isinstance(record, dict):
            continue
        for value in _strings(record.get(key)):
            if value not in out:
                out.append(value)
    return out


def _total(records: list, key: str):
    """Sum a count across nested records; None when none of them carry it."""
    values = [
        r.get(key)
        for r in records or []
        if isinstance(r, dict) and isinstance(r.get(key), (int, float))
    ]
    return sum(values) if values else None


def _ages(donors: list) -> list:
    """organismAge is a list of {value, unit} per donor, not a string."""
    out = []
    for donor in donors or []:
        if not isinstance(donor, dict):
            continue
        for age in donor.get("organismAge") or []:
            if not isinstance(age, dict):
                continue
            text = " ".join(
                str(age.get(part)) for part in ("value", "unit") if age.get(part)
            )
            if text and text not in out:
                out.append(text)
    return out


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
                #
                # Four fields were not enough to tell one project from
                # another, and one omission made the answer misleading: the
                # first project this endpoint returns is "1M Neurons", which
                # is Mus musculus, and the row never said the species. A tool
                # that searches "single-cell projects" also has to say which
                # single-cell assay: the protocol block carries
                # libraryConstructionApproach ("10x 3' v2"), and the
                # cellSuspensions block the cell count the project is worth
                # opening for.
                specimens = hit.get("specimens") or []
                donors = hit.get("donorOrganisms") or []
                protocols = hit.get("protocols") or []
                suspensions = hit.get("cellSuspensions") or []
                project = (hit.get("projects") or [{}])[0] or {}
                projects.append(
                    {
                        "entryId": hit.get("entryId"),
                        "projectTitle": project.get("projectTitle"),
                        "projectShortname": project.get("projectShortname"),
                        "laboratory": _strings(project.get("laboratory")),
                        "estimatedCellCount": project.get("estimatedCellCount"),
                        "accessible": project.get("accessible"),
                        "dataUseRestriction": project.get("dataUseRestriction"),
                        # A project can span several specimens, donors and
                        # protocols; the row reported the first of each.
                        "organ": _facet(specimens, "organ"),
                        "organPart": _facet(suspensions, "organPart"),
                        "selectedCellType": _facet(suspensions, "selectedCellType"),
                        "totalCells": _total(suspensions, "totalCells"),
                        "donorDisease": _facet(donors, "disease"),
                        "genusSpecies": _facet(donors, "genusSpecies"),
                        "biologicalSex": _facet(donors, "biologicalSex"),
                        "developmentStage": _facet(donors, "developmentStage"),
                        "organismAge": _ages(donors),
                        "donorCount": _total(donors, "donorCount"),
                        "libraryConstructionApproach": _facet(
                            protocols, "libraryConstructionApproach"
                        ),
                        "nucleicAcidSource": _facet(protocols, "nucleicAcidSource"),
                        "instrumentManufacturerModel": _facet(
                            protocols, "instrumentManufacturerModel"
                        ),
                        "pairedEnd": _facet(protocols, "pairedEnd"),
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
                            # A manifest of downloads with no way to verify
                            # one, identify its version, or tell a final
                            # matrix from an intermediate.
                            "uuid": f.get("uuid"),
                            "version": f.get("version"),
                            "sha256": f.get("sha256"),
                            "accessible": f.get("accessible"),
                            "is_intermediate": f.get("isIntermediate"),
                            "content_description": _strings(
                                f.get("contentDescription")
                            ),
                            "matrix_cell_count": f.get("matrixCellCount"),
                            "file_source": f.get("fileSource"),
                            "drs_uri": f.get("drs_uri"),
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
