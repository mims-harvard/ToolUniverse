# bioimage_archive_tool.py
"""
BioImage Archive (EBI BioStudies) REST API tool for ToolUniverse.

The BioImage Archive is an open resource at EMBL-EBI for biological images from
life sciences research. It stores and distributes biological image datasets
spanning microscopy, imaging, and visualization experiments.

API: https://www.ebi.ac.uk/biostudies/api/v1/
No authentication required. Free for all use.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

BIOSTUDIES_BASE_URL = "https://www.ebi.ac.uk/biostudies/api/v1"


@register_tool("BioImageArchiveTool")
class BioImageArchiveTool(BaseTool):
    """
    Tool for querying the BioImage Archive at EBI.

    Provides access to biological imaging datasets including fluorescence
    microscopy, cryo-EM, confocal imaging, and other life sciences imaging
    modalities. Supports searching studies and retrieving detailed metadata.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.action = fields.get("action", "search")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the BioImage Archive API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"BioImage Archive API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to BioImage Archive API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"BioImage Archive API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying BioImage Archive: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate query method."""
        if self.action == "search":
            return self._search(arguments)
        elif self.action == "get_study":
            return self._get_study(arguments)
        elif self.action == "search_bioimages":
            return self._search_bioimages(arguments)
        elif self.action == "list_study_files":
            return self._list_study_files(arguments)
        else:
            return {"status": "error", "error": f"Unknown action: {self.action}"}

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for biological imaging studies."""
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        page_size = min(arguments.get("page_size") or 10, 100)
        page = arguments.get("page") or 1

        params = {
            "query": query,
            "pageSize": page_size,
            "page": page,
        }

        url = f"{BIOSTUDIES_BASE_URL}/search"
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        hits = data.get("hits", [])

        results = []
        for hit in hits:
            results.append(
                {
                    "accession": hit.get("accession", ""),
                    "title": hit.get("title"),
                    "author": hit.get("author"),
                    "release_date": hit.get("releaseDate") or hit.get("release_date"),
                    "type": hit.get("type"),
                    "links": hit.get("links"),
                    "files": hit.get("files"),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "BioImage Archive (EBI BioStudies)",
                "total_hits": data.get("totalHits", 0),
                "page": page,
                "page_size": page_size,
                "query": query,
            },
        }

    def _get_study(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information about a specific study."""
        accession = arguments.get("accession", "")
        if not accession:
            return {"status": "error", "error": "accession parameter is required"}

        url = f"{BIOSTUDIES_BASE_URL}/studies/{accession}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()

        # Parse attributes into a more usable format
        attributes = data.get("attributes", [])
        attr_dict = {}
        for attr in attributes:
            name = attr.get("name", "")
            value = attr.get("value", "")
            if name:
                attr_dict[name] = value

        # Extract section info
        section = data.get("section", {})
        section_type = section.get("type")
        section_attrs = section.get("attributes", [])

        # Extract key metadata from section attributes
        title = None
        description = None
        organism = None
        imaging_method = None

        for attr in section_attrs:
            name = attr.get("name", "").lower()
            value = attr.get("value", "")
            if name == "title":
                title = value
            elif name in ("description", "abstract"):
                description = value
            elif name == "organism":
                organism = value
            elif name in ("imaging method", "imaging_method"):
                imaging_method = value

        return {
            "status": "success",
            "data": {
                "accession": data.get("accno", accession),
                "type": data.get("type"),
                "title": title or attr_dict.get("Title"),
                "release_date": attr_dict.get("ReleaseDate"),
                "description": description,
                "organism": organism,
                "imaging_method": imaging_method,
                "attributes": attributes,
                "section_type": section_type,
            },
            "metadata": {
                "source": "BioImage Archive (EBI BioStudies)",
                "accession": accession,
            },
        }

    def _search_bioimages(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search the BioImages-specific collection."""
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        page_size = min(arguments.get("page_size") or 10, 100)

        params = {
            "query": query,
            "pageSize": page_size,
        }

        url = f"{BIOSTUDIES_BASE_URL}/BioImages/search"
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        hits = data.get("hits", [])

        results = []
        for hit in hits:
            results.append(
                {
                    "accession": hit.get("accession", ""),
                    "title": hit.get("title"),
                    "author": hit.get("author"),
                    "release_date": hit.get("releaseDate") or hit.get("release_date"),
                    "type": hit.get("type"),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "BioImage Archive (EBI BioStudies - BioImages collection)",
                "total_hits": data.get("totalHits", 0),
                "query": query,
            },
        }

    def _list_study_files(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List the file/image manifest of a study with per-file metadata.

        Each returned record carries the file Name, relative download path, size,
        and any per-image experimental annotations attached in the study (e.g.
        staining, cells, treatment, channels, timepoint).
        """
        accession = arguments.get("accession", "")
        if not accession:
            return {"status": "error", "error": "accession parameter is required"}

        # DataTables-style pagination: the files endpoint uses start/length.
        length = min(int(arguments.get("limit") or 25), 500)
        start = int(arguments.get("offset") or 0)

        params = {"start": start, "length": length}
        url = f"{BIOSTUDIES_BASE_URL}/files/{accession}"
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        files = data.get("data", []) if isinstance(data, dict) else []

        results = []
        # Structural keys present on every record; everything else is an
        # experiment-specific annotation column (staining, cells, channels...).
        structural = {"Name", "Size", "Section", "path", "type", "size"}
        for row in files:
            if not isinstance(row, dict):
                continue
            annotations = {
                k: v
                for k, v in row.items()
                if k not in structural and v not in (None, "")
            }
            results.append(
                {
                    "Name": row.get("Name"),
                    "path": row.get("path"),
                    "size": row.get("size") or row.get("Size"),
                    "type": row.get("type"),
                    "section": row.get("Section"),
                    "annotations": annotations,
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "BioImage Archive (EBI BioStudies)",
                "accession": accession,
                "records_total": data.get("recordsTotal")
                if isinstance(data, dict)
                else None,
                "returned": len(results),
                "offset": start,
                "limit": length,
            },
        }
