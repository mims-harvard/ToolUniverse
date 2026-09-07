# nasa_osdr_tool.py
"""
NASA Open Science Data Repository (OSDR) tool for ToolUniverse.

OSDR (formerly GeneLab) holds ~1,000 space biology studies: how spaceflight
and simulated microgravity affect organisms from bacteria to humans, across
transcriptomics, proteomics, microscopy, and physiology assays. ToolUniverse
already reaches other NASA data (the Exoplanet Archive) but nothing
biological, and OSDR's own study identifiers (OSD-N) are otherwise opaque.

A prior attempt at this integration was removed because the GeneLab data
domain it targeted (genelab-data.ndc.nasa.gov) had gone down; that domain
still 404s. OSDR has since migrated to osdr.nasa.gov and
visualization.osdr.nasa.gov, both verified live here.

APIs: https://osdr.nasa.gov/osdr/data/search
      https://visualization.osdr.nasa.gov/biodata/api/v2
No authentication required.
"""

from typing import Dict, Any, List

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

SEARCH_URL = "https://osdr.nasa.gov/osdr/data/search"
FILES_URL = "https://osdr.nasa.gov/osdr/data/osd/files"
DATASET_URL = "https://visualization.osdr.nasa.gov/biodata/api/v2/dataset"


def _first(value: Any) -> Any:
    """OSDR search hits sometimes wrap a scalar in a one-item list."""
    if isinstance(value, list):
        return value[0] if value else None
    return value


