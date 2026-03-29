"""
re3data tool for searching and retrieving research data repository metadata.

re3data.org is a global registry of 3,000+ research data repositories covering
all academic disciplines. The API returns XML which this tool parses into JSON.
"""

import requests
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool
from .http_utils import request_with_retry

_NS = {"r3d": "http://www.re3data.org/schema/2-2"}


def _text(el: Optional[ET.Element], tag: str) -> Optional[str]:
    """Extract text from a namespaced child element."""
    child = el.find(f"r3d:{tag}", _NS) if el is not None else None
    return child.text.strip() if child is not None and child.text else None


def _texts(el: Optional[ET.Element], tag: str) -> List[str]:
    """Extract text from all matching namespaced child elements."""
    if el is None:
        return []
    return [
        c.text.strip()
        for c in el.findall(f"r3d:{tag}", _NS)
        if c.text and c.text.strip()
    ]


def _parse_repo_list(xml_text: str) -> List[Dict[str, Any]]:
    """Parse the search results XML list into a list of repository summaries."""
    root = ET.fromstring(xml_text)
    repos = []
    for repo_el in root.findall("repository"):
        repo_id = repo_el.findtext("id", "").strip()
        name = repo_el.findtext("name", "").strip()
        doi = repo_el.findtext("doi", "").strip()
        repos.append({"id": repo_id, "name": name, "doi": doi})
    return repos


def _parse_repo_detail(xml_text: str) -> Dict[str, Any]:
    """Parse the detailed repository XML into a structured dictionary."""
    root = ET.fromstring(xml_text)
    repo = root.find(".//r3d:repository", _NS)
    if repo is None:
        return {"error": "No repository element found in response"}

    # Subjects with their scheme attribute
    subjects = []
    for s in repo.findall("r3d:subject", _NS):
        scheme = s.get("subjectScheme", "")
        if s.text and s.text.strip():
            subjects.append({"subject": s.text.strip(), "scheme": scheme})

    # Content types
    content_types = _texts(repo, "contentType")

    # Keywords
    keywords = _texts(repo, "keyword")

    # Data access types
    access_types = []
    for da in repo.findall("r3d:dataAccess", _NS):
        access_type = _text(da, "dataAccessType")
        restrictions = _texts(da, "dataAccessRestriction")
        if access_type:
            entry = {"type": access_type}
            if restrictions:
                entry["restrictions"] = restrictions
            access_types.append(entry)

    # Institutions
    institutions = []
    for inst in repo.findall("r3d:institution", _NS):
        inst_name = _text(inst, "institutionName")
        country = _text(inst, "institutionCountry")
        inst_type = _text(inst, "institutionType")
        url = _text(inst, "institutionURL")
        if inst_name:
            entry = {"name": inst_name}
            if country:
                entry["country"] = country
            if inst_type:
                entry["type"] = inst_type
            if url:
                entry["url"] = url
            institutions.append(entry)

    # Data licenses
    licenses = []
    for dl in repo.findall("r3d:dataLicense", _NS):
        lic_name = _text(dl, "dataLicenseName")
        lic_url = _text(dl, "dataLicenseURL")
        if lic_name:
            licenses.append({"name": lic_name, "url": lic_url})

    return {
        "id": _text(repo, "re3data.orgIdentifier"),
        "name": _text(repo, "repositoryName"),
        "url": _text(repo, "repositoryURL"),
        "description": _text(repo, "description"),
        "type": _text(repo, "type"),
        "size": _text(repo, "size"),
        "languages": _texts(repo, "repositoryLanguage"),
        "subjects": subjects,
        "keywords": keywords,
        "content_types": content_types,
        "data_access": access_types,
        "data_licenses": licenses,
        "institutions": institutions,
        "mission_statement_url": _text(repo, "missionStatementURL"),
    }


@register_tool("Re3DataTool")
class Re3DataTool(BaseTool):
    """Search and retrieve metadata from the re3data.org registry of research data repositories."""

    BASE_URL = "https://www.re3data.org/api/beta"

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "ToolUniverse/1.0 (re3data client)"})
        self.timeout = 30

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = self.tool_config.get("name", "")

        if tool_name == "re3data_search_repositories":
            return self._search_repositories(arguments)
        elif tool_name == "re3data_get_repository":
            return self._get_repository(arguments)
        return {"status": "error", "error": f"Unknown tool: {tool_name}"}

    def _search_repositories(self, args: Dict[str, Any]) -> Dict[str, Any]:
        query = args.get("query")
        if not query:
            return {"status": "error", "error": "`query` parameter is required."}

        subjects = args.get("subjects")
        countries = args.get("countries")

        try:
            params = {"query": query}
            resp = request_with_retry(
                self.session,
                "GET",
                f"{self.BASE_URL}/repositories",
                params=params,
                timeout=self.timeout,
                max_attempts=3,
            )
            if resp.status_code != 200:
                return {
                    "status": "error",
                    "error": f"re3data API error: HTTP {resp.status_code}",
                    "detail": resp.text[:500],
                }

            repos = _parse_repo_list(resp.text)

            # Client-side filtering by subjects/countries (API doesn't support these filters)
            if subjects:
                subjects_lower = subjects.lower()
                repos = [
                    r
                    for r in repos
                    if subjects_lower in r.get("name", "").lower()
                    or subjects_lower in r.get("id", "").lower()
                ]

            if countries:
                countries.upper()
                # Country filtering requires detail data; skip for search results
                # as the list endpoint doesn't include country info
                pass

            return {
                "status": "success",
                "data": repos,
                "count": len(repos),
            }
        except Exception as e:
            return {"status": "error", "error": f"re3data API error: {str(e)}"}

    def _get_repository(self, args: Dict[str, Any]) -> Dict[str, Any]:
        repo_id = args.get("repository_id")
        if not repo_id:
            return {
                "status": "error",
                "error": "`repository_id` parameter is required.",
            }

        try:
            url = f"{self.BASE_URL}/repository/{repo_id}"
            resp = request_with_retry(
                self.session,
                "GET",
                url,
                timeout=self.timeout,
                max_attempts=3,
            )
            if resp.status_code == 404:
                return {
                    "status": "error",
                    "error": f"Repository not found: {repo_id}",
                }
            if resp.status_code != 200:
                return {
                    "status": "error",
                    "error": f"re3data API error: HTTP {resp.status_code}",
                    "detail": resp.text[:500],
                }

            detail = _parse_repo_detail(resp.text)
            return {
                "status": "success",
                "data": detail,
                "url": url,
            }
        except Exception as e:
            return {"status": "error", "error": f"re3data API error: {str(e)}"}
