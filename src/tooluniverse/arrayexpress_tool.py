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

            # Fetch a stable 100-row upstream window, then slice the exact
            # caller offset in run(). Mapping offset directly with
            # ``offset // limit`` silently rounded arbitrary offsets down
            # (offset=5, limit=10 returned offset=0 verbatim).
            params["pageSize"] = 100

            # BioStudies uses 1-based page numbers (page=0 is normalized to 1).
            offset = args.get("offset", 0)
            page_size = params["pageSize"]
            params["page"] = (offset // page_size) + 1

        return params

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the BioStudies API call for ArrayExpress data"""
        try:
            tool_name = self.tool_config.get("name", "")
            if tool_name == "arrayexpress_search_experiments":
                limit = arguments.get("limit", 10)
                offset = arguments.get("offset", 0)
                if (
                    isinstance(limit, bool)
                    or not isinstance(limit, int)
                    or not 1 <= limit <= 100
                ):
                    return {
                        "status": "error",
                        "error": "limit must be an integer between 1 and 100",
                    }
                if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
                    return {
                        "status": "error",
                        "error": "offset must be a non-negative integer",
                    }

            url = self._build_url(arguments)
            params = self._build_params(arguments)

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
                upstream_page_size = params["pageSize"]
                within_page = offset % upstream_page_size
                required = within_page + limit
                combined_hits = list(hits)
                total_hits = int(data.get("totalHits", len(combined_hits)))
                total_hits_exact = bool(data.get("isTotalHitsExact", False))
                last_page_hits = hits
                upstream_start = (params["page"] - 1) * upstream_page_size
                if (
                    required > len(combined_hits)
                    and upstream_start + len(combined_hits) < total_hits
                ):
                    next_params = dict(params, page=params["page"] + 1)
                    next_response = self.session.get(
                        url, params=next_params, timeout=self.timeout
                    )
                    next_response.raise_for_status()
                    next_content_type = next_response.headers.get("content-type", "")
                    if "json" not in next_content_type.lower():
                        return {
                            "status": "error",
                            "error": f"API returned non-JSON content: {next_content_type}",
                            "url": next_response.url,
                        }
                    next_data = next_response.json()
                    last_page_hits = next_data.get("hits", [])
                    combined_hits.extend(last_page_hits)
                    total_hits = max(
                        total_hits,
                        int(next_data.get("totalHits", total_hits)),
                    )
                    total_hits_exact = total_hits_exact or bool(
                        next_data.get("isTotalHitsExact", False)
                    )
                selected_hits = combined_hits[within_page : within_page + limit]
                covered_through = upstream_start + len(combined_hits)
                total_hits = max(total_hits, covered_through)
                buffered_more = within_page + len(selected_hits) < len(combined_hits)
                has_more = (
                    offset + len(selected_hits) < total_hits
                    if total_hits_exact
                    else (
                        buffered_more
                        or len(last_page_hits) == upstream_page_size
                        or offset + len(selected_hits) < total_hits
                    )
                )
                transformed_data = {
                    "experiments": selected_hits,
                    "totalHits": total_hits,
                    "totalHitsExact": total_hits_exact,
                    "totalHitsRelation": "exact" if total_hits_exact else "lower_bound",
                    "returned": len(selected_hits),
                    "offset": offset,
                    "limit": limit,
                    "has_more": has_more,
                    "next_offset": offset + len(selected_hits) if has_more else None,
                    "result_set_complete": offset == 0 and not has_more,
                    "page": data.get("page", params["page"]),
                    "pageSize": limit,
                }
                if not total_hits_exact:
                    transformed_data["totalHitsWarning"] = (
                        "BioStudies reports isTotalHitsExact=false; totalHits is a "
                        "lower bound that can increase on later pages. Continue "
                        "with next_offset while has_more is true."
                    )
                return {
                    "status": "success",
                    "data": transformed_data,
                    "count": len(selected_hits),
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

        # Fix-R14C-2: the literal "Samples" section is just a wrapper
        # carrying aggregate summary attributes (e.g. "Sample count", plus
        # one "Experimental Factors" attribute per factor -- which the dict
        # build below collapses to just the last one on name collision) --
        # not per-sample data. Confirmed live via the raw BioStudies API
        # (E-GEOD-33447) that the actual per-sample-group records live one
        # level deeper, under a "Source Characteristics" subsection, as
        # "Characteristics Table" entries (one per distinct combination of
        # characteristics, e.g. age/tissue). Match those instead of the
        # aggregate wrapper; "sample" (singular) is kept for any submission
        # that uses that type directly on an individual record.
        section_type = section.get("type", "")
        if section_type.lower() in ["sample", "characteristics table"]:
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
