"""Persistent, secret-free connections to explicitly selected remote tools."""

from __future__ import annotations

import json
import os
import re
import tempfile
from contextlib import contextmanager
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
    target = Path(path) if path is not None else connections_path()
    if not target.exists():
        return []
    try:
        return _read_connections_strict(target)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return []


def _read_connections_strict(target: Path) -> List[Dict[str, Any]]:
    payload = json.loads(target.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        if payload.get("version", 1) != 1:
            raise ValueError("unsupported remote connections file version")
        payload = payload.get("connections", [])
    if not isinstance(payload, list):
        raise ValueError("remote connections file must contain a list")
    if not all(isinstance(item, dict) for item in payload):
        raise ValueError("every remote connection must be an object")
    return payload


@contextmanager
def _connections_lock(target: Path):
    """Serialize read-modify-write updates across CLI processes."""
    target.parent.mkdir(parents=True, exist_ok=True)
    lock_path = target.with_name(target.name + ".lock")
    with lock_path.open("a+b") as handle:
        os.chmod(lock_path, 0o600)
        if os.name == "nt":
            import msvcrt

            if handle.seek(0, os.SEEK_END) == 0:
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _write_connections_unlocked(
    connections: List[Dict[str, Any]], target: Path
) -> None:
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


def write_connections(
    connections: List[Dict[str, Any]], path: Path | None = None
) -> None:
    target = Path(path) if path is not None else connections_path()
    with _connections_lock(target):
        _write_connections_unlocked(connections, target)


def save_connection(connection: Dict[str, Any], path: Path | None = None) -> bool:
    """Save or replace a connection. Returns True when it changed the file."""
    target = Path(path) if path is not None else connections_path()
    with _connections_lock(target):
        try:
            connections = _read_connections_strict(target) if target.exists() else []
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError(
                f"cannot update invalid remote connections file {target}: {exc}"
            ) from exc
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
                _validate_connection_namespaces(connections)
                _write_connections_unlocked(connections, target)
                return True
        connections.append(connection)
        _validate_connection_namespaces(connections)
        _write_connections_unlocked(connections, target)
        return True


def _connection_namespace(connection: Dict[str, Any]) -> str | None:
    """Return the generated tool namespace that must remain unique."""
    if connection.get("kind") == "mcp":
        return connection.get("prefix")
    if connection.get("kind") == "platform":
        return connection.get("tool_name")
    return None


def _validate_connection_namespaces(connections: List[Dict[str, Any]]) -> None:
    """Reject connections that would silently replace each other's tools."""
    owners: Dict[str, str] = {}
    for connection in connections:
        namespace = _connection_namespace(connection)
        if not namespace:
            continue
        label = str(connection.get("name") or "remote tool")
        previous = owners.get(namespace)
        if previous is not None:
            raise ValueError(
                f"remote connection name collision: '{previous}' and '{label}' "
                f"both generate '{namespace}'; reconnect with a unique --name"
            )
        owners[namespace] = label


def remove_connection(target: str, path: Path | None = None) -> Dict[str, Any] | None:
    """Remove one saved connection by URL, resource UUID, name, or tool namespace."""
    value = target.strip()
    if not value:
        raise ValueError("a connection URL, UUID, name, or tool namespace is required")

    normalized_url: str | None = None
    if value.startswith(("http://", "https://")):
        try:
            normalized_url = normalize_mcp_url(value)
        except ValueError:
            # A marketplace URL is matched through its embedded resource UUID below.
            pass
    resource_id = extract_resource_id(value)
    target_path = Path(path) if path is not None else connections_path()
    with _connections_lock(target_path):
        try:
            connections = (
                _read_connections_strict(target_path) if target_path.exists() else []
            )
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError(
                f"cannot update invalid remote connections file {target_path}: {exc}"
            ) from exc

        matches = [
            index
            for index, connection in enumerate(connections)
            if (normalized_url is not None and connection.get("url") == normalized_url)
            or (
                resource_id is not None and connection.get("resource_id") == resource_id
            )
            or connection.get("name") == value
            or _connection_namespace(connection) == value
        ]
        if not matches:
            return None
        if len(matches) > 1:
            raise ValueError(
                f"connection selector '{value}' is ambiguous; use its exact URL or UUID"
            )
        removed = connections.pop(matches[0])
        _write_connections_unlocked(connections, target_path)
        return removed


def mcp_connection(url: str, name: str = "", auth_env: str = "") -> Dict[str, Any]:
    normalized = normalize_mcp_url(url)
    if auth_env and not _ENV_NAME_RE.fullmatch(auth_env):
        raise ValueError(
            "authentication environment variable must be a valid variable name"
        )
    parsed = urlsplit(normalized)
    if (
        auth_env
        and parsed.scheme == "http"
        and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
    ):
        raise ValueError(
            "bearer-authenticated MCP connections must use https:// outside localhost"
        )
    label = name.strip() or (parsed.hostname or "remote")
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
    connections = read_connections(path)
    _validate_connection_namespaces(connections)
    for index, connection in enumerate(connections):
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
