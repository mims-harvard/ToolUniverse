"""Synapse (Sage Bionetworks) public-data tools.

Synapse serves search and metadata for public projects, folders, files, tables and
datasets to anonymous callers. Restricted or private entities answer HTTP 403 and are
reported as such; nothing here logs in or reads file contents.

API: https://rest-docs.synapse.org/rest/
"""

import re
from datetime import datetime, timezone
from typing import Any, Dict, List

import requests

from .base_tool import BaseTool
from .http_utils import request_with_retry
from .tool_registry import register_tool

BASE_URL = "https://repo-prod.prod.sagebase.org/repo/v1"
USER_AGENT = "ToolUniverse/1.0 (+https://github.com/mims-harvard/ToolUniverse)"
ENTITY_ID = re.compile(r"syn\d+", re.I)
DESCRIPTION_CHARS = 400


def _iso(epoch_seconds: Any) -> Any:
    if isinstance(epoch_seconds, (int, float)):
        return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    return epoch_seconds


def _short_type(concrete_type: Any) -> Any:
    if isinstance(concrete_type, str):
        name = concrete_type.rsplit(".", 1)[-1]
        return name[: -len("Entity")] if name.endswith("Entity") else name
    return concrete_type


@register_tool("SynapseTool")
class SynapseTool(BaseTool):
    """Search and browse public Synapse entities (anonymous, read-only)."""

    def __init__(self, tool_config: Dict[str, Any], timeout: int = 30):
        super().__init__(tool_config)
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": USER_AGENT, "Accept": "application/json"}
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = self.tool_config.get("fields", {}).get("operation")
        handler = {
            "search": self._search,
            "get_entity": self._get_entity,
            "list_children": self._list_children,
        }.get(operation)
        if handler is None:
            return {
                "status": "error",
                "error": f"Unknown Synapse operation {operation!r}",
            }
        try:
            return handler(arguments)
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Synapse request failed: {e}"}

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        return request_with_retry(
            self.session,
            method,
            f"{BASE_URL}{path}",
            timeout=self.timeout,
            **kwargs,
        )

    @staticmethod
    def _http_error(response: requests.Response, what: str) -> Dict[str, Any]:
        if response.status_code == 403:
            message = (
                f"{what} is not public: Synapse returned 403 (this tool reads public "
                "entities anonymously and does not log in)"
            )
        elif response.status_code == 404:
            message = f"{what} was not found on Synapse"
        else:
            try:
                message = response.json().get("reason") or response.text[:200]
            except ValueError:
                message = response.text[:200]
            message = f"Synapse returned HTTP {response.status_code}: {message}"
        return {"status": "error", "error": message}

    @staticmethod
    def _entity_id(arguments: Dict[str, Any]) -> str:
        return str(arguments.get("entity_id") or "").strip()

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = str(arguments.get("query") or "").strip()
        if not query:
            return {"status": "error", "error": "query is required"}
        size = min(max(int(arguments.get("size") or 10), 1), 100)
        start = max(int(arguments.get("start") or 0), 0)
        body: Dict[str, Any] = {
            "queryTerm": query.split(),
            "size": size,
            "start": start,
        }
        node_type = str(arguments.get("node_type") or "").strip().lower()
        if node_type:
            body["booleanQuery"] = [{"key": "node_type", "value": node_type}]
        response = self._request("POST", "/search", json=body)
        if response.status_code not in (200, 201):
            return self._http_error(response, "The search")
        payload = response.json()
        rows = []
        for hit in payload.get("hits", []):
            description = (hit.get("description") or "").strip()
            rows.append(
                {
                    "id": hit.get("id"),
                    "name": hit.get("name"),
                    "node_type": hit.get("node_type"),
                    "description": description[:DESCRIPTION_CHARS]
                    + ("..." if len(description) > DESCRIPTION_CHARS else ""),
                    "created_on": _iso(hit.get("created_on")),
                    "modified_on": _iso(hit.get("modified_on")),
                    "created_by": hit.get("created_by"),
                }
            )
        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "source": "Synapse.org",
                "total_found": payload.get("found"),
                "start": start,
                "size": size,
                "query": query,
                "node_type": node_type or None,
            },
        }

    def _get_entity(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        entity_id = self._entity_id(arguments)
        if not ENTITY_ID.fullmatch(entity_id):
            return {
                "status": "error",
                "error": "entity_id must look like syn123456 (a Synapse ID)",
            }
        response = self._request("GET", f"/entity/{entity_id}")
        if response.status_code != 200:
            return self._http_error(response, f"Entity {entity_id}")
        entity = response.json()
        annotations: Dict[str, Any] = {}
        ann_response = self._request("GET", f"/entity/{entity_id}/annotations2")
        if ann_response.status_code == 200:
            for key, item in (ann_response.json().get("annotations") or {}).items():
                values = item.get("value") if isinstance(item, dict) else item
                annotations[key] = (
                    values[0]
                    if isinstance(values, list) and len(values) == 1
                    else values
                )
        data = {
            "id": entity.get("id"),
            "name": entity.get("name"),
            "type": _short_type(entity.get("concreteType")),
            "description": entity.get("description"),
            "parent_id": entity.get("parentId"),
            "created_on": entity.get("createdOn"),
            "modified_on": entity.get("modifiedOn"),
            "created_by": entity.get("createdBy"),
            "version_number": entity.get("versionNumber"),
            "version_label": entity.get("versionLabel"),
            "data_file_handle_id": entity.get("dataFileHandleId"),
            "annotations": annotations,
            "url": f"https://www.synapse.org/Synapse:{entity.get('id')}",
        }
        return {
            "status": "success",
            "data": data,
            "metadata": {"source": "Synapse.org"},
        }

    def _list_children(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        parent_id = self._entity_id(arguments)
        if not ENTITY_ID.fullmatch(parent_id):
            return {
                "status": "error",
                "error": "entity_id must look like syn123456 (a project or folder ID)",
            }
        types = arguments.get("include_types") or ["folder", "file", "table", "dataset"]
        body: Dict[str, Any] = {"parentId": parent_id, "includeTypes": list(types)}
        if arguments.get("next_page_token"):
            body["nextPageToken"] = arguments["next_page_token"]
        response = self._request("POST", "/entity/children", json=body)
        if response.status_code != 200:
            return self._http_error(response, f"Container {parent_id}")
        payload = response.json()
        rows: List[Dict[str, Any]] = []
        for child in payload.get("page", []):
            rows.append(
                {
                    "id": child.get("id"),
                    "name": child.get("name"),
                    "type": _short_type(child.get("type")),
                    "version_number": child.get("versionNumber"),
                    "created_on": child.get("createdOn"),
                    "modified_on": child.get("modifiedOn"),
                    "created_by": child.get("createdBy"),
                }
            )
        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "source": "Synapse.org",
                "parent_id": parent_id,
                "count": len(rows),
                "next_page_token": payload.get("nextPageToken"),
            },
        }
