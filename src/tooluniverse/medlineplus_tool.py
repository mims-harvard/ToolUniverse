# medlineplus_tool.py

import re
from typing import Any, Dict, Optional

import requests
import xmltodict

from .base_tool import BaseTool
from .logging_config import get_logger
from .tool_registry import register_tool

logger = get_logger("MedlinePlusRESTTool")

_HTML_TAG_RE = re.compile(r"<[^>]+>")

# The wsearch service wraps every term match in <span class="qt0">...</span>
# highlight markup in the flat `brief`/`all` content nodes. The same text in
# the `topic` <health-topic> record carries no such markup, so stripping the
# spans (keeping their inner text) makes the three rettypes agree.
_HIGHLIGHT_SPAN_RE = re.compile(r"</?span[^>]*>")

# NLM's wsearch endpoint accepts any `db` value but only actually serves the
# two health-topic databases; every query against the other historically
# documented databases returns <count>0</count>. Verified live (2026-08) for
# drugs / drugsSpanish / genetics / medicalTests / medicalEncyclopedia across
# the terms aspirin, cancer, heart, BRCA1, diabetes and vitamin -- all zero,
# while healthTopics/healthTopicsSpanish return hundreds of hits for the same
# terms. The values stay accepted so existing callers keep working; they just
# now get an explanation instead of a generic "no results".
_SERVED_SEARCH_DBS = ("healthTopics", "healthTopicsSpanish")


