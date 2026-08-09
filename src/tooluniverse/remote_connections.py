"""Persistent, secret-free connections to explicitly selected remote tools."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlsplit, urlunsplit


_UUID_RE = re.compile(
    r"(?i)(?<![0-9a-f])([0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12})(?![0-9a-f])"
)
_ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def connections_path() -> Path:
    override = os.getenv("TOOLUNIVERSE_CONNECTIONS_FILE")
    return (
        Path(override).expanduser()
        if override
        else Path.home() / ".tooluniverse" / "connections.json"
    )


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip()).strip("_").lower()
    return slug or "remote"


def normalize_mcp_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(
            "remote MCP URL must use http:// or https:// and include a host"
        )
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("remote MCP URL must not contain credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("remote MCP URL must not contain a query or fragment")
    path = parsed.path.rstrip("/")
    if not path.endswith("/mcp"):
        path += "/mcp"
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def extract_resource_id(value: str) -> str | None:
    match = _UUID_RE.search(value.strip())
    return match.group(1).lower() if match else None


def read_connections(path: Path | None = None) -> List[Dict[str, Any]]:
    target = path or connections_path()
    if not target.exists():
        return []
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return []
    if isinstance(payload, dict):
        payload = payload.get("connections", [])
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def write_connections(
    connections: List[Dict[str, Any]], path: Path | None = None
) -> None:
    target = path or connections_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    document = {"version": 1, "connections": connections}
    fd, temp_name = tempfile.mkstemp(
        prefix=".connections-", suffix=".json", dir=target.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(document, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_name, 0o600)
        os.replace(temp_name, target)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def save_connection(connection: Dict[str, Any], path: Path | None = None) -> bool:
    """Save or replace a connection. Returns True when it changed the file."""
    connections = read_connections(path)
    identity = (
        connection.get("kind"),
        connection.get("url") or connection.get("resource_id"),
    )
    for index, existing in enumerate(connections):
        existing_identity = (
            existing.get("kind"),
            existing.get("url") or existing.get("resource_id"),
        )
        if existing_identity == identity:
            if existing == connection:
                return False
            connections[index] = connection
            write_connections(connections, path)
            return True
    connections.append(connection)
    write_connections(connections, path)
    return True


def mcp_connection(url: str, name: str = "", auth_env: str = "") -> Dict[str, Any]:
    normalized = normalize_mcp_url(url)
    if auth_env and not _ENV_NAME_RE.fullmatch(auth_env):
        raise ValueError(
            "authentication environment variable must be a valid variable name"
        )
    label = name.strip() or (urlsplit(normalized).hostname or "remote")
    result: Dict[str, Any] = {
        "kind": "mcp",
        "name": label,
        "url": normalized,
        "prefix": _slug(label) + "_",
    }
    if auth_env:
        result["auth_env"] = auth_env
    return result


def platform_connection(
    resource_id: str,
    *,
    name: str,
    description: str,
    input_schema: Dict[str, Any],
    base_url: str,
) -> Dict[str, Any]:
    return {
        "kind": "platform",
        "name": name.strip() or "Remote platform tool",
        "resource_id": resource_id,
        "description": description.strip(),
        "input_schema": input_schema,
        "base_url": base_url.rstrip("/"),
        "tool_name": "remote_" + _slug(name),
    }


def connection_configs(path: Path | None = None) -> List[Dict[str, Any]]:
    """Translate persisted connections into normal ToolUniverse tool configs."""
    configs: List[Dict[str, Any]] = []
    for index, connection in enumerate(read_connections(path)):
        kind = connection.get("kind")
        if kind == "mcp" and connection.get("url"):
            config: Dict[str, Any] = {
                "name": f"connected_mcp_{index}",
                "description": f"Load tools from {connection.get('name', 'remote MCP')}",
                "type": "MCPAutoLoaderTool",
                "server_url": connection["url"],
                "tool_prefix": connection.get("prefix", "remote_"),
                "category": "connected_remote_tools",
                "timeout": 30,
            }
            if connection.get("auth_env"):
                config["auth_env"] = connection["auth_env"]
            configs.append(config)
        elif kind == "platform" and connection.get("resource_id"):
            configs.append(
                {
                    "name": connection.get("tool_name") or f"platform_tool_{index}",
                    "description": connection.get("description")
                    or "Connected platform tool",
                    "type": "PlatformRemoteTool",
                    "resource_id": connection["resource_id"],
                    "base_url": connection.get("base_url", ""),
                    "parameter": connection.get("input_schema") or {"type": "object"},
                    "category": "connected_remote_tools",
                }
            )
    return configs
