import re
import requests
from typing import Dict, Any, Optional, List
from .base_tool import BaseTool
from .tool_registry import register_tool

# Optional but recommended: text extraction for HTML
try:
    from bs4 import BeautifulSoup  # pip install beautifulsoup4
except ImportError:
    BeautifulSoup = None  # We’ll guard uses so the tool still loads

ODPHP_BASE_URL = "https://odphp.health.gov/myhealthfinder/api/v4"


class ODPHPRESTTool(BaseTool):
    """Base class for ODPHP (MyHealthfinder) REST API tools."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = tool_config["fields"]["endpoint"]

    def _make_request(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{ODPHP_BASE_URL}{self.endpoint}"
        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return {
                "status": "success",
                "data": data.get("Result"),
                "metadata": {
                    "source": "ODPHP MyHealthfinder",
                    "endpoint": url,
                    "query": params,
                },
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except ValueError as e:
            return {"status": "error", "error": f"Failed to parse JSON: {str(e)}"}


def _sections_array(resource: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Tolerant accessor for the sections array.
    Data sometimes uses Sections.Section (capital S) and sometimes Sections.section (lowercase).
    """
    sect = resource.get("Sections") or {}
    arr = sect.get("Section")
    if not isinstance(arr, list):
        arr = sect.get("section")
    return arr if isinstance(arr, list) else []


def _strip_html_to_text(html: str) -> str:
    if not html:
        return ""
    if BeautifulSoup is None:
        # fallback: very light tag remover
        text = re.sub(r"<[^>]+>", " ", html)
        return re.sub(r"\s+", " ", text).strip()
    soup = BeautifulSoup(html, "html.parser")
    # remove scripts/styles
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    text = soup.get_text("\n", strip=True)
    text = re.sub(r"\n{2,}", "\n\n", text)
    return text.strip()


@register_tool("ODPHPMyHealthfinder")
class ODPHPMyHealthfinder(ODPHPRESTTool):
    """Search for demographic-specific health recommendations (MyHealthfinder)."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if "lang" in arguments:
            params["lang"] = arguments["lang"]
        if "age" in arguments:
            params["age"] = arguments["age"]
        if "sex" in arguments:
            params["sex"] = arguments["sex"]
        if "pregnant" in arguments:
            params["pregnant"] = arguments["pregnant"]

        res = self._make_request(params)

        # Optional: attach PlainSections if requested
        if (
            isinstance(res, dict)
            and not res.get("error")
            and arguments.get("strip_html")
        ):
            data = res.get("data") or {}
            resources = (
                ((data.get("Resources") or {}).get("All") or {}).get("Resource")
            ) or []
            if isinstance(resources, list):
                for r in resources:
                    plain = []
                    for sec in _sections_array(r):
                        plain.append(
                            {
                                "Title": sec.get("Title", ""),
                                "PlainContent": _strip_html_to_text(
                                    sec.get("Content", "")
                                ),
                            }
                        )
                    if plain:
                        r["PlainSections"] = plain
        return res


@register_tool("ODPHPItemList")
class ODPHPItemList(ODPHPRESTTool):
    """Retrieve list of topics or categories."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if "lang" in arguments:
            params["lang"] = arguments["lang"]
        if "type" in arguments:
            params["type"] = arguments["type"]
        return self._make_request(params)


@register_tool("ODPHPTopicSearch")
class ODPHPTopicSearch(ODPHPRESTTool):
    """Search for health topics by ID, category, or keyword."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if "lang" in arguments:
            params["lang"] = arguments["lang"]
        if "topicId" in arguments:
            params["topicId"] = arguments["topicId"]
        if "categoryId" in arguments:
            params["categoryId"] = arguments["categoryId"]
        if "keyword" in arguments:
            params["keyword"] = arguments["keyword"]

        res = self._make_request(params)

        # Optional: attach PlainSections if requested
        if (
            isinstance(res, dict)
            and not res.get("error")
            and arguments.get("strip_html")
        ):
            data = res.get("data") or {}
            resources = ((data.get("Resources") or {}).get("Resource")) or []
            if isinstance(resources, list):
                for r in resources:
                    plain = []
                    for sec in _sections_array(r):
                        plain.append(
                            {
                                "Title": sec.get("Title", ""),
                                "PlainContent": _strip_html_to_text(
                                    sec.get("Content", "")
                                ),
                            }
                        )
                    if plain:
                        r["PlainSections"] = plain
        return res


@register_tool("ODPHPOutlinkFetch")
class ODPHPOutlinkFetch(BaseTool):
    """
    Fetch article pages referenced by AccessibleVersion / RelatedItems.Url and return readable text.
    - HTML: extracts main/article/body text; strips nav/aside/footer/script/style.
    - PDF or non-HTML: returns metadata + URL so the agent can surface it.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.timeout = 30

    def _extract_text(self, html: str) -> Dict[str, str]:
        if BeautifulSoup is None:
            # fallback: crude extraction
            title = ""
            # attempt to find <title>
            m = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.I | re.S)
            if m:
                title = re.sub(r"\s+", " ", m.group(1)).strip()
            text = re.sub(r"<[^>]+>", " ", html)
            text = re.sub(r"\s+", " ", text).strip()
            return {"title": title, "text": text}

        soup = BeautifulSoup(html, "html.parser")
        # remove non-content
        for tag in soup(["script", "style", "noscript", "footer", "nav", "aside"]):
            tag.decompose()

        candidate = soup.find("main") or soup.find("article") or soup.body or soup
        title = ""
        # prefer main/article heading, else <title>
        h = candidate.find(["h1", "h2"]) if candidate else None
        if h:
            title = h.get_text(" ", strip=True)
        elif soup.title and soup.title.string:
            title = soup.title.string.strip()

        text = (
            candidate.get_text("\n", strip=True)
            if candidate
            else soup.get_text("\n", strip=True)
        )
        text = re.sub(r"\n{2,}", "\n\n", text)
        return {"title": title, "text": text}

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        urls: List[str] = arguments.get("urls", [])
        max_chars: Optional[int] = arguments.get("max_chars")
        return_html: bool = bool(arguments.get("return_html", False))

        if not urls or not isinstance(urls, list):
            return {
                "status": "error",
                "error": "Missing required parameter 'urls' (array of 1–3 URLs).",
            }

        out: List[Dict[str, Any]] = []
        for u in urls[:3]:
            try:
                resp = requests.get(u, timeout=self.timeout, allow_redirects=True)
                ct = resp.headers.get("Content-Type", "")
                item: Dict[str, Any] = {
                    "url": u,
                    "status": resp.status_code,
                    "content_type": ct,
                }

                if "text/html" in ct or (not ct and resp.text.startswith("<!")):
                    ex = self._extract_text(resp.text)
                    if isinstance(max_chars, int) and max_chars > 0:
                        ex["text"] = ex["text"][:max_chars]
                    item.update(ex)
                    if return_html:
                        item["html"] = resp.text
                elif "pdf" in ct or u.lower().endswith(".pdf"):
                    item["title"] = "(PDF Document)"
                    item["text"] = f"[PDF file: {u}]"
                else:
                    item["title"] = ""
                    item["text"] = ""
                out.append(item)
            except requests.exceptions.RequestException as e:
                out.append(
                    {
                        "url": u,
                        "status": 0,
                        "content_type": "",
                        "title": "",
                        "text": "",
                        "error": str(e),
                    }
                )

        return {"results": out, "metadata": {"source": "ODPHP OutlinkFetch"}}
