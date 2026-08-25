# reactome_graph_tool.py

import requests
import re
from .base_tool import BaseTool
from .tool_registry import register_tool
from .http_utils import request_with_retry

# Reactome Content Service Base URL
REACTOME_BASE_URL = "https://reactome.org/ContentService"


@register_tool("ReactomeRESTTool")
class ReactomeRESTTool(BaseTool):
    """
    Generic Reactome Content Service REST tool.
    If there is no "fields.extract_path" in config or its value is empty, returns complete JSON;
    Otherwise, drills down according to the "dot-separated path" in extract_path and returns corresponding sub-node.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint_template = tool_config["endpoint"]  # e.g. "/data/pathway/{stId}"
        self.method = tool_config.get("method", "GET").upper()  # Default to GET
        self.param_schema = tool_config["parameter"][
            "properties"
        ]  # Parameter schema (including required)
        self.required_params = tool_config["parameter"].get(
            "required", []
        )  # List of required parameters
        # If config has fields and it contains extract_path, take it. Otherwise None.
        self.extract_path = None
        if "fields" in tool_config and isinstance(tool_config["fields"], dict):
            ep = tool_config["fields"].get("extract_path", None)
            if ep is not None and isinstance(ep, str) and ep.strip() != "":
                # Only effective when extract_path is a non-empty string
                self.extract_path = ep.strip()
        # Allow per-tool timeout override via JSON config
        self.timeout = int(tool_config.get("timeout", 10))

    def _build_url(self, arguments: dict) -> str:
        """
        Combines endpoint_template (containing {xxx}) with path parameters from arguments to generate complete URL.
        For example endpoint_template="/data/pathway/{stId}", arguments={"stId":"R-HSA-73817"}
        → Returns "https://reactome.org/ContentService/data/pathway/R-HSA-73817"
        """
        url_path = self.endpoint_template
        # Find all {xxx} placeholders and replace with values from arguments
        for key in re.findall(r"\{([^{}]+)\}", self.endpoint_template):
            if key not in arguments:
                raise ValueError(f"Missing path parameter '{key}'")
            url_path = url_path.replace(f"{{{key}}}", str(arguments[key]))
        return REACTOME_BASE_URL + url_path

    def run(
        self, arguments: dict, stream_callback=None, use_cache=False, validate=True
    ):
        # Feature-111A-006: id is a backward alias for uniprot_id (renamed in round 68B)
        if not arguments.get("uniprot_id") and arguments.get("id"):
            arguments = dict(arguments, uniprot_id=arguments["id"])

        # Optional schema validation (when jsonschema is available)
        if validate:
            validation_error = self.validate_parameters(arguments)
            if validation_error is not None:
                return {"status": "error", "error": str(validation_error)}

        # 1. Validate required parameters (check from required_params list)
        for required_param in self.required_params:
            if required_param not in arguments:
                return {
                    "status": "error",
                    "error": f"Parameter '{required_param}' is required.",
                }

        # 2. Build URL, replace {xxx} placeholders
        try:
            url = self._build_url(arguments)
        except ValueError as e:
            return {"status": "error", "error": str(e)}

        # 3. Find remaining arguments besides path parameters as query parameters
        path_keys = re.findall(r"\{([^{}]+)\}", self.endpoint_template)
        query_params = {}
        for k, v in arguments.items():
            if k not in path_keys:
                query_params[k] = v

        # 3b. The /data/query/ids endpoint performs no server-side filtering:
        # Reactome returns a byte-identical payload for every species/types
        # value (including ones that should have excluded every record), so a
        # filter passed here could only ever be silently ignored. Reject it at
        # input instead of returning unfiltered results that look filtered.
        # Scoped to this endpoint only -- other Reactome tools take species as
        # a genuine path parameter.
        if self.endpoint_template == "/data/query/ids":
            unsupported = [
                k for k in ("species", "types") if query_params.get(k) is not None
            ]
            if unsupported:
                return {
                    "status": "error",
                    "error": (
                        "Unsupported parameter(s): "
                        f"{', '.join(repr(k) for k in unsupported)}. The Reactome "
                        "/data/query/ids endpoint has no server-side filtering "
                        "and returns every requested ID regardless of species or "
                        "type. Re-run without them and filter the returned array "
                        "client-side -- each record carries 'speciesName' (e.g. "
                        "'Homo sapiens') and 'schemaClass' (e.g. 'Pathway', "
                        "'Reaction'). For species-scoped results retrieved "
                        "server-side, use Reactome_list_top_pathways or "
                        "Reactome_get_events_hierarchy, which take species as a "
                        "path parameter."
                    ),
                }

        # 4. Make HTTP request
        try:
            # Check if this is an attribute query endpoint (returns TSV, not JSON)
            is_attribute_query = (
                "/query/" in self.endpoint_template
                and "/" in self.endpoint_template.split("/query/")[-1]
                and self.endpoint_template.split("/query/")[-1].count("/") > 0
            )

            # Special handling for database version endpoint (returns plain text)
            is_version_endpoint = self.endpoint_template == "/data/database/version"

            headers = {"Accept": "application/json"}
            if is_attribute_query:
                # Attribute queries return TSV format, need text/plain
                headers["Accept"] = "text/plain"
            elif is_version_endpoint:
                # Version endpoint returns plain text integer
                headers["Accept"] = "text/plain"

            if self.method == "GET":
                resp = request_with_retry(
                    requests,
                    "GET",
                    url,
                    params=query_params,
                    headers=headers,
                    timeout=self.timeout,
                    max_attempts=3,
                    backoff_seconds=0.5,
                )
            else:
                # POST requests: Reactome API expects text/plain for query endpoints
                # Special handling for /data/query/ids endpoint
                if "/data/query/ids" in url:
                    # For query/ids, send comma-separated IDs as plain text
                    if "ids" in query_params:
                        ids = query_params["ids"]
                        if isinstance(ids, list):
                            body = ",".join(str(id) for id in ids)
                        else:
                            body = str(ids)
                        headers = {
                            "Content-Type": "text/plain",
                            "Accept": "application/json",
                        }
                        resp = request_with_retry(
                            requests,
                            "POST",
                            url,
                            data=body,
                            headers=headers,
                            timeout=self.timeout,
                            max_attempts=3,
                            backoff_seconds=0.5,
                        )
                    else:
                        # Fallback to JSON for other POST endpoints
                        headers = {"Content-Type": "application/json"}
                        resp = request_with_retry(
                            requests,
                            "POST",
                            url,
                            json=query_params,
                            headers=headers,
                            timeout=self.timeout,
                            max_attempts=3,
                            backoff_seconds=0.5,
                        )
                else:
                    # For other POST endpoints, use JSON
                    headers = {"Content-Type": "application/json"}
                    resp = request_with_retry(
                        requests,
                        "POST",
                        url,
                        json=query_params,
                        headers=headers,
                        timeout=self.timeout,
                        max_attempts=3,
                        backoff_seconds=0.5,
                    )
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to request Reactome Content Service: {str(e)}",
            }

        # 5. Check HTTP status code
        if resp.status_code != 200:
            # Fix-R15C-3: for the /data/mapping/... "list everything linked
            # to this identifier" endpoints, Reactome signals a genuine
            # empty result (identifier exists but has no entries of the
            # requested kind -- e.g. a non-human ortholog with no directly
            # curated pathways) as HTTP 404 with reason=NOT_FOUND and a
            # "No <things> found for <id>" message, not as a real error.
            # Confirmed live for bovine DGAT1 (Q8MK44): mapping/pathways and
            # mapping/reactions both 404 this way, while the human ortholog
            # (O75907) succeeds with real data via the same endpoint. Treat
            # that specific shape as an empty list so batch/automated
            # pipelines get a normal empty result instead of a hard
            # exception. Scoped to /data/mapping/ only -- single-entity
            # lookups (e.g. /data/pathway/{stId}) should keep erroring on a
            # bad ID rather than silently returning nothing.
            if resp.status_code == 404 and "/data/mapping/" in self.endpoint_template:
                try:
                    body = resp.json()
                except ValueError:
                    body = {}
                if body.get("reason") == "NOT_FOUND":
                    return {
                        "status": "success",
                        "data": [],
                        "metadata": {
                            "note": (body.get("messages") or [None])[0]
                            or "No results found.",
                            "source": "Reactome Content Service",
                        },
                    }
            return {
                "status": "error",
                "error": f"Reactome API returned HTTP {resp.status_code}",
                "detail": resp.text,
                "url": url,
            }

        # 6. Parse response (JSON or TSV)
        try:
            content_type = resp.headers.get("Content-Type", "").lower()

            # Check if response is TSV (for attribute queries)
            if "text/plain" in content_type or is_attribute_query:
                # Parse TSV format
                lines = resp.text.strip().split("\n")
                if not lines or not lines[0]:
                    return []

                # Parse TSV into list of dictionaries
                # First line might be header, or might be data
                data = []
                for line in lines:
                    if not line.strip():
                        continue
                    parts = line.split("\t")
                    # Create dict with indexed keys or use header if available
                    if len(parts) >= 3:
                        # Typical TSV format: ID, Name, Type
                        item = {
                            "id": parts[0] if len(parts) > 0 else "",
                            "name": parts[1] if len(parts) > 1 else "",
                            "type": parts[2] if len(parts) > 2 else "",
                            "raw": line,
                        }
                        # Add additional fields if present
                        if len(parts) > 3:
                            item["additional"] = parts[3:]
                        data.append(item)
                    else:
                        # Single value or simple format
                        data.append({"value": line.strip()})

                parsed = data if len(data) > 1 else (data[0] if data else {})
                return {"status": "success", "data": parsed}
            else:
                # Parse JSON
                data = resp.json()
        except (ValueError, requests.exceptions.JSONDecodeError):
            # Special handling for /data/database/version which returns plain integer
            if self.endpoint_template == "/data/database/version":
                try:
                    return int(resp.text.strip())
                except ValueError:
                    return resp.text.strip()

            return {
                "status": "error",
                "error": "Unable to parse Reactome returned response.",
                "content": resp.text[:500],
                "content_type": content_type,
            }

        # 7. If no extract_path in config, return complete JSON
        if not self.extract_path:
            return {"status": "success", "data": data}

        # 8. Otherwise drill down according to "dot-separated path" in extract_path
        fragment = data
        for part in self.extract_path.split("."):
            if isinstance(fragment, dict) and part in fragment:
                fragment = fragment[part]
            else:
                return {
                    "status": "error",
                    "error": f"Path '{self.extract_path}' not found in JSON.",
                }
        return {"status": "success", "data": fragment}
