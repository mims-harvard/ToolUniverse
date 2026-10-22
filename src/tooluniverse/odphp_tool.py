import json
import re
import requests
from urllib.parse import urlparse
from typing import Dict, Any, Optional, List
from .base_tool import BaseTool
from .tool_registry import register_tool

# Optional but recommended: text extraction for HTML
try:
    from bs4 import BeautifulSoup  # pip install beautifulsoup4
except ImportError:
    BeautifulSoup = None  # We’ll guard uses so the tool still loads

ODPHP_BASE_URL = "https://odphp.health.gov/myhealthfinder/api/v4"


def _application_error(value: Any) -> Optional[str]:
    """Return an upstream application error while accepting its string false flag."""
    if value is None or value is False:
        return None
    if isinstance(value, str) and value.strip().casefold() in {
        "",
        "false",
        "0",
        "no",
        "none",
    }:
        return None
    return str(value)


def _returned_record_count(result: Dict[str, Any]) -> Optional[int]:
    """Count records in each documented v4 result shape."""
    resources = result.get("Resources")
    if isinstance(resources, dict):
        all_resources = resources.get("All")
        if isinstance(all_resources, dict) and isinstance(
            all_resources.get("Resource"), list
        ):
            count = len(all_resources["Resource"])
            callouts = result.get("Callouts")
            if isinstance(callouts, dict):
                all_callouts = callouts.get("All")
                if isinstance(all_callouts, dict) and isinstance(
                    all_callouts.get("Resource"), list
                ):
                    count += len(all_callouts["Resource"])
            return count
        if isinstance(resources.get("Resource"), list):
            return len(resources["Resource"])
    items = result.get("Items")
    if isinstance(items, dict) and isinstance(items.get("Item"), list):
        return len(items["Item"])
    return 0 if result.get("Total") == 0 else None