@register_tool("NASAOSDRTool")
class NASAOSDRTool(BaseTool):
    """
    Tool for searching NASA's Open Science Data Repository of space biology
    studies.

    Supports full-text search with optional organism/assay filters, fetching
    one study's full metadata, and listing its downloadable data files.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 45)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "search_studies"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the OSDR lookup."""
        try:
            if self.operation == "search_studies":
                return self._search_studies(arguments)
            if self.operation == "get_study":
                return self._get_study(arguments)
            if self.operation == "list_files":
                return self._list_files(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"OSDR request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to NASA OSDR. Check network.",
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {"status": "error", "error": f"OSDR returned HTTP {code}"}
        except ValueError:
            return {"status": "error", "error": "OSDR returned a non-JSON response"}
        except Exception as e:
            return {"status": "error", "error": f"Error querying OSDR: {str(e)}"}

    def _search_studies(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Full-text search over OSDR studies, with optional field filters."""
        query = (arguments.get("query") or "").strip()
        if not query:
            return {
                "status": "error",
                "error": "query is required: free text such as 'microgravity "
                "bone loss' or 'radiation Drosophila'.",
            }

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 25
        limit = min(limit, 100)

        params: Dict[str, Any] = {"term": query, "size": limit, "from": 0}
        organism = (arguments.get("organism") or "").strip()
        if organism:
            params["ffield"] = "organism"
            params["fvalue"] = organism

        response = requests.get(SEARCH_URL, params=params, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        hits = (payload.get("hits") or {}).get("hits") or []

        rows = []
        for hit in hits:
            source = hit.get("_source") or {}
            accession = source.get("Accession")
            rows.append(
                {
                    "accession": accession,
                    "title": source.get("Study Title"),
                    "organism": _first(source.get("organism")),
                    "mission": (source.get("Mission") or {}).get("Name") or None,
                    "flight_program": source.get("Flight Program"),
                    "assay_measurement_type": source.get(
                        "Study Assay Measurement Type"
                    ),
                    "assay_technology_type": source.get(
                        "Study Assay Technology Type"
                    ),
                    "factor_name": source.get("Study Factor Name"),
                    "release_date": source.get("Study Public Release Date"),
                    "usable_with_get_study": bool(
                        accession and str(accession).startswith("OSD-")
                    ),
                }
            )

        if not rows:
            return {
                "status": "error",
                "error": f"No OSDR studies matching '{query}'"
                + (f" for organism '{organism}'" if organism else "")
                + ".",
            }

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "query": query,
                "organism_filter": organism or None,
                "total_matching": (payload.get("hits") or {}).get("total"),
                "returned": len(rows),
                "note": "OSDR also indexes cross-referenced external datasets "
                "(e.g. GEO accessions); only rows with usable_with_get_study "
                "true (accession starting 'OSD-') work with get_study and "
                "list_files.",
                "source": "NASA Open Science Data Repository",
            },
        }

    @staticmethod
    def _study_number(study_id: str) -> str:
        """Accept 'OSD-486', 'osd-486', or a bare '486'."""
        study_id = study_id.strip()
        if "-" in study_id:
            study_id = study_id.split("-", 1)[1]
        return study_id

    def _get_study(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch full metadata for one OSDR study."""
        study_id = (arguments.get("study_id") or "").strip()
        if not study_id:
            return {
                "status": "error",
                "error": "study_id is required, e.g. 'OSD-1'. Use "
                "OSDR_search_studies to find one.",
            }

        number = self._study_number(study_id)
        accession = f"OSD-{number}"
        response = requests.get(
            f"{DATASET_URL}/{accession}/", timeout=self.timeout
        )
        if response.status_code == 422:
            return {
                "status": "error",
                "error": f"No OSDR study '{accession}'.",
            }
        response.raise_for_status()
        payload = response.json().get(accession)
        if not payload:
            return {
                "status": "error",
                "error": f"No OSDR study '{accession}'.",
            }

        metadata = payload.get("metadata") or {}
        return {
            "status": "success",
            "data": {
                "accession": accession,
                "title": metadata.get("study title"),
                "description": metadata.get("study description"),
                "organism": _first(metadata.get("organism")),
                "material_type": metadata.get("material type"),
                "mission": metadata.get("mission"),
                "flight_program": metadata.get("flight program"),
                "project_title": metadata.get("project title"),
                "factor_name": metadata.get("study factor name"),
                "factor_type": metadata.get("study factor type"),
                "assay_measurement_type": metadata.get(
                    "study assay measurement type"
                ),
                "assay_technology_type": metadata.get(
                    "study assay technology type"
                ),
                "publication_title": metadata.get("study publication title"),
                "publication_authors": metadata.get(
                    "study publication author list"
                ),
                "release_date": metadata.get("study public release date"),
            },
            "metadata": {
                "accession": accession,
                "note": "Use OSDR_list_files with the same accession for "
                "downloadable data files.",
                "source": "NASA Open Science Data Repository",
            },
        }

    def _list_files(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List one study's downloadable data files."""
        study_id = (arguments.get("study_id") or "").strip()
        if not study_id:
            return {
                "status": "error",
                "error": "study_id is required, e.g. 'OSD-1'. Use "
                "OSDR_search_studies to find one.",
            }

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 50
        limit = min(limit, 200)

        number = self._study_number(study_id)
        accession = f"OSD-{number}"
        response = requests.get(
            f"{FILES_URL}/{number}", timeout=self.timeout
        )
        response.raise_for_status()
        payload = response.json()
        study = (payload.get("studies") or {}).get(accession)
        if not study:
            return {
                "status": "error",
                "error": f"No OSDR study '{accession}'.",
            }

        all_files = study.get("study_files") or []
        rows = [
            {
                "file_name": f.get("file_name"),
                "category": f.get("category"),
                "subcategory": f.get("subcategory") or None,
                "file_size_bytes": f.get("file_size"),
                "restricted": bool(f.get("restricted")),
                "download_path": f.get("remote_url"),
            }
            for f in all_files[:limit]
        ]

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "accession": accession,
                "total_files": study.get("file_count", len(all_files)),
                "returned": len(rows),
                "note": "download_path is relative to https://osdr.nasa.gov.",
                "source": "NASA Open Science Data Repository",
            },
        }
