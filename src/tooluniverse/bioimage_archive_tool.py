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


def _positive_int(value: Any, *, name: str, maximum: int | None = None) -> int:
    """Parse a positive integer without silently rounding or clamping it."""
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a positive integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a positive integer") from None
    if isinstance(value, float) and not value.is_integer():
        raise ValueError(f"{name} must be a positive integer")
    if parsed < 1:
        raise ValueError(f"{name} must be a positive integer")
    if maximum is not None and parsed > maximum:
        raise ValueError(f"{name} must be at most {maximum}")
    return parsed


def _search_page_metadata(
    data: Dict[str, Any], *, page: int, page_size: int, returned: int
) -> Dict[str, Any]:
    """Preserve BioStudies' exact-vs-lower-bound total qualifier."""
    total_hits = data.get("totalHits")
    total_hits_exact = data.get("isTotalHitsExact")
    relation = (
        "exact"
        if total_hits_exact is True
        else "lower_bound"
        if total_hits_exact is False
        else "unknown"
    )
    page_end = (page - 1) * page_size + returned
    if total_hits_exact is True and isinstance(total_hits, int):
        has_more = page_end < total_hits
    else:
        has_more = bool(
            (isinstance(total_hits, int) and page_end < total_hits)
            or returned >= page_size
        )
    warning = None
    if total_hits_exact is False:
        warning = (
            "BioStudies reports totalHits as a lower bound, not an exact count; "
            "continue through next_page until a short or empty page is returned."
        )
    return {
        "total_hits": total_hits,
        "total_hits_exact": total_hits_exact,
        "total_hits_relation": relation,
        "returned": returned,
        "page": page,
        "page_size": page_size,
        "has_more": has_more,
        "truncated": has_more,
        "next_page": page + 1 if has_more else None,
        "warning": warning,
    }


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

        try:
            page_size_value = arguments.get("page_size")
            page_value = arguments.get("page")
            page_size = _positive_int(
                10 if page_size_value is None else page_size_value,
                name="page_size",
                maximum=100,
            )
            page = _positive_int(1 if page_value is None else page_value, name="page")
        except (TypeError, ValueError) as exc:
            return {"status": "error", "error": str(exc)}

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

        metadata = _search_page_metadata(
            data, page=page, page_size=page_size, returned=len(results)
        )
        metadata.update(
            {
                "source": "BioImage Archive (EBI BioStudies)",
                "query": query,
            }
        )
        return {
            "status": "success",
            "data": results,
            "metadata": metadata,
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

        try:
            page_size_value = arguments.get("page_size")
            page_value = arguments.get("page")
            page_size = _positive_int(
                10 if page_size_value is None else page_size_value,
                name="page_size",
                maximum=100,
            )
            page = _positive_int(1 if page_value is None else page_value, name="page")
        except (TypeError, ValueError) as exc:
            return {"status": "error", "error": str(exc)}

        params = {
            "query": query,
            "pageSize": page_size,
            "page": page,
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

        metadata = _search_page_metadata(
            data, page=page, page_size=page_size, returned=len(results)
        )
        metadata.update(
            {
                "source": "BioImage Archive (EBI BioStudies - BioImages collection)",
                "query": query,
            }
        )
        return {
            "status": "success",
            "data": results,
            "metadata": metadata,
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
        try:
            limit_value = arguments.get("limit")
            length = _positive_int(
                25 if limit_value is None else limit_value,
                name="limit",
                maximum=500,
            )
            raw_start = arguments.get("offset")
            raw_start = 0 if raw_start is None else raw_start
            if isinstance(raw_start, bool):
                raise ValueError("offset must be a non-negative integer")
            start = int(raw_start)
            if isinstance(raw_start, float) and not raw_start.is_integer():
                raise ValueError("offset must be a non-negative integer")
            if start < 0:
                raise ValueError("offset must be a non-negative integer")
        except (TypeError, ValueError) as exc:
            return {"status": "error", "error": str(exc)}

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

        records_total = data.get("recordsTotal") if isinstance(data, dict) else None
        records_filtered = (
            data.get("recordsFiltered") if isinstance(data, dict) else None
        )
        paging_total = (
            records_filtered if isinstance(records_filtered, int) else records_total
        )
        has_more = bool(
            isinstance(paging_total, int) and start + len(results) < paging_total
        )
        next_offset = start + len(results) if has_more and results else None

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "BioImage Archive (EBI BioStudies)",
                "accession": accession,
                "records_total": records_total,
                "records_filtered": records_filtered,
                "returned": len(results),
                "offset": start,
                "limit": length,
                "has_more": has_more,
                "truncated": has_more,
                "next_offset": next_offset,
            },
        }
