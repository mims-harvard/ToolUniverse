# single_cell_portal_tool.py
"""
Broad Institute Single Cell Portal (SCP) REST API tool for ToolUniverse.

The Single Cell Portal hosts 1000+ curated single-cell studies covering
80M+ cells, with per-study cell counts, gene counts, and free-text
descriptions. It complements CELLxGENE Discover (CxGDisc_* tools) and the
EBI Single Cell Expression Atlas (SCXA_* tools), which index largely
different study sets.

API: https://singlecell.broadinstitute.org/single_cell/api/v1
No authentication required for public study metadata.
"""

import requests
from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool

SCP_BASE_URL = "https://singlecell.broadinstitute.org/single_cell/api/v1"


def _summarize_study(study: Dict[str, Any], description_chars: int) -> Dict[str, Any]:
    """Trim a raw SCP study record to the fields agents actually use.

    SCP descriptions embed whole paper abstracts, so they are truncated to
    keep responses usable in a model context window.
    """
    description = study.get("description") or ""
    if description_chars >= 0 and len(description) > description_chars:
        description = description[:description_chars].rstrip() + "..."

    accession = study.get("accession")
    study_url = study.get("study_url")
    if study_url and study_url.startswith("/"):
        study_url = f"https://singlecell.broadinstitute.org{study_url}"
    elif not study_url and accession:
        study_url = (
            f"https://singlecell.broadinstitute.org/single_cell/study/{accession}"
        )

    return {
        "accession": accession,
        "name": (study.get("name") or "").strip(),
        "description": description,
        "cell_count": study.get("cell_count"),
        "gene_count": study.get("gene_count"),
        "study_url": study_url,
    }


@register_tool("SingleCellPortalTool")
class SingleCellPortalTool(BaseTool):
    """
    Tool for querying the Broad Institute Single Cell Portal.

    Supports keyword search across studies, listing the full public study
    catalog with optional filtering, and retrieving a single study by
    accession.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "search_studies"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Single Cell Portal API call."""
        try:
            if self.operation == "search_studies":
                return self._search_studies(arguments)
            elif self.operation == "list_studies":
                return self._list_studies(arguments)
            elif self.operation == "get_study":
                return self._get_study(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Single Cell Portal request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to Single Cell Portal. Check network.",
            }
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            return {
                "status": "error",
                "error": f"Single Cell Portal returned HTTP {status}",
            }
        except ValueError:
            return {
                "status": "error",
                "error": "Single Cell Portal returned a non-JSON response",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Error querying Single Cell Portal: {str(e)}",
            }

    def _fetch_all_studies(self) -> List[Dict[str, Any]]:
        """Fetch the public study catalog.

        Note: the /studies route requires authentication; /site/studies is the
        public equivalent.
        """
        url = f"{SCP_BASE_URL}/site/studies"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        raw = response.json()
        return raw if isinstance(raw, list) else []

    def _search_studies(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Keyword search across study titles, descriptions, and metadata."""
        query = arguments.get("query")
        if not query:
            return {
                "status": "error",
                "error": "query is required "
                "(e.g., 'lung', 'glioblastoma', 'COVID-19').",
            }

        url = f"{SCP_BASE_URL}/search"
        params = {"type": "study", "terms": query}
        page = arguments.get("page")
        if isinstance(page, int) and page > 0:
            params["page"] = page

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        raw = response.json()

        studies = raw.get("studies") or []
        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 20
        limit = min(limit, 100)

        desc_chars = arguments.get("description_chars")
        if not isinstance(desc_chars, int) or desc_chars < 0:
            desc_chars = 500

        results = [_summarize_study(s, desc_chars) for s in studies[:limit]]

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "query": query,
                "total_matching": raw.get("total_studies"),
                "total_pages": raw.get("total_pages"),
                "current_page": raw.get("current_page"),
                "returned": len(results),
                "source": "Broad Institute Single Cell Portal",
            },
        }

    def _list_studies(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List the public study catalog, optionally filtered by cell count."""
        studies = self._fetch_all_studies()
        total_available = len(studies)

        min_cells = arguments.get("min_cells")
        if isinstance(min_cells, int):
            studies = [s for s in studies if (s.get("cell_count") or 0) >= min_cells]

        keyword = arguments.get("keyword")
        if keyword:
            kw = keyword.lower()
            studies = [
                s
                for s in studies
                if kw in (s.get("name") or "").lower()
                or kw in (s.get("description") or "").lower()
            ]

        studies.sort(key=lambda s: s.get("cell_count") or 0, reverse=True)

        total_matching = len(studies)
        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 20
        limit = min(limit, 100)

        desc_chars = arguments.get("description_chars")
        if not isinstance(desc_chars, int) or desc_chars < 0:
            desc_chars = 300

        results = [_summarize_study(s, desc_chars) for s in studies[:limit]]

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "total_available": total_available,
                "total_matching": total_matching,
                "returned": len(results),
                "sorted_by": "cell_count descending",
                "source": "Broad Institute Single Cell Portal",
            },
        }

    def _get_study(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve one study by its SCP accession."""
        accession = arguments.get("accession")
        if not accession:
            return {
                "status": "error",
                "error": "accession is required (e.g., 'SCP1'). "
                "Use SCP_search_studies to find accessions.",
            }

        accession = accession.strip()
        studies = self._fetch_all_studies()
        match = next(
            (
                s
                for s in studies
                if (s.get("accession") or "").lower() == accession.lower()
            ),
            None,
        )

        if match is None:
            return {
                "status": "error",
                "error": f"No public study found with accession '{accession}'. "
                "Accessions look like 'SCP1'. Note that private or detached "
                "studies are not exposed by the public API.",
            }

        return {
            "status": "success",
            "data": _summarize_study(match, -1),
            "metadata": {
                "accession": accession,
                "source": "Broad Institute Single Cell Portal",
            },
        }
