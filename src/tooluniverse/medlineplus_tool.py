# medlineplus_tool.py

import requests
import xmltodict
from typing import Optional, Dict, Any
import re
import json

from .base_tool import BaseTool
from .tool_registry import register_tool


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
            url_path = url_path.replace(f"{{{ph}}}", str(arguments[ph]))

        return url_path

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
            if isinstance(paragraphs, list):
                return "\n".join(
                    [
                        p.get("#text", "")
                        for p in paragraphs
                        if isinstance(p, dict) and "#text" in p
                    ]
                )
        return html.replace("<p>", "").replace("</p>", "\n")

    def _format_response(self, response: Any, tool_name: str) -> Dict[str, Any]:
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

        # Extract list items
        def get_list_items(
            data, list_key, item_key, name_key="name", url_key="ghr-page"
        ):
            items = []
            list_data = data.get(list_key, {})
            if isinstance(list_data, dict):
                items = list_data.get(item_key, [])
                if not isinstance(items, list):
                    items = [items]
            for item in items:
                if isinstance(item, dict):
                    name = item.get(name_key, "")
                    url = item.get(url_key, "")
                    items.append(f"{name} ({url})" if url else name)
            return items

        # Format response based on tool type
        if tool_name == "MedlinePlus_search_topics_by_keyword":
            # First print raw response for debugging
            print("\n🔍 Raw response structure:")
            print(
                json.dumps(response, indent=2, ensure_ascii=False)[:2000] + "..."
                if len(json.dumps(response, indent=2, ensure_ascii=False)) > 2000
                else json.dumps(response, indent=2, ensure_ascii=False)
            )

            # Extract topic information from XML structure
            nlm_result = response.get("nlmSearchResult", {})
            if not nlm_result:
                return {"status": "error", "error": "nlmSearchResult node not found"}

            # Get document list
            document_list = nlm_result.get("list", {}).get("document", [])
            if not document_list:
                return {"status": "error", "error": "document list not found"}

            # Ensure document_list is a list
            if isinstance(document_list, dict):
                document_list = [document_list]

            formatted_topics = []
            for doc in document_list:
                # Get document basic info
                doc_url = doc.get("@url", "")
                doc_rank = doc.get("@rank", "")

                # Get content node
                content = doc.get("content", {})
                if isinstance(content, dict):
                    health_topic = content.get("health-topic", {})
                    if health_topic:
                        # Extract health topic information
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

                        formatted_topics.append(
                            {
                                "title": title,
                                "meta_desc": meta_desc,
                                "url": topic_url,
                                "language": language,
                                "rank": doc_rank,
                                "also_called": also_called,
                                "summary": (
                                    full_summary[:500] + "..."
                                    if len(str(full_summary)) > 500
                                    else full_summary
                                ),
                                "groups": groups,
                            }
                        )

            return (
                {"topics": formatted_topics}
                if formatted_topics
                else {"error": "Failed to parse health topic information"}
            )

        elif tool_name == "MedlinePlus_get_genetics_condition_by_name":
            return {
                "name": response.get("name", ""),
                "description": get_text_content(response, "description"),
                "genes": get_list_items(
                    response, "related-gene-list", "related-gene", "gene-symbol"
                ),
                "synonyms": [
                    s.get("synonym", "") for s in response.get("synonym-list", [])
                ],
                "ghr_page": response.get("ghr_page", ""),
            }

        elif tool_name == "MedlinePlus_get_genetics_gene_by_name":
            gene_summary = response.get("gene-summary", {})
            return {
                "name": gene_summary.get("name", ""),
                "function": get_text_content(gene_summary, "function"),
                "health_conditions": get_list_items(
                    gene_summary,
                    "related-health-condition-list",
                    "related-health-condition",
                ),
                "synonyms": gene_summary.get("synonym-list", {}).get("synonym", []),
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

        # Print complete URL
        print(f"\n🔗 Request URL: {url}")

        # Make request
        try:
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code != 200:
                return {
                    "status": "error",
                    "error": f"MedlinePlus returned non-200 status code: {resp.status_code}",
                    "detail": resp.text,
                }

            print(f"\n📊 Response status: {resp.status_code}")
            print(f"📏 Response length: {len(resp.text)} characters")
            print(f"🔤 First 500 characters of response: {resp.text[:500]}...")

            # Improved parsing logic
            tool_name = self.tool_config["name"]
            response_text = resp.text.strip()

            # Decide parsing method based on tool type and content format
            format_arg = arguments.get("format", "")
            if url.endswith(".json") or (format_arg in ["json", "application/json"]):
                # JSON format
                try:
                    response = resp.json()
                    print("📋 Parsed as: JSON")
                except Exception:
                    # If JSON parsing fails, fall back to XML
                    response = xmltodict.parse(resp.text)
                    print("📋 Parsed as: XML -> Dictionary (fallback)")
            elif (
                url.endswith(".xml")
                or response_text.startswith("<?xml")
                or (format_arg in ["xml", "text/xml"])
            ):
                # XML format
                response = xmltodict.parse(resp.text)
                print("📋 Parsed as: XML -> Dictionary")
            elif tool_name == "MedlinePlus_search_topics_by_keyword":
                # Search tool defaults to XML
                response = xmltodict.parse(resp.text)
                print("📋 Parsed as: XML -> Dictionary (Search tool)")
            elif tool_name == "MedlinePlus_get_genetics_index":
                # Genetics index defaults to XML
                response = xmltodict.parse(resp.text)
                print("📋 Parsed as: XML -> Dictionary (Genetics index)")
            else:
                # Other cases keep original text
                response = resp.text
                print("📋 Parsed as: Plain text")

            print(f"🔍 Parsed data type: {type(response)}")
            if isinstance(response, dict):
                print(f"🗝️ Top-level dictionary keys: {list(response.keys())}")

            return self._format_response(response, tool_name)

        except requests.RequestException as e:
            return {
                "status": "error",
                "error": f"Failed to request MedlinePlus: {str(e)}",
            }

    # Tool methods
    def search_topics_by_keyword(
        self, term: str, db: str, rettype: str = "brief"
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