def _query_mismatches(
    params: Optional[Dict[str, Any]], query: Any
) -> List[Dict[str, Any]]:
    """Find request values silently ignored or changed by the upstream API."""
    if not params:
        return []
    if not isinstance(query, dict):
        return [
            {
                "parameter": key,
                "requested": value,
                "returned": None,
            }
            for key, value in params.items()
        ]
    echoed = {str(key).casefold(): value for key, value in query.items()}
    mismatches = []
    for key, requested in params.items():
        returned = echoed.get(key.casefold())
        if str(returned).strip().casefold() != str(requested).strip().casefold():
            mismatches.append(
                {
                    "parameter": key,
                    "requested": requested,
                    "returned": returned,
                }
            )
    return mismatches


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
            if not isinstance(data, dict) or not isinstance(data.get("Result"), dict):
                return {
                    "status": "error",
                    "error": "ODPHP response did not contain a Result object",
                    "metadata": {"source": "ODPHP MyHealthfinder", "endpoint": url},
                }
            result = data["Result"]
            upstream_error = _application_error(result.get("Error"))
            if upstream_error:
                return {
                    "status": "error",
                    "error": f"ODPHP application error: {upstream_error}",
                    "metadata": {
                        "source": "ODPHP MyHealthfinder",
                        "endpoint": url,
                        "query": params,
                        "http_status": resp.status_code,
                        "requested_scope_complete": False,
                    },
                }
            mismatches = _query_mismatches(params, result.get("Query"))
            if mismatches:
                return {
                    "status": "error",
                    "error": "ODPHP ignored or changed one or more query parameters",
                    "parameter_mismatches": mismatches,
                    "metadata": {
                        "source": "ODPHP MyHealthfinder",
                        "endpoint": url,
                        "query": params,
                        "http_status": resp.status_code,
                        "requested_scope_complete": False,
                    },
                }
            reported_total = result.get("Total")
            returned_records = _returned_record_count(result)
            result_set_complete = (
                isinstance(reported_total, int)
                and returned_records is not None
                and returned_records == reported_total
            )
            return {
                "status": "success",
                "data": result,
                "metadata": {
                    "source": "ODPHP MyHealthfinder",
                    "endpoint": url,
                    "query": params,
                    "http_status": resp.status_code,
                    "reported_total": reported_total,
                    "returned_records": returned_records,
                    "result_set_complete": result_set_complete,
                    "requested_scope_complete": result_set_complete,
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
        return_html = arguments.get("return_html", False)

        if not urls or not isinstance(urls, list):
            return {
                "status": "error",
                "error": "Missing required parameter 'urls' (array of 1–3 URLs).",
            }
        if len(urls) > 3:
            return {
                "status": "error",
                "error": "urls must contain between 1 and 3 entries; no URL was fetched",
            }
        for url in urls:
            parsed = urlparse(url) if isinstance(url, str) else None
            if (
                not isinstance(url, str)
                or not url.strip()
                or parsed is None
                or parsed.scheme not in ("http", "https")
                or not parsed.netloc
            ):
                return {
                    "status": "error",
                    "error": "every urls entry must be an absolute HTTP(S) URL",
                }
        if max_chars is not None and (
            isinstance(max_chars, bool)
            or not isinstance(max_chars, int)
            or not 1 <= max_chars <= 1_000_000
        ):
            return {
                "status": "error",
                "error": "max_chars must be an integer from 1 to 1000000",
            }
        if not isinstance(return_html, bool):
            return {"status": "error", "error": "return_html must be a boolean"}

        def set_text(item: Dict[str, Any], text: str) -> None:
            original_chars = len(text)
            truncated = max_chars is not None and original_chars > max_chars
            item["text"] = text[:max_chars] if truncated else text
            item["original_text_chars"] = original_chars
            item["text_truncated"] = truncated

        out: List[Dict[str, Any]] = []
        for u in urls:
            try:
                resp = requests.get(u, timeout=self.timeout, allow_redirects=True)
                ct = resp.headers.get("Content-Type", "")
                item: Dict[str, Any] = {
                    "url": u,
                    "status": resp.status_code,
                    "content_type": ct,
                }

                if not 200 <= resp.status_code < 300:
                    item.update(
                        {
                            "title": "",
                            "text": "",
                            "original_text_chars": 0,
                            "text_truncated": False,
                            "error": "HTTP {} fetching URL".format(resp.status_code),
                        }
                    )
                elif "text/html" in ct or (not ct and resp.text.startswith("<!")):
                    ex = self._extract_text(resp.text)
                    item["title"] = ex["title"]
                    set_text(item, ex["text"])
                    if return_html:
                        item["html"] = resp.text
                elif "json" in ct:
                    try:
                        payload = resp.json()
                    except ValueError:
                        item.update(
                            {
                                "title": "",
                                "text": "",
                                "original_text_chars": 0,
                                "text_truncated": False,
                                "error": "Response declared JSON but was invalid",
                            }
                        )
                    else:
                        result = (
                            payload.get("Result") if isinstance(payload, dict) else None
                        )
                        upstream_error = (
                            _application_error(result.get("Error"))
                            if isinstance(result, dict)
                            else None
                        )
                        item["title"] = "(JSON Document)"
                        set_text(
                            item, json.dumps(payload, ensure_ascii=False, indent=2)
                        )
                        if upstream_error:
                            item["error"] = (
                                f"JSON document reports application error: {upstream_error}"
                            )
                elif "pdf" in ct or u.lower().endswith(".pdf"):
                    item["title"] = "(PDF Document)"
                    set_text(item, f"[PDF file: {u}]")
                elif ct.lower().startswith("text/"):
                    item["title"] = ""
                    set_text(item, resp.text)
                else:
                    item["title"] = ""
                    item["text"] = ""
                    item["original_text_chars"] = 0
                    item["text_truncated"] = False
                    item["note"] = (
                        "Binary or unsupported content type; content not decoded"
                    )
                out.append(item)
            except requests.exceptions.RequestException as e:
                out.append(
                    {
                        "url": u,
                        "status": 0,
                        "content_type": "",
                        "title": "",
                        "text": "",
                        "original_text_chars": 0,
                        "text_truncated": False,
                        "error": str(e),
                    }
                )

        failures = sum(1 for item in out if item.get("error"))
        return {
            "results": out,
            "metadata": {
                "source": "ODPHP OutlinkFetch",
                "requested_urls": len(urls),
                "processed_urls": len(out),
                "failed_urls": failures,
                "all_urls_processed": len(out) == len(urls),
                "requested_scope_complete": failures == 0 and len(out) == len(urls),
            },
        }
