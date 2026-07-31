"""
Dynamic REST/GraphQL tool loader for Verified Source Directory (VSD).

This module keeps an in-memory registry of generated tool specifications and
exposes helper functions for refreshing, inserting, or removing entries. Tools
are backed by lightweight BaseTool subclasses that issue HTTP requests using
the stored configuration.
"""

from __future__ import annotations

import json
import logging
import threading
from typing import Any, Dict, Optional

import requests

from .base_tool import BaseTool
from .common_utils import read_json, vsd_generated_path
from .tool_registry import register_config, register_tool

LOGGER = logging.getLogger("DynamicRESTRunner")
_REGISTRY_LOCK = threading.Lock()
_GENERATED_TOOLS: Dict[str, Dict[str, Any]] = {}


def _normalize_spec(spec: Any) -> Dict[str, Dict[str, Any]]:
    """
    Accept legacy list or dict formats and normalize to {name: config}.
    """
    if isinstance(spec, dict):
        if "generated_tools" in spec and isinstance(spec["generated_tools"], list):
            return {
                item.get("name"): dict(item)
                for item in spec["generated_tools"]
                if isinstance(item, dict) and item.get("name")
            }
        return {
            name: dict(cfg)
            for name, cfg in spec.items()
            if isinstance(cfg, dict)
        }

    if isinstance(spec, list):
        result: Dict[str, Dict[str, Any]] = {}
        for item in spec:
            if isinstance(item, dict) and item.get("name"):
                result[item["name"]] = dict(item)
        return result

    return {}


def _load_generated_specs() -> Dict[str, Dict[str, Any]]:
    path = vsd_generated_path()
    data = read_json(path, {})
    return _normalize_spec(data)


def _build_request_kwargs(config: Dict[str, Any], arguments: Dict[str, Any]) -> Dict[str, Any]:
    fields = config.get("fields", {})
    method = fields.get("method", "GET").upper()
    timeout = fields.get("timeout", 30)
    headers = fields.get("headers", {})
    default_params = fields.get("default_params", {})

    params = dict(default_params)
    body: Optional[Any] = None

    if method in {"GET", "DELETE"}:
        params.update(arguments)
    else:
        if fields.get("body_format", "json") == "form":
            body = dict(arguments)
        else:
            body = arguments or {}

    kwargs: Dict[str, Any] = {
        "method": method,
        "url": fields.get("base_url"),
        "headers": headers,
        "timeout": timeout,
    }
    if params:
        kwargs["params"] = params
    if body is not None:
        if fields.get("body_format", "json") == "form":
            kwargs["data"] = body
        else:
            kwargs["json"] = body
    return kwargs


def _handle_response(response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return {
            "status_code": response.status_code,
            "text": response.text,
        }


@register_tool("GenericRESTTool")
class GenericRESTTool(BaseTool):
    """
    Generic REST tool generated from a VSD configuration.
    """

    def run(self, arguments=None, stream_callback=None, **_: Any):
        arguments = arguments or {}
        kwargs = _build_request_kwargs(self.tool_config, arguments)
        method = kwargs.pop("method")
        url = kwargs.pop("url")

        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        result = _handle_response(response)

        if stream_callback:
            stream_callback(json.dumps(result))
        return result


@register_tool("GenericGraphQLTool")
class GenericGraphQLTool(BaseTool):
    """
    Generic GraphQL tool generated from a VSD configuration.
    """

    def run(self, arguments=None, stream_callback=None, **_: Any):
        arguments = arguments or {}
        fields = self.tool_config.get("fields", {})
        headers = fields.get("headers", {})
        timeout = fields.get("timeout", 30)
        payload = {
            "query": arguments.get("query") or fields.get("default_query"),
            "variables": arguments.get("variables") or fields.get("default_variables", {}),
        }

        response = requests.post(
            fields.get("base_url"),
            json=payload,
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        result = _handle_response(response)

        if stream_callback:
            stream_callback(json.dumps(result))
        return result


def _register_generated_tool(tool_name: str, config: Dict[str, Any]) -> None:
    config = dict(config)
    config.setdefault("name", tool_name)
    tool_type = config.get("type") or "GenericRESTTool"

    register_config(tool_name, config)
    _GENERATED_TOOLS[tool_name] = config

    LOGGER.debug("Registered generated tool %s of type %s", tool_name, tool_type)


def refresh_generated_registry() -> Dict[str, Dict[str, Any]]:
    """
    Reload generated tool specs from disk and update the runtime registry.
    """
    specs = _load_generated_specs()
    with _REGISTRY_LOCK:
        _GENERATED_TOOLS.clear()
        for name, cfg in specs.items():
            _register_generated_tool(name, cfg)
    return specs


def upsert_generated_tool(tool_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Insert or update a generated tool in the runtime registry.
    """
    with _REGISTRY_LOCK:
        _register_generated_tool(tool_name, config)
    return _GENERATED_TOOLS[tool_name]


def remove_generated_tool(tool_name: str) -> None:
    """
    Remove a generated tool from the runtime registry.
    """
    with _REGISTRY_LOCK:
        _GENERATED_TOOLS.pop(tool_name, None)
        LOGGER.debug("Removed generated tool %s", tool_name)
