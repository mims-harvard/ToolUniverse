"""
BioStudies Database Tool

BioStudies is a comprehensive repository for biological study data at EMBL-EBI.
It hosts data from various collections including ArrayExpress, and supports
diverse data types from genomics to imaging and clinical trials.

This tool provides access to the BioStudies API for searching and retrieving
biological study information.
"""

import requests
from typing import Any, Dict, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

try:
    from markitdown import MarkItDown

    MARKITDOWN_AVAILABLE = True
except ImportError:
    MARKITDOWN_AVAILABLE = False


@register_tool("BioStudiesRESTTool")
class BioStudiesRESTTool(BaseTool):
    """
    BioStudies REST API tool.

    BioStudies is a general-purpose repository for biological studies at EMBL-EBI.
    It provides access to diverse study types including genomics, transcriptomics,
    proteomics, imaging, and more.
    """

    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.base_url = "https://www.ebi.ac.uk/biostudies/api/v1"
        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/json", "User-Agent": "ToolUniverse/1.0"}
        )
        self.timeout = 30

        # Initialize MarkItDown if available
        if MARKITDOWN_AVAILABLE:
            self.md_converter = MarkItDown()
        else:
            self.md_converter = None

    def _build_url(self, args: Dict[str, Any]) -> str:
        """Build URL from arguments"""
        tool_name = self.tool_config.get("name", "")

        if tool_name == "biostudies_search":
            return f"{self.base_url}/search"

        elif tool_name == "biostudies_get_study":
            accession = args.get("accession", "")
            if accession:
                return f"{self.base_url}/studies/{accession}"

        elif tool_name == "biostudies_get_study_files":
            accession = args.get("accession", "")
            if accession:
                # Note: files endpoint doesn't exist, we get files from study details
                return f"{self.base_url}/studies/{accession}"

        elif tool_name == "biostudies_search_by_collection":
            # Collection goes in URL path per API docs: /api/v1/{collection}/search
            collection = args.get("collection", "")
            if collection:
                return f"{self.base_url}/{collection}/search"
            return f"{self.base_url}/search"

        return f"{self.base_url}/search"

    def _build_params(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Build query parameters for BioStudies API"""
        params = {}
        tool_name = self.tool_config.get("name", "")

        if tool_name in ["biostudies_search", "biostudies_search_by_collection"]:
            # Build search query
            if "query" in args:
                params["query"] = args["query"]
            else:
                params["query"] = "*"  # Default to all

            # Note: for biostudies_search_by_collection, collection is in URL path, not params
            # For biostudies_search, collection can still be used as a filter
            if tool_name == "biostudies_search" and "collection" in args:
                params["collection"] = args["collection"]

            # Pagination
            page_size = args.get("pageSize", args.get("limit", 10))
            params["pageSize"] = min(page_size, 100)

            page = args.get("page", 1)
            params["page"] = page

            # Sorting
            if "sortBy" in args:
                params["sortBy"] = args["sortBy"]
            if "sortOrder" in args:
                params["sortOrder"] = args["sortOrder"]

        return params

    def _convert_html_to_markdown(self, html_content: str, url: str) -> str:
        """Convert HTML content to Markdown using markitdown"""
        if not self.md_converter:
            return html_content

        try:
            # markitdown expects file-like or string
            result = self.md_converter.convert_stream(html_content)
            return (
                result.text_content if hasattr(result, "text_content") else str(result)
            )
        except Exception as e:
            return f"[Could not convert HTML to Markdown: {str(e)}]\n\n{html_content[:500]}..."

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the BioStudies API call"""
        try:
            url = self._build_url(arguments)
            params = self._build_params(arguments)
            tool_name = self.tool_config.get("name", "")

            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            # Check content type
            content_type = response.headers.get("content-type", "")

            if "json" in content_type.lower():
                data = response.json()

                # Format response based on tool type
                if tool_name in [
                    "biostudies_search",
                    "biostudies_search_by_collection",
                ]:
                    hits = data.get("hits", [])
                    return {
                        "status": "success",
                        "data": {
                            "hits": hits,
                            "totalHits": data.get("totalHits", 0),
                            "page": data.get("page", 1),
                            "pageSize": data.get("pageSize", len(hits)),
                            "sortBy": data.get("sortBy"),
                            "sortOrder": data.get("sortOrder"),
                        },
                        "count": len(hits),
                        "url": response.url,
                    }

                elif tool_name == "biostudies_get_study":
                    return {
                        "status": "success",
                        "data": data,
                        "url": response.url,
                    }

                elif tool_name == "biostudies_get_study_files":
                    # Extract file list from response
                    files = self._extract_files(data)
                    return {
                        "status": "success",
                        "data": files,
                        "count": len(files),
                        "url": response.url,
                    }

                else:
                    # Generic response
                    return {
                        "status": "success",
                        "data": data,
                        "url": response.url,
                    }

            elif "html" in content_type.lower():
                # Handle HTML response using markitdown
                html_content = response.text

                if self.md_converter:
                    markdown_content = self._convert_html_to_markdown(
                        html_content, response.url
                    )
                    return {
                        "status": "success",
                        "data": {
                            "format": "markdown",
                            "content": markdown_content,
                            "original_format": "html",
                            "note": "HTML response converted to Markdown using markitdown",
                        },
                        "url": response.url,
                    }
                else:
                    return {
                        "status": "warning",
                        "data": {
                            "format": "html",
                            "content": html_content,
                            "note": "HTML response returned (markitdown not available for conversion)",
                        },
                        "url": response.url,
                    }

            else:
                # Unknown content type
                return {
                    "status": "warning",
                    "data": {
                        "format": content_type,
                        "content": response.text,
                        "note": f"Unexpected content type: {content_type}",
                    },
                    "url": response.url,
                }

        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"BioStudies API error: {str(e)}",
                "url": url if "url" in locals() else None,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error: {str(e)}",
                "url": url if "url" in locals() else None,
            }

    def _extract_files(self, data: Any) -> list:
        """Extract file list from BioStudies response"""
        files = []

        if isinstance(data, dict):
            # If data has a section, extract files from it
            if "section" in data:
                files = self._extract_files_from_section(data["section"])
            # If data has direct files array
            elif "files" in data and isinstance(data["files"], list):
                for file_obj in data["files"]:
                    if isinstance(file_obj, dict):
                        files.append(
                            {
                                "path": file_obj.get("path", file_obj.get("name", "")),
                                "size": file_obj.get("size", 0),
                                "type": file_obj.get("type", ""),
                                "attributes": file_obj.get("attributes", []),
                            }
                        )
        elif isinstance(data, list):
            # If data is directly a list of files
            for file_obj in data:
                if isinstance(file_obj, dict):
                    files.append(
                        {
                            "path": file_obj.get("path", file_obj.get("name", "")),
                            "size": file_obj.get("size", 0),
                            "type": file_obj.get("type", ""),
                        }
                    )

        return files

    def _extract_files_from_section(self, section: Dict[str, Any]) -> list:
        """Extract files from a BioStudies section (recursive)"""
        files = []

        # Add files from current section
        if "files" in section and isinstance(section["files"], list):
            for file_obj in section["files"]:
                if isinstance(file_obj, dict):
                    files.append(
                        {
                            "path": file_obj.get("path", file_obj.get("name", "")),
                            "size": file_obj.get("size", 0),
                            "type": file_obj.get("type", ""),
                            "attributes": file_obj.get("attributes", []),
                        }
                    )

        # Recursively extract from subsections
        if "subsections" in section and isinstance(section["subsections"], list):
            for subsection_group in section["subsections"]:
                if isinstance(subsection_group, list):
                    for subsection in subsection_group:
                        if isinstance(subsection, dict):
                            files.extend(self._extract_files_from_section(subsection))
                elif isinstance(subsection_group, dict):
                    files.extend(self._extract_files_from_section(subsection_group))

        return files