@register_tool("MedlinePlusRESTTool")
class MedlinePlusRESTTool(BaseTool):
    """
    MedlinePlus REST API tool class.
    Supports health topic search, code lookup, genetics information retrieval, etc.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.timeout = 10
        self.endpoint_template = tool_config["fields"]["endpoint"]
        self.param_schema = tool_config["parameter"]["properties"]

    # MedlinePlus's genetics download endpoints are case-sensitive on the
    # identifier segment: an uppercase gene symbol (e.g. "FBN1.json") 200s
    # but silently serves XML instead of the requested JSON, forcing a much
    # buggier XML-fallback parse path (confirmed live). Lowercasing matches
    # the convention already used for condition names (e.g.
    # "marfan-syndrome") and routes both endpoints through the same
    # reliably-correct real-JSON response shape.
    _LOWERCASE_URL_PARAMS = {"gene", "condition"}

    def _build_url(self, arguments: dict) -> str:
        """Build complete URL"""
        url_path = self.endpoint_template
        placeholders = re.findall(r"\{([^{}]+)\}", url_path)

        for ph in placeholders:
            if ph not in arguments:
                return {
                    "status": "error",
                    "error": f"Missing required parameter '{ph}'",
                }
            value = str(arguments[ph])
            if ph in self._LOWERCASE_URL_PARAMS:
                value = value.lower()
            url_path = url_path.replace(f"{{{ph}}}", value)

        return url_path

    @staticmethod
    def _paragraph_text(p) -> str:
        """A <html:p> paragraph from xmltodict is a bare string when it has
        no nested inline tag, or a dict when it does (e.g. <html:i>FMR1</html:i>
        splits into {"html:i": "FMR1", "#text": "The  gene provides..."} --
        xmltodict keeps the surrounding text but drops the inline tag's own
        text from "#text", leaving a double-space gap where it belongs).
        Reinsert the inline text into that gap instead of losing the word."""
        if isinstance(p, str):
            return p
        if not isinstance(p, dict):
            return ""
        text = p.get("#text", "")
        inline = next(
            (v for k, v in p.items() if k != "#text" and isinstance(v, str)), None
        )
        if inline and "  " in text:
            text = text.replace("  ", f" {inline} ", 1)
        return text

    def _extract_text_content(self, text_item: dict) -> str:
        """Extract content from text item"""
        if not isinstance(text_item, dict):
            return ""

        text = text_item.get("text", {})
        if not isinstance(text, dict):
            return ""

        html = text.get("html", "")
        if isinstance(html, dict) and "html:p" in html:
            paragraphs = html["html:p"]
            if not isinstance(paragraphs, list):
                paragraphs = [paragraphs]
            # Confirmed live: paragraphs without a nested inline tag parse as
            # bare strings, not dicts -- the previous `isinstance(p, dict)`
            # filter silently dropped every such paragraph (e.g. lost the
            # entire middle paragraph of FMR1's "function" description).
            return "\n".join(self._paragraph_text(p) for p in paragraphs)
        if isinstance(html, str):
            return _HTML_TAG_RE.sub("", html.replace("</p>", "\n")).strip()
        return ""

    @staticmethod
    def _strip_highlight(value: Any) -> str:
        """Drop the wsearch term-highlight <span> wrappers, keeping their text."""
        if not isinstance(value, str):
            return ""
        return _HIGHLIGHT_SPAN_RE.sub("", value).strip()

    @staticmethod
    def _truncate_summary(summary: Any) -> Any:
        text = summary if isinstance(summary, str) else str(summary)
        return text[:500] + "..." if len(text) > 500 else summary

    @staticmethod
    def _split_document_content(doc: dict):
        """Split a <document>'s <content> nodes into the structured
        <health-topic> record (rettype=topic / all) and a name -> [text] map
        of the flat content nodes (rettype=brief / all).

        rettype=topic yields exactly one <content name="healthTopic"> node,
        which xmltodict collapses to a bare dict; brief yields several flat
        <content name="..."> nodes (a list); all yields both in one list.
        The old code only ever looked at the dict shape, so every brief/all
        document was silently discarded.
        """
        content = doc.get("content", {})
        if isinstance(content, dict):
            entries = [content]
        elif isinstance(content, list):
            entries = [c for c in content if isinstance(c, dict)]
        else:
            entries = []

        health_topic = {}
        flat: dict[str, list] = {}
        for entry in entries:
            nested = entry.get("health-topic")
            if isinstance(nested, dict):
                health_topic = nested
                continue
            text = entry.get("#text")
            if isinstance(text, str):
                flat.setdefault(entry.get("@name", ""), []).append(text)
        return health_topic, flat

    def _format_health_topic(self, health_topic: dict, doc_url: str, doc_rank: str):
        """Format the structured <health-topic> record (rettype=topic/all)."""
        title = health_topic.get("@title", "")
        meta_desc = health_topic.get("@meta-desc", "")
        topic_url = health_topic.get("@url", doc_url)
        language = health_topic.get("@language", "")

        # Extract aliases
        also_called = health_topic.get("also-called", [])
        if isinstance(also_called, str):
            also_called = [also_called]
        elif isinstance(also_called, dict):
            also_called = [also_called.get("#text", str(also_called))]
        elif not isinstance(also_called, list):
            also_called = []

        # Extract summary
        full_summary = health_topic.get("full-summary", "")
        if isinstance(full_summary, dict):
            full_summary = str(full_summary)

        # Extract group information
        groups = health_topic.get("group", [])
        if isinstance(groups, str):
            groups = [groups]
        elif isinstance(groups, dict):
            groups = [groups.get("#text", str(groups))]
        elif not isinstance(groups, list):
            groups = []

        return {
            "title": title,
            "meta_desc": meta_desc,
            "url": topic_url,
            "language": language,
            "rank": doc_rank,
            "also_called": also_called,
            "summary": self._truncate_summary(full_summary),
            "groups": groups,
        }

    def _format_brief_document(
        self, flat: dict[str, list], doc_url: str, doc_rank: str, db: str
    ):
        """Format a rettype=brief document, whose fields arrive as flat
        <content name="title|altTitle|FullSummary|groupName|snippet"> nodes
        instead of a nested <health-topic> record."""

        def first(name: str) -> str:
            values = flat.get(name) or [""]
            return self._strip_highlight(values[0])

        # brief carries no meta-desc; the search snippet is the equivalent
        # short description the service offers for this rettype.
        snippet = first("snippet")
        # brief carries no language attribute either; it is fixed by the db.
        if db.lower().endswith("spanish"):
            language = "Spanish"
        elif db:
            language = "English"
        else:
            language = ""

        return {
            "title": first("title"),
            "meta_desc": snippet,
            "url": doc_url,
            "language": language,
            "rank": doc_rank,
            "also_called": [
                self._strip_highlight(v)
                for v in flat.get("altTitle", [])
                if self._strip_highlight(v)
            ],
            "summary": self._truncate_summary(first("FullSummary")),
            "groups": [
                self._strip_highlight(v)
                for v in flat.get("groupName", [])
                if self._strip_highlight(v)
            ],
        }

    @staticmethod
    def _no_documents_error(arguments: dict[str, Any]) -> str:
        """Explain an empty result set, naming the real cause when the caller
        targeted a `db` that wsearch accepts but never serves."""
        db = str(arguments.get("db", "") or "")
        term = str(arguments.get("term", "") or "")
        if db and db not in _SERVED_SEARCH_DBS:
            return (
                f"MedlinePlus wsearch does not serve `db={db}`; only "
                f"{' and '.join(_SERVED_SEARCH_DBS)} return results. The service "
                f"accepts the request but always answers with count=0, so this is "
                f"not a 'no match for your term' result. Retry with "
                f"db=healthTopics (or db=healthTopicsSpanish)."
            )
        where = f" in db={db}" if db else ""
        for_term = f" for term '{term}'" if term else ""
        return f"MedlinePlus returned no matching documents{for_term}{where} (count=0)."

    def _format_response(
        self,
        response: Any,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Format response content"""
        if not isinstance(response, dict):
            return {"raw_response": response}

        # Extract text content
        def get_text_content(data, role):
            text_list = data.get("text-list", [])
            if isinstance(text_list, dict):
                text_list = [text_list]
            for item in text_list:
                if isinstance(item, dict) and "text" in item:
                    text = item["text"]
                    if text.get("text-role") == role:
                        return self._extract_text_content(item)
            return ""

        # MedlinePlus genetics list fields arrive in two shapes depending on
        # the parse path (confirmed live): real JSON gives a top-level *list*
        # of single-key wrapper dicts (e.g. [{"related-gene": {...}}, ...]),
        # while the XML fallback (xmltodict) collapses the same data to a
        # *dict* ({"related-gene": [...] or {...}}). Normalize both to a flat
        # list of entries.
        def unwrap_entries(data, list_key, item_key):
            raw = data.get(list_key, [])
            if isinstance(raw, dict):
                entries = raw.get(item_key, [])
                return entries if isinstance(entries, list) else [entries]
            if isinstance(raw, list):
                return [w.get(item_key) if isinstance(w, dict) else w for w in raw]
            return []

        def get_list_items(
            data, list_key, item_key, name_key="name", url_key="ghr-page"
        ):
            formatted = []
            for item in unwrap_entries(data, list_key, item_key):
                if isinstance(item, dict):
                    name = item.get(name_key, "")
                    url = item.get(url_key, "")
                    formatted.append(f"{name} ({url})" if url else name)
            return formatted

        def get_synonyms(data):
            return [
                s
                for s in unwrap_entries(data, "synonym-list", "synonym")
                if isinstance(s, str)
            ]

        # Format response based on tool type
        if tool_name == "MedlinePlus_search_topics_by_keyword":
            arguments = arguments or {}
            logger.debug("MedlinePlus raw search response: %s", response)

            # Extract topic information from XML structure
            nlm_result = response.get("nlmSearchResult", {})
            if not nlm_result:
                return {"status": "error", "error": "nlmSearchResult node not found"}

            # Get document list
            document_list = nlm_result.get("list", {}).get("document", [])
            if not document_list:
                return {
                    "status": "error",
                    "error": self._no_documents_error(arguments),
                }

            # Ensure document_list is a list
            if isinstance(document_list, dict):
                document_list = [document_list]

            db = str(arguments.get("db", "") or "")
            formatted_topics = []
            for doc in document_list:
                if not isinstance(doc, dict):
                    continue
                # Get document basic info
                doc_url = doc.get("@url", "")
                doc_rank = doc.get("@rank", "")

                health_topic, flat = self._split_document_content(doc)
                if health_topic:
                    # rettype=topic, and rettype=all (which ships the same
                    # structured record alongside the flat fields).
                    formatted_topics.append(
                        self._format_health_topic(health_topic, doc_url, doc_rank)
                    )
                elif flat:
                    # rettype=brief: only the flat content nodes are present.
                    formatted_topics.append(
                        self._format_brief_document(flat, doc_url, doc_rank, db)
                    )

            return (
                {"topics": formatted_topics}
                if formatted_topics
                else {"error": "Failed to parse health topic information"}
            )

        elif tool_name == "MedlinePlus_get_genetics_condition_by_name":
            inheritance = [
                p.get("memo", "")
                for p in unwrap_entries(
                    response, "inheritance-pattern-list", "inheritance-pattern"
                )
                if isinstance(p, dict)
            ]

            return {
                "name": response.get("name", ""),
                "description": get_text_content(response, "description"),
                "genes": get_list_items(
                    response, "related-gene-list", "related-gene", "gene-symbol"
                ),
                "inheritance": inheritance,
                "synonyms": get_synonyms(response),
                "ghr_page": response.get("ghr_page", ""),
            }

        elif tool_name == "MedlinePlus_get_genetics_gene_by_name":
            # Real JSON responses have the gene's fields at the top level
            # (no "gene-summary" wrapper) -- that wrapper only exists in the
            # XML-parsed shape. Fall back to `response` itself so both
            # shapes work.
            gene_summary = response.get("gene-summary", response)
            return {
                "name": gene_summary.get("name", ""),
                "function": get_text_content(gene_summary, "function"),
                "health_conditions": get_list_items(
                    gene_summary,
                    "related-health-condition-list",
                    "related-health-condition",
                ),
                "synonyms": get_synonyms(gene_summary),
                "ghr_page": gene_summary.get("ghr-page", ""),
            }

        elif tool_name == "MedlinePlus_connect_lookup_by_code":
            # Handle both JSON and XML response from Connect API
            feed = response.get("feed", {})
            entries = feed.get("entry", [])

            # Ensure entries is a list
            if isinstance(entries, dict):
                entries = [entries]

            if not entries:
                return {
                    "status": "error",
                    "error": "No matching code information found",
                }

            formatted_responses = []
            for entry in entries:
                # Extract title - handle both JSON and XML formats
                title = entry.get("title", "")
                if isinstance(title, dict):
                    # JSON format: {"_value": "...", "type": "text"}
                    # XML format: {"#text": "..."}
                    title = title.get("_value", title.get("#text", str(title)))

                # Extract link - handle both JSON and XML formats
                link = entry.get("link", {})
                url = ""
                if isinstance(link, dict):
                    # JSON format: {"href": "..."}
                    # XML format: {"@href": "..."}
                    url = link.get("href", link.get("@href", ""))
                elif isinstance(link, list):
                    # Multiple links, get the first one
                    if link:
                        url = link[0].get("href", link[0].get("@href", ""))

                # Extract summary - handle both JSON and XML formats
                summary_data = entry.get("summary", {})
                summary = ""
                if isinstance(summary_data, dict):
                    # JSON format: {"_value": "...", "type": "html"}
                    # XML format: {"#text": "..."}
                    summary = summary_data.get("_value", summary_data.get("#text", ""))
                elif isinstance(summary_data, str):
                    summary = summary_data

                formatted_responses.append(
                    {
                        "title": title,
                        "summary": summary[:500] + "..."
                        if len(summary) > 500
                        else summary,
                        "url": url,
                    }
                )

            return {"responses": formatted_responses}

        elif tool_name == "MedlinePlus_get_genetics_index":
            topics = response.get("genetics_home_reference_topic_list", {}).get(
                "topic", []
            )
            return (
                {
                    "topics": [
                        {"name": t.get("name", ""), "url": t.get("url", "")}
                        for t in topics
                    ]
                }
                if topics
                else {"error": "No genetics topics found"}
            )

        return {"raw_response": response}

    def run(self, arguments: dict):
        """Execute tool call"""
        # Apply default values for optional parameters
        for key, prop in self.param_schema.items():
            if key not in arguments and "default" in prop:
                arguments[key] = prop["default"]

        # Build URL
        url = self._build_url(arguments)
        if isinstance(url, dict) and "error" in url:
            return url

        # Diagnostics go to the shared ToolUniverse logger at DEBUG level
        # (enable with TOOLUNIVERSE_LOG_LEVEL=DEBUG). They used to be bare
        # print() calls, which polluted stdout on every single call and
        # corrupted any consumer parsing the tool's JSON payload from there.
        logger.debug("Request URL: %s", url)

        # Make request
        try:
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code != 200:
                return {
                    "status": "error",
                    "error": f"MedlinePlus returned non-200 status code: {resp.status_code}",
                    "detail": resp.text,
                }

            logger.debug(
                "Response status: %s, length: %s characters",
                resp.status_code,
                len(resp.text),
            )
            logger.debug("First 500 characters of response: %s", resp.text[:500])

            # Improved parsing logic
            tool_name = self.tool_config["name"]
            response_text = resp.text.strip()

            # Decide parsing method based on tool type and content format
            format_arg = arguments.get("format", "")
            if url.endswith(".json") or (format_arg in ["json", "application/json"]):
                # JSON format
                try:
                    response = resp.json()
                    logger.debug("Parsed as: JSON")
                except Exception:
                    # If JSON parsing fails, fall back to XML
                    response = xmltodict.parse(resp.text)
                    logger.debug("Parsed as: XML -> Dictionary (fallback)")
            elif (
                url.endswith(".xml")
                or response_text.startswith("<?xml")
                or (format_arg in ["xml", "text/xml"])
            ):
                # XML format
                response = xmltodict.parse(resp.text)
                logger.debug("Parsed as: XML -> Dictionary")
            elif tool_name == "MedlinePlus_search_topics_by_keyword":
                # Search tool defaults to XML
                response = xmltodict.parse(resp.text)
                logger.debug("Parsed as: XML -> Dictionary (Search tool)")
            elif tool_name == "MedlinePlus_get_genetics_index":
                # Genetics index defaults to XML
                response = xmltodict.parse(resp.text)
                logger.debug("Parsed as: XML -> Dictionary (Genetics index)")
            else:
                # Other cases keep original text
                response = resp.text
                logger.debug("Parsed as: Plain text")

            if isinstance(response, dict):
                logger.debug("Top-level dictionary keys: %s", list(response.keys()))

            return self._format_response(response, tool_name, arguments)

        except requests.RequestException as e:
            return {
                "status": "error",
                "error": f"Failed to request MedlinePlus: {str(e)}",
            }

    # Tool methods
    def search_topics_by_keyword(
        self, term: str, db: str, rettype: str = "topic"
    ) -> Dict[str, Any]:
        return self.run({"term": term, "db": db, "rettype": rettype})

    def connect_lookup_by_code(
        self,
        cs: str,
        c: str,
        dn: Optional[str] = None,
        language: str = "en",
        format: str = "json",
    ) -> Any:
        args = {"cs": cs, "c": c, "language": language, "format": format}
        if dn:
            args["dn"] = dn
        return self.run(args)

    def get_genetics_condition_by_name(
        self, condition: str, format: str = "json"
    ) -> Any:
        return self.run({"condition": condition, "format": format})

    def get_genetics_gene_by_name(self, gene: str, format: str = "json") -> Any:
        return self.run({"gene": gene, "format": "json"})

    def get_genetics_index(self) -> Any:
        return self.run({})
