from .base_tool import BaseTool
from .tool_registry import register_tool

import requests


@register_tool("RCSBTool")
class RCSBTool(BaseTool):
    def __init__(self, tool_config):
        super().__init__(tool_config)
        # Prefer optional `rcsbapi` (GraphQL client). Fall back to direct REST calls
        # so these tools still work in minimal environments.
        try:
            from rcsbapi.data import DataQuery

            self.DataQuery = DataQuery
        except ImportError as e:
            self.DataQuery = None
            self._rcsbapi_import_error = e
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize RCSB API client. "
                f"This may be due to network issues or API unavailability. "
                f"Original error: {str(e)}"
            ) from e

        self.name = tool_config.get("name")
        self.description = tool_config.get("description")
        self.input_type = tool_config.get("input_type")
        fields = tool_config.get("fields", {})
        self.search_fields = fields.get("search_fields", {})
        self.return_fields = fields.get("return_fields", [])
        parameter = tool_config.get("parameter", {})
        self.parameter_schema = parameter.get("properties", {})
        self.required_params = parameter.get("required", []) or []
        self._rest_api_base = "https://data.rcsb.org/rest/v1/core"
        self._timeout = 60

    def validate_params(self, params: dict):
        for param_name in self.required_params:
            if param_name not in params:
                raise ValueError(f"Missing required parameter: {param_name}")
        return True

    def prepare_input_ids(self, params: dict):
        for param_name in self.search_fields:
            if param_name in params:
                val = params[param_name]
                return val if isinstance(val, list) else [val]
        raise ValueError("No valid search parameter provided")

    def _split_composite_id(
        self, value: str, sep: str, expected_parts: int, label: str
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Invalid {label}: must be a non-empty string")
        parts = value.strip()
        parts = parts.split(sep)
        if len(parts) != expected_parts or any(not p for p in parts):
            raise ValueError(
                f"Invalid {label}: expected format with {expected_parts} parts separated by '{sep}'"
            )
        return parts

    def _rest_url_for_input_id(self, input_id: str) -> str:
        input_type = (self.input_type or "").strip()
        if input_type in ("entry", "entries"):
            entry_id = str(input_id).strip().upper()
            return f"{self._rest_api_base}/entry/{entry_id}"
        if input_type == "polymer_entity":
            entry_id, entity_id = self._split_composite_id(
                str(input_id), "_", 2, "polymer entity ID (e.g., '1A8M_1')"
            )
            return (
                f"{self._rest_api_base}/polymer_entity/{entry_id.upper()}/{entity_id}"
            )
        if input_type == "assembly":
            entry_id, assembly_id = self._split_composite_id(
                str(input_id), "-", 2, "assembly ID (e.g., '1A8M-1')"
            )
            return f"{self._rest_api_base}/assembly/{entry_id.upper()}/{assembly_id}"
        if input_type == "branched_entity":
            entry_id, entity_id = self._split_composite_id(
                str(input_id), "_", 2, "branched entity ID (e.g., '5FMB_2')"
            )
            return (
                f"{self._rest_api_base}/branched_entity/{entry_id.upper()}/{entity_id}"
            )
        if input_type == "polymer_entity_instance":
            entry_id, asym_id = self._split_composite_id(
                str(input_id), ".", 2, "polymer entity instance ID (e.g., '1NDO.A')"
            )
            return f"{self._rest_api_base}/polymer_entity_instance/{entry_id.upper()}/{asym_id}"
        if input_type == "chem_comp":
            comp_id = str(input_id).strip().upper()
            return f"{self._rest_api_base}/chem_comp/{comp_id}"

        raise ValueError(
            f"Unsupported RCSB input_type for REST fallback: {input_type!r}"
        )

    def _run_via_rest(self, input_ids: list):
        results = []
        for input_id in input_ids:
            url = self._rest_url_for_input_id(input_id)
            resp = requests.get(url, timeout=self._timeout)
            resp.raise_for_status()
            results.append(resp.json())

        # Keep output shape consistent with existing return_schemas.
        input_type = (self.input_type or "").strip()
        if input_type in ("entry", "entries"):
            return {"data": {"entries": results}}
        if input_type == "polymer_entity":
            return {"data": {"polymer_entities": results}}
        if input_type == "assembly":
            return {"data": {"assemblies": results}}
        if input_type == "branched_entity":
            return {"data": {"branched_entities": results}}
        if input_type == "polymer_entity_instance":
            return {"data": {"polymer_entity_instances": results}}
        if input_type == "chem_comp":
            return {"data": {"chem_comps": results}}
        return {"data": results}

    def run(self, params: dict):
        self.validate_params(params)
        input_ids = self.prepare_input_ids(params)
        if self.DataQuery is None:
            return self._run_via_rest(input_ids)

        query = self.DataQuery(
            input_type=self.input_type,
            input_ids=input_ids,
            return_data_list=self.return_fields,
        )
        return query.exec()
