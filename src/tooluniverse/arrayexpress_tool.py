"""
ArrayExpress Database Tool (Original Source)

This tool provides access to the ORIGINAL ArrayExpress database for functional
genomics experiments including microarray and RNA-seq data.

ArrayExpress is the authoritative source for functional genomics data. While the
underlying infrastructure has migrated to BioStudies, this tool specifically
accesses the ArrayExpress collection, maintaining the original ArrayExpress
interface and data structure.
"""

import requests
from typing import Any, Dict, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("ArrayExpressRESTTool")
class ArrayExpressRESTTool(BaseTool):
    """
    ArrayExpress REST API tool - Original ArrayExpress Database.

    Accesses the official ArrayExpress functional genomics database.
    ArrayExpress is the authoritative source for gene expression data,
    microarray experiments, and RNA-seq studies from EBI.

    The database infrastructure uses BioStudies backend for improved
    performance and integration, but this tool specifically queries
    the ArrayExpress collection to maintain the original data source.
    """

    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        # ArrayExpress collection via BioStudies API
        # This IS the original ArrayExpress - just modern infrastructure
        self.base_url = "https://www.ebi.ac.uk/biostudies/api/v1"
        self.collection = "arrayexpress"  # Original ArrayExpress data
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "ToolUniverse/ArrayExpress/1.0",
            }
        )
        self.timeout = 30

    def _build_url(self, args: Dict[str, Any]) -> str:
        """Build URL from endpoint template and arguments (BioStudies API)"""
        tool_name = self.tool_config.get("name", "")

        if tool_name == "arrayexpress_search_experiments":
            return f"{self.base_url}/search"

        elif tool_name == "arrayexpress_get_experiment":
            experiment_id = args.get("experiment_id", "")
            if experiment_id:
                return f"{self.base_url}/studies/{experiment_id}"

        elif tool_name == "arrayexpress_get_experiment_files":
            experiment_id = args.get("experiment_id", "")
            if experiment_id:
                return f"{self.base_url}/studies/{experiment_id}"

        elif tool_name == "arrayexpress_get_experiment_samples":
            experiment_id = args.get("experiment_id", "")
            if experiment_id:
                return f"{self.base_url}/studies/{experiment_id}"

        return f"{self.base_url}/search"

    def _build_params(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Build query parameters for BioStudies API"""
        params = {}
        tool_name = self.tool_config.get("name", "")

        if tool_name == "arrayexpress_search_experiments":
            # Build search query for BioStudies
            query_parts = []

            if "keywords" in args:
                query_parts.append(args["keywords"])
            if "species" in args:
                query_parts.append(args["species"])
            if "array" in args:
                query_parts.append(args["array"])

            if query_parts:
                params["query"] = " ".join(query_parts)
            else:
                params["query"] = "*"  # Default to all

            # CRITICAL: Always filter to ArrayExpress collection
            # This ensures we query the ORIGINAL ArrayExpress database only,
            # not the broader BioStudies repository
            params["collection"] = "arrayexpress"

            # Map limit to pageSize
            limit = args.get("limit", 10)
            params["pageSize"] = min(limit, 100)

            # Map offset to page number (BioStudies uses 1-based page numbers)
            offset = args.get("offset", 0)
            page_size = params["pageSize"]
            params["page"] = (offset // page_size) + 1

        return params

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the BioStudies API call for ArrayExpress data"""
        try:
            url = self._build_url(arguments)
            params = self._build_params(arguments)
            tool_name = self.tool_config.get("name", "")

            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            # Check content type
            content_type = response.headers.get("content-type", "")
            if "json" not in content_type.lower():
                return {
                    "status": "error",
                    "error": f"API returned non-JSON content: {content_type}",
                    "url": response.url,
                }

            data = response.json()

            # Transform BioStudies response to match expected ArrayExpress format
            if tool_name == "arrayexpress_search_experiments":
                # BioStudies search response
                hits = data.get("hits", [])
                transformed_data = {
                    "experiments": hits,
                    "totalHits": data.get("totalHits", 0),
                    "page": data.get("page", 1),
                    "pageSize": data.get("pageSize", len(hits)),
                }
                return {
                    "status": "success",
                    "data": transformed_data,
                    "count": len(hits),
                    "url": response.url,
                }

            elif tool_name == "arrayexpress_get_experiment":
                # BioStudies study response
                return {
                    "status": "success",
                    "data": data,
                    "url": response.url,
                }

            elif tool_name == "arrayexpress_get_experiment_files":
                # Extract files from BioStudies study
                files = []
                if "section" in data:
                    section = data.get("section", {})
                    files = self._extract_files_from_section(section)

                return {
                    "status": "success",
                    "data": files,
                    "count": len(files),
                    "url": response.url,
                }

            elif tool_name == "arrayexpress_get_experiment_samples":
                # Extract samples from BioStudies study
                samples = []
                if "section" in data:
                    section = data.get("section", {})
                    samples = self._extract_samples_from_section(section)

                return {
                    "status": "success",
                    "data": samples,
                    "count": len(samples),
                    "url": response.url,
                }

            else:
                # Generic response
                return {
                    "status": "success",
                    "data": data,
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

    def _extract_files_from_section(self, section: Dict[str, Any]) -> list:
        """Extract files from a BioStudies section"""
        files = []

        # Add files from current section
        if "files" in section and isinstance(section["files"], list):
            for file_obj in section["files"]:
                if isinstance(file_obj, dict):
                    files.append(
                        {
                            "name": file_obj.get("path", file_obj.get("name", "")),
                            "size": file_obj.get("size", 0),
                            "type": file_obj.get("type", ""),
                        }
                    )

        # Recursively extract from subsections
        # Note: BioStudies subsections can be a list of lists
        if "subsections" in section and isinstance(section["subsections"], list):
            for subsection_group in section["subsections"]:
                # Handle both list of dicts and list of lists
                if isinstance(subsection_group, list):
                    for subsection in subsection_group:
                        if isinstance(subsection, dict):
                            files.extend(self._extract_files_from_section(subsection))
                elif isinstance(subsection_group, dict):
                    files.extend(self._extract_files_from_section(subsection_group))

        return files

    def _extract_samples_from_section(self, section: Dict[str, Any]) -> list:
        """Extract sample information from a BioStudies section"""
        samples = []

        # Check if current section is a sample
        section_type = section.get("type", "")
        if section_type.lower() in ["samples", "sample"]:
            # Extract sample attributes
            if "attributes" in section and isinstance(section["attributes"], list):
                sample_data = {}
                for attr in section["attributes"]:
                    if isinstance(attr, dict):
                        sample_data[attr.get("name", "")] = attr.get("value", "")
                if sample_data:
                    samples.append(sample_data)

        # Look for subsections that might contain sample data
        # Note: BioStudies subsections can be a list of lists
        if "subsections" in section and isinstance(section["subsections"], list):
            for subsection_group in section["subsections"]:
                # Handle both list of dicts and list of lists
                if isinstance(subsection_group, list):
                    for subsection in subsection_group:
                        if isinstance(subsection, dict):
                            samples.extend(
                                self._extract_samples_from_section(subsection)
                            )
                elif isinstance(subsection_group, dict):
                    samples.extend(self._extract_samples_from_section(subsection_group))

        return samples
