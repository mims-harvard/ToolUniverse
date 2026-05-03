"""
MetaboLights Database Tool

This tool provides access to the MetaboLights database, the largest repository
of metabolomics experiments and raw data.
"""

import requests
from typing import Any, Dict
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("MetaboLightsRESTTool")
class MetaboLightsRESTTool(BaseTool):
    """
    MetaboLights REST API tool.
    Generic wrapper for MetaboLights API endpoints defined in metabolights_tools.json.
    """

    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.base_url = "https://www.ebi.ac.uk/metabolights/ws"
        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/json", "User-Agent": "ToolUniverse/1.0"}
        )
        self.timeout = 30

    def _build_url(self, args: Dict[str, Any]) -> str:
        """Build URL from endpoint template and arguments"""
        endpoint_template = self.tool_config["fields"].get("endpoint", "")
        tool_name = self.tool_config.get("name", "")

        if endpoint_template:
            url = endpoint_template
            for k, v in args.items():
                url = url.replace(f"{{{k}}}", str(v))
            return url

        # Build URL based on tool name
        if tool_name == "metabolights_list_studies":
            return f"{self.base_url}/studies"

        elif tool_name == "metabolights_get_study":
            study_id = args.get("study_id", "")
            if study_id:
                return f"{self.base_url}/studies/{study_id}"

        elif tool_name == "metabolights_search_studies":
            return f"{self.base_url}/studies"

        elif tool_name == "metabolights_get_study_assays":
            study_id = args.get("study_id", "")
            if study_id:
                return f"{self.base_url}/studies/{study_id}/assays"

        elif tool_name == "metabolights_get_study_samples":
            study_id = args.get("study_id", "")
            if study_id:
                return f"{self.base_url}/studies/{study_id}/samples"

        elif tool_name == "metabolights_get_study_files":
            study_id = args.get("study_id", "")
            if study_id:
                return f"{self.base_url}/studies/{study_id}/files"

        return self.base_url

    def _build_params(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Build query parameters for MetaboLights API"""
        params = {}
        tool_name = self.tool_config.get("name", "")

        if tool_name == "metabolights_search_studies":
            if "query" in args:
                params["query"] = args["query"]
            if "size" in args:
                params["size"] = args["size"]
            if "page" in args:
                params["page"] = args["page"]

        elif tool_name == "metabolights_list_studies":
            if "size" in args:
                params["size"] = args["size"]
            if "page" in args:
                params["page"] = args["page"]

        elif tool_name == "metabolights_get_study_data_files":
            # Required parameters for data-files endpoint
            if "search_pattern" in args:
                params["search_pattern"] = args["search_pattern"]
            if "file_match" in args:
                params["file_match"] = str(args["file_match"]).lower()
            if "folder_match" in args:
                params["folder_match"] = str(args["folder_match"]).lower()

        return params

    def _extract_samples_from_study(self, study_id: str) -> Dict[str, Any]:
        """Extract sample information from study endpoint as fallback"""
        try:
            study_url = f"{self.base_url}/studies/{study_id}"
            response = self.session.get(study_url, timeout=self.timeout)
            response.raise_for_status()
            study_data = response.json()

            samples_info = {
                "samples": [],
                "note": "Samples extracted from study endpoint (samples API endpoint unavailable)",
            }

            # Extract samples from ISA investigation structure
            if "isaInvestigation" in study_data:
                isa = study_data["isaInvestigation"]

                # Check studies array for materials/samples
                if "studies" in isa and isinstance(isa["studies"], list):
                    for study_item in isa["studies"]:
                        if isinstance(study_item, dict):
                            # Check for materials (samples)
                            if "materials" in study_item:
                                materials = study_item["materials"]
                                if isinstance(materials, list):
                                    for material in materials:
                                        if isinstance(material, dict):
                                            samples_info["samples"].append(material)

                            # Check for samples directly
                            if "samples" in study_item:
                                samples = study_item["samples"]
                                if isinstance(samples, list):
                                    for sample in samples:
                                        if isinstance(sample, dict):
                                            samples_info["samples"].append(sample)

            samples_info["count"] = len(samples_info["samples"])
            return samples_info

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to extract samples from study endpoint: {str(e)}",
            }

    def _extract_files_from_study(self, study_id: str) -> Dict[str, Any]:
        """Extract file information from study endpoint as fallback"""
        try:
            study_url = f"{self.base_url}/studies/{study_id}"
            response = self.session.get(study_url, timeout=self.timeout)
            response.raise_for_status()
            study_data = response.json()

            files_info = {
                "files": [],
                "file_urls": {},
                "note": "Files extracted from study endpoint (files API endpoint unavailable)",
            }

            # Extract file URLs from study data
            if "mtblsStudy" in study_data:
                study = study_data["mtblsStudy"]

                # Get FTP and HTTP URLs
                if "studyFtpUrl" in study and study["studyFtpUrl"]:
                    files_info["file_urls"]["ftp"] = study["studyFtpUrl"]
                if "studyHttpUrl" in study and study["studyHttpUrl"]:
                    files_info["file_urls"]["http"] = study["studyHttpUrl"]
                if "studyGlobusUrl" in study and study["studyGlobusUrl"]:
                    files_info["file_urls"]["globus"] = study["studyGlobusUrl"]

            # Extract ISA investigation file references
            if "isaInvestigation" in study_data:
                isa = study_data["isaInvestigation"]

                # Check for filename
                if "filename" in isa and isa["filename"]:
                    files_info["files"].append(
                        {
                            "name": isa["filename"],
                            "type": "investigation",
                            "source": "isaInvestigation",
                        }
                    )

                # Check studies array for files
                if "studies" in isa and isinstance(isa["studies"], list):
                    for study_item in isa["studies"]:
                        if isinstance(study_item, dict) and "filename" in study_item:
                            files_info["files"].append(
                                {
                                    "name": study_item["filename"],
                                    "type": "study",
                                    "source": "isaInvestigation.studies",
                                }
                            )

            files_info["count"] = len(files_info["files"])
            files_info["has_urls"] = len(files_info["file_urls"]) > 0

            return files_info

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to extract files from study endpoint: {str(e)}",
            }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the MetaboLights API call"""
        tool_name = self.tool_config.get("name", "")

        try:
            url = self._build_url(arguments)
            params = self._build_params(arguments)

            response = self.session.get(url, params=params, timeout=self.timeout)

            # Handle samples endpoint 400 errors with fallback
            if (
                tool_name == "metabolights_get_study_samples"
                and response.status_code == 400
            ):
                study_id = arguments.get("study_id", "")
                if study_id:
                    # Try to extract samples from study endpoint
                    fallback_data = self._extract_samples_from_study(study_id)

                    if "error" not in fallback_data:
                        return {
                            "status": "success",
                            "data": fallback_data.get("samples", []),
                            "url": url,
                            "count": fallback_data.get("count", 0),
                            "note": fallback_data.get("note", ""),
                            "fallback_used": True,
                            "original_error": "Samples endpoint returned 400 error, used study endpoint fallback",
                        }
                    else:
                        return {
                            "status": "error",
                            "error": f"Samples endpoint returned 400 error for study {study_id}. Fallback to study endpoint also failed.",
                            "url": url,
                            "suggestion": f"Access samples via MetaboLights website: https://www.ebi.ac.uk/metabolights/studies/{study_id}",
                        }

            # Handle files endpoint 500 errors with fallback
            if (
                tool_name == "metabolights_get_study_files"
                and response.status_code == 500
            ):
                study_id = arguments.get("study_id", "")
                if study_id:
                    # Try to extract files from study endpoint
                    fallback_data = self._extract_files_from_study(study_id)

                    if "error" not in fallback_data:
                        return {
                            "status": "success",
                            "data": fallback_data.get("files", []),
                            "file_urls": fallback_data.get("file_urls", {}),
                            "url": url,
                            "count": fallback_data.get("count", 0),
                            "note": fallback_data.get("note", ""),
                            "fallback_used": True,
                            "original_error": "Files endpoint returned 500 error, used study endpoint fallback",
                        }
                    else:
                        return {
                            "status": "error",
                            "error": f"Files endpoint returned server error (500) for study {study_id}. Fallback to study endpoint also failed.",
                            "url": url,
                            "suggestion": f"Access files via MetaboLights website: https://www.ebi.ac.uk/metabolights/studies/{study_id} or use FTP/HTTP URLs if available in study data.",
                        }
                else:
                    return {
                        "status": "error",
                        "error": "Files endpoint returned server error (500). This is a known MetaboLights API issue.",
                        "url": url,
                        "suggestion": "The files endpoint is currently unavailable. Try accessing files via the MetaboLights website directly.",
                    }

            response.raise_for_status()
            data = response.json()

            # Extract arrays from dict wrappers for protocols, factors, data-files endpoints
            # These endpoints return {'protocols': [...]}, {'factors': [...]}, {'files': [...]}
            tool_name = self.tool_config.get("name", "")
            extracted_data = data
            count = None

            if isinstance(data, dict):
                # Check for common array wrapper keys
                for key in ["protocols", "factors", "files", "assays", "samples"]:
                    if key in data and isinstance(data[key], list):
                        extracted_data = data[key]
                        count = len(data[key])
                        break

                # Handle nested structure like {'data': {'assays': [...]}}
                if "data" in data and isinstance(data["data"], dict):
                    for key in ["assays", "protocols", "factors", "files"]:
                        if key in data["data"] and isinstance(data["data"][key], list):
                            extracted_data = data["data"][key]
                            count = len(data["data"][key])
                            break

                # Fallback: check for other common patterns
                if count is None:
                    if "content" in data and isinstance(data["content"], list):
                        extracted_data = data["content"]
                        count = len(data["content"])
                    elif "studies" in data and isinstance(data["studies"], list):
                        extracted_data = data["studies"]
                        count = len(data["studies"])
            elif isinstance(data, list):
                extracted_data = data
                count = len(data)

            # Apply client-side pagination for list/search (API ignores size/page params)
            if tool_name in (
                "metabolights_list_studies",
                "metabolights_search_studies",
            ):
                size = arguments.get("size", 20)
                page = arguments.get("page", 0)
                if isinstance(extracted_data, list):
                    total = len(extracted_data)
                    start = page * size
                    extracted_data = extracted_data[start : start + size]
                    count = len(extracted_data)

            response_data = {
                "status": "success",
                "data": extracted_data,
                "url": response.url,
            }

            if count is not None:
                response_data["count"] = count

            return response_data

        except requests.exceptions.HTTPError as e:
            tool_name = self.tool_config.get("name", "")

            # Handle samples endpoint 400 errors
            if (
                tool_name == "metabolights_get_study_samples"
                and e.response.status_code == 400
            ):
                study_id = arguments.get("study_id", "")
                if study_id:
                    fallback_data = self._extract_samples_from_study(study_id)
                    if "error" not in fallback_data:
                        return {
                            "status": "success",
                            "data": fallback_data.get("samples", []),
                            "url": url if "url" in locals() else None,
                            "count": fallback_data.get("count", 0),
                            "note": fallback_data.get("note", ""),
                            "fallback_used": True,
                        }

            # Handle files endpoint which may return 500 errors
            if (
                tool_name == "metabolights_get_study_files"
                and e.response.status_code == 500
            ):
                study_id = arguments.get("study_id", "")
                if study_id:
                    # Try fallback
                    fallback_data = self._extract_files_from_study(study_id)
                    if "error" not in fallback_data:
                        return {
                            "status": "success",
                            "data": fallback_data.get("files", []),
                            "file_urls": fallback_data.get("file_urls", {}),
                            "url": url if "url" in locals() else None,
                            "count": fallback_data.get("count", 0),
                            "note": fallback_data.get("note", ""),
                            "fallback_used": True,
                        }

            return {
                "status": "error",
                "error": f"MetaboLights API error: {str(e)}",
                "url": url if "url" in locals() else None,
            }
        except requests.exceptions.RequestException as e:
            tool_name = self.tool_config.get("name", "")

            # Handle samples endpoint
            if tool_name == "metabolights_get_study_samples" and "400" in str(e):
                study_id = arguments.get("study_id", "")
                if study_id:
                    fallback_data = self._extract_samples_from_study(study_id)
                    if "error" not in fallback_data:
                        return {
                            "status": "success",
                            "data": fallback_data.get("samples", []),
                            "url": url if "url" in locals() else None,
                            "count": fallback_data.get("count", 0),
                            "note": fallback_data.get("note", ""),
                            "fallback_used": True,
                        }

            # Handle files endpoint
            if tool_name == "metabolights_get_study_files" and "500" in str(e):
                study_id = arguments.get("study_id", "")
                if study_id:
                    fallback_data = self._extract_files_from_study(study_id)
                    if "error" not in fallback_data:
                        return {
                            "status": "success",
                            "data": fallback_data.get("files", []),
                            "file_urls": fallback_data.get("file_urls", {}),
                            "url": url if "url" in locals() else None,
                            "count": fallback_data.get("count", 0),
                            "note": fallback_data.get("note", ""),
                            "fallback_used": True,
                        }

            return {
                "status": "error",
                "error": f"MetaboLights API error: {str(e)}",
                "url": url if "url" in locals() else None,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error: {str(e)}",
                "url": url if "url" in locals() else None,
            }
