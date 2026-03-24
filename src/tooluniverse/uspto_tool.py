import requests
import json
import re
import os
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .base_tool import BaseTool
from .tool_registry import register_tool
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(usecwd=True))

USPTO_API_KEY = os.environ.get("USPTO_API_KEY")


@register_tool("USPTOOpenDataPortalTool")
class USPTOOpenDataPortalTool(BaseTool):
    """
    A tool for interacting with the USPTO Open Data Portal API to search for and retrieve patent information.
    The run method dynamically constructs API requests based on the provided tool configuration.
    """

    def __init__(
        self,
        tool_config,
        api_key=USPTO_API_KEY,
        base_url="https://api.uspto.gov/api/v1",
    ):
        """
        Initializes the USPTOOpenDataPortalTool.

        Args:
            tool_config: The configuration for the specific tool being run.
            api_key: Your USPTO Open Data Portal API key.
            base_url: The base URL for the USPTO API.
        """
        super().__init__(tool_config)
        self.base_url = base_url
        if api_key == "YOUR_API_KEY" or not api_key:
            raise ValueError(
                "You must set a USPTO API key via the USPTO_API_KEY environment variable."
            )
        self.headers = {"X-API-KEY": api_key, "Accept": "application/json"}
        self.session = requests.Session()
        retry_strategy = Retry(
            total=5,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=5,  # first retry waits 5s, then 10s, 20s, …
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)

    def get_by_path(self, d, keys):
        """Safely navigate nested dicts by a list of keys."""
        for k in keys:
            if d is None:
                return None
            if isinstance(d, dict):
                d = d.get(k)
            else:
                return None
        return d

    def assign_by_path(self, d, path, value):
        """Create nested dicts for a dot‑path and set the final key to value."""
        keys = path.split(".")
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value

    def prune_item(self, item, return_fields):
        out = {}
        missing_fields = []

        # 1) First, handle all the list‑of‑objects fields (the "/" ones),
        #    grouping them by their list‑path prefix.
        list_groups = {}
        for field in return_fields:
            if "/" in field:
                list_path, prop = field.split("/", 1)
                list_groups.setdefault(list_path, []).append(prop)

        for list_path, props in list_groups.items():
            prefix_keys = list_path.split(".")
            raw_list = self.get_by_path(item, prefix_keys)
            if not isinstance(raw_list, list):
                for prop in props:
                    missing_fields.append(f"{list_path}/{prop}")
                continue

            pruned_list = []
            prop_found = {prop: False for prop in props}
            for el in raw_list:
                if not isinstance(el, dict):
                    continue
                pruned_el = {}
                for prop in props:
                    if prop in el:
                        pruned_el[prop] = el[prop]
                        prop_found[prop] = True
                if pruned_el:
                    pruned_list.append(pruned_el)

            # Track missing properties
            for prop, found in prop_found.items():
                if not found:
                    missing_fields.append(f"{list_path}/{prop}")

            if pruned_list:
                self.assign_by_path(out, list_path, pruned_list)

        # 2) Then handle all the scalar or nested‑dict fields (the "." ones without "/").
        for field in return_fields:
            if "/" in field:
                continue  # already done
            keys = field.split(".")
            raw_value = self.get_by_path(item, keys)
            if raw_value is None:
                missing_fields.append(field)
                continue

            self.assign_by_path(out, field, raw_value)

        out["missing_fields"] = missing_fields
        return out

    def run(self, arguments):
        """
        Runs the specified tool by constructing and executing an API call based on the tool's configuration.

        Args:
            arguments: A dictionary of arguments for the tool, matching the parameters in the tool definition.

        Returns
            The result of the API call, either as a dictionary (for JSON) or a string (for CSV).
        """
        endpoint = self.tool_config.get("api_endpoint")
        if not endpoint:
            return {
                "status": "error",
                "error": "API endpoint not found in tool configuration.",
            }

        path_params = re.findall(r"\{(\w+)\}", endpoint)
        query_params = {}

        # Substitute path parameters and build query string parameters
        for key, value in arguments.items():
            if key in path_params:
                endpoint = endpoint.replace(f"{{{key}}}", str(value))
            else:
                query_params[key] = value

        # Remove any None values from the query parameters
        keys_to_process = list(query_params.keys())
        for k in keys_to_process:
            v = query_params.get(k)
            if v is None:
                param_props = (
                    self.tool_config.get("parameter", {})
                    .get("properties", {})
                    .get(k, {})
                )
                default = param_props.get("default")
                if default is not None:
                    query_params[k] = default
                else:
                    query_params.pop(k, None)

        # default parameters if not provided
        for k, v in self.tool_config.get("default_query_params", {}).items():
            if k not in query_params or query_params[k] is None:
                query_params[k] = v

        # Special handling for the inputs to this tool
        if self.tool_config.get("name") == "get_patent_overview_by_text_query":
            if "query" in query_params:
                query_params["q"] = query_params["query"]
                del query_params["query"]
            else:
                return {
                    "status": "error",
                    "data": {"error": "Missing required parameter 'query'."},
                }

            if query_params.get("exact_match", False):
                query_params["q"] = f'"{query_params["q"]}"'

            # Remove exact_match from params if present
            query_params.pop("exact_match", None)

            field_mappings = {
                "filingDate": "applicationMetaData.filingDate",
                "grantDate": "applicationMetaData.grantDate",
            }

            for old_field, new_field in field_mappings.items():
                if old_field in query_params.get("sort", ""):
                    query_params["sort"] = query_params["sort"].replace(
                        old_field, new_field
                    )
                if old_field in query_params.get("rangeFilters", ""):
                    query_params["rangeFilters"] = query_params["rangeFilters"].replace(
                        old_field, new_field
                    )

        try:
            # The timeout for downloads can be longer
            timeout = 120 if "download" in self.tool_config.get("name", "") else 30

            response = self.session.get(
                f"{self.base_url}/{endpoint}",
                headers=self.headers,
                params=query_params,
                timeout=timeout,
            )
            response.raise_for_status()

            # Otherwise, assume the response is JSON
            if self.tool_config.get("return_fields", []):
                # Filter the JSON response to only include specified fields
                pruned_patents = []
                result = response.json()
                for patent in result.get("patentFileWrapperDataBag", []):
                    pruned_patents.append(
                        self.prune_item(patent, self.tool_config.get("return_fields"))
                    )
                result["patentFileWrapperDataBag"] = pruned_patents
            else:
                result = response.json()

            # Wrap response with data field for schema validation
            return {"status": "success", "data": result}

        except requests.exceptions.HTTPError as http_err:
            # Attempt to return the structured error from the API response body
            try:
                error_details = http_err.response.json()
            except json.JSONDecodeError:
                error_details = http_err.response.text
            return {
                "status": "error",
                "data": {
                    "error": f"HTTP Error: {http_err.response.status_code}",
                    "details": error_details,
                },
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "data": {"error": "API request failed", "details": str(e)},
            }
