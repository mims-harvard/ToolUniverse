"""Open Targets Platform: free-form GraphQL query and schema tools.

ToolUniverse already wraps the commonly used Open Targets queries one by one. These two
tools expose the API directly, so any field of the Platform schema can be asked for
(the same capability as Open Targets' own MCP server): first read the schema, then
send a GraphQL query.
"""

import json
import re
from typing import Any, Dict, List

import requests

from .base_tool import BaseTool
from .http_utils import request_with_retry
from .tool_registry import register_tool

GRAPHQL_URL = "https://api.platform.opentargets.org/api/v4/graphql"
USER_AGENT = "ToolUniverse/1.0 (+https://github.com/mims-harvard/ToolUniverse)"

_TYPE_REF = """
kind name ofType { kind name ofType { kind name ofType { kind name ofType { kind name } } } }
"""
_TYPE_QUERY = (
    "query($name: String!) { __type(name: $name) { name kind description "
    "fields { name description args { name description type { " + _TYPE_REF + " } } "
    "type { " + _TYPE_REF + " } } "
    "inputFields { name description type { " + _TYPE_REF + " } } "
    "enumValues { name description } } }"
)
_ROOT_QUERY = (
    "{ __schema { queryType { fields { name description args { name type { "
    + _TYPE_REF
    + " } } type { "
    + _TYPE_REF
    + " } } } types { name kind } } }"
)


def _render_type(ref: Any) -> str:
    """Turn an introspection type reference into GraphQL notation, e.g. [Target!]!"""
    if not isinstance(ref, dict):
        return "?"
    kind = ref.get("kind")
    if kind == "NON_NULL":
        return _render_type(ref.get("ofType")) + "!"
    if kind == "LIST":
        return "[" + _render_type(ref.get("ofType")) + "]"
    return ref.get("name") or "?"


class _OpenTargetsGraphQL(BaseTool):
    def __init__(self, tool_config: Dict[str, Any], timeout: int = 60):
        super().__init__(tool_config)
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def _post(self, query: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        body: Dict[str, Any] = {"query": query}
        if variables:
            body["variables"] = variables
        response = request_with_retry(
            self.session,
            "POST",
            GRAPHQL_URL,
            json=body,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        payload["_http_status"] = response.status_code
        return payload


@register_tool("OpenTargetsGraphQLQueryTool")
class OpenTargetsGraphQLQueryTool(_OpenTargetsGraphQL):
    """Run any read-only GraphQL query against the Open Targets Platform API."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = str(arguments.get("query") or "").strip()
        if not query:
            return {"status": "error", "error": "query is required"}
        if re.match(r"(mutation|subscription)\b", query, re.I):
            return {
                "status": "error",
                "error": "Only read-only GraphQL queries are supported",
            }
        variables = arguments.get("variables")
        if isinstance(variables, str) and variables.strip():
            try:
                variables = json.loads(variables)
            except ValueError as e:
                return {"status": "error", "error": f"variables is not valid JSON: {e}"}
        if variables is not None and not isinstance(variables, dict):
            return {"status": "error", "error": "variables must be a JSON object"}
        try:
            payload = self._post(query, variables)
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Open Targets request failed: {e}"}
        errors = payload.get("errors") or []
        if payload.get("data") is None:
            detail = (
                "; ".join(
                    str(e.get("message", e)) if isinstance(e, dict) else str(e)
                    for e in errors
                )
                or f"HTTP {payload['_http_status']}"
            )
            return {"status": "error", "error": f"Open Targets GraphQL error: {detail}"}
        result: Dict[str, Any] = {"status": "success", "data": payload["data"]}
        if errors:
            result["metadata"] = {"graphql_errors": errors}
        return result


@register_tool("OpenTargetsGraphQLSchemaTool")
class OpenTargetsGraphQLSchemaTool(_OpenTargetsGraphQL):
    """Describe the Open Targets GraphQL schema: root queries, or one type in detail."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        type_name = str(arguments.get("type_name") or "").strip()
        try:
            if type_name:
                return self._describe_type(type_name)
            return self._describe_root()
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Open Targets request failed: {e}"}

    def _describe_root(self) -> Dict[str, Any]:
        payload = self._post(_ROOT_QUERY)
        schema = (payload.get("data") or {}).get("__schema")
        if not schema:
            return {"status": "error", "error": "Open Targets did not return a schema"}
        queries = [
            {
                "name": f["name"],
                "description": f.get("description"),
                "returns": _render_type(f["type"]),
                "arguments": {a["name"]: _render_type(a["type"]) for a in f["args"]},
            }
            for f in schema["queryType"]["fields"]
        ]
        types = sorted(
            t["name"]
            for t in schema["types"]
            if not t["name"].startswith("__")
            and t["kind"] in ("OBJECT", "ENUM", "INPUT_OBJECT")
        )
        return {
            "status": "success",
            "data": {"queries": queries, "type_names": types},
            "metadata": {
                "hint": "Call again with type_name (e.g. 'Target') to list a type's fields."
            },
        }

    def _describe_type(self, type_name: str) -> Dict[str, Any]:
        payload = self._post(_TYPE_QUERY, {"name": type_name})
        type_info = (payload.get("data") or {}).get("__type")
        if not type_info:
            return {
                "status": "error",
                "error": f"No type named {type_name!r} in the Open Targets schema "
                "(names are case-sensitive; call without type_name to list them)",
            }
        data: Dict[str, Any] = {
            "name": type_info["name"],
            "kind": type_info["kind"],
            "description": type_info.get("description"),
        }
        if type_info.get("fields"):
            data["fields"] = [
                {
                    "name": f["name"],
                    "type": _render_type(f["type"]),
                    "description": f.get("description"),
                    "arguments": {
                        a["name"]: _render_type(a["type"]) for a in f["args"]
                    },
                }
                for f in type_info["fields"]
            ]
        if type_info.get("inputFields"):
            data["input_fields"] = [
                {
                    "name": f["name"],
                    "type": _render_type(f["type"]),
                    "description": f.get("description"),
                }
                for f in type_info["inputFields"]
            ]
        if type_info.get("enumValues"):
            data["enum_values"] = [
                {"name": v["name"], "description": v.get("description")}
                for v in type_info["enumValues"]
            ]
        return {"status": "success", "data": data}
