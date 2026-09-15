"""Administrator-only provisioning for a reviewed Docker LLM profile."""

from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlsplit

import requests

from .client import DockerLLMClientTool, _validated_client_config

_VERSION = 1
_MAX_ARTIFACT_BYTES = 1_000_000
_NAME_RE = re.compile(r"^[a-z][a-z0-9-]{2,62}$")
_TOOL_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{2,44}$")
_IMAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@-]{0,254}$")
_PATH_RE = re.compile(r"^/[A-Za-z0-9._~!$&'()*+,;=:@%/-]{1,127}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_MANAGED_LABEL = "org.tooluniverse.managed"
_PROFILE_LABEL = "org.tooluniverse.profile-sha256"
_SERVICE_LABEL = "org.tooluniverse.service-id"


class DockerProvisionError(RuntimeError):
    """Raised when a Docker lifecycle or profile check fails closed."""


def _canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _workspace_root(workspace: str | Path | None) -> Path:
    if workspace is not None:
        root = Path(workspace).expanduser()
    else:
        configured = os.environ.get("TOOLUNIVERSE_DOCKER_DIR")
        root = (
            Path(configured).expanduser()
            if configured
            else Path.home() / ".tooluniverse" / "docker_llm"
        )
    root.mkdir(parents=True, exist_ok=True)
    return root


def _read_json(path: Path) -> Any:
    try:
        if path.stat().st_size > _MAX_ARTIFACT_BYTES:
            raise DockerProvisionError(f"Artifact {path.name!r} exceeds 1 MB")
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DockerProvisionError(f"Artifact {path.name!r} does not exist") from exc
    except json.JSONDecodeError as exc:
        raise DockerProvisionError(f"Artifact {path.name!r} is not valid JSON") from exc


def _atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    if len(encoded.encode("utf-8")) > _MAX_ARTIFACT_BYTES:
        raise DockerProvisionError("Provisioning artifact exceeds 1 MB")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.stem}_", suffix=".json", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _bounded_text(value: Any, *, field: str, minimum: int, maximum: int) -> str:
    text = str(value or "").strip()
    if not minimum <= len(text) <= maximum or any(
        ord(character) < 32 for character in text
    ):
        raise DockerProvisionError(
            f"{field} must contain {minimum}-{maximum} printable characters"
        )
    return text


def _allowed_images() -> set[str]:
    raw = os.environ.get("TOOLUNIVERSE_DOCKER_ALLOWED_IMAGES", "")
    images = {item.strip() for item in raw.split(",") if item.strip()}
    if not images:
        raise DockerProvisionError(
            "TOOLUNIVERSE_DOCKER_ALLOWED_IMAGES must list exact approved image references"
        )
    return images


def load_profile(profile_path: str | Path) -> tuple[dict[str, Any], str]:
    """Load and strictly validate one administrator-reviewed JSON profile."""
    profile = _read_json(Path(profile_path))
    if not isinstance(profile, dict) or set(profile) != {
        "version",
        "profile_name",
        "service_id",
        "image",
        "container_port",
        "health_path",
        "inference_path",
        "model",
        "tool",
        "resources",
        "timeouts",
    }:
        raise DockerProvisionError("Profile fields do not match the reviewed schema")
    if profile["version"] != _VERSION:
        raise DockerProvisionError("Profile version must be 1")
    for field in ("profile_name", "service_id"):
        value = profile[field]
        if not isinstance(value, str) or not _NAME_RE.fullmatch(value):
            raise DockerProvisionError(f"{field} must be a lowercase stable identifier")
    image = profile["image"]
    if (
        not isinstance(image, str)
        or not _IMAGE_RE.fullmatch(image)
        or image.startswith("-")
        or image not in _allowed_images()
    ):
        raise DockerProvisionError("Profile image is not in the exact image allowlist")
    port = profile["container_port"]
    if isinstance(port, bool) or not isinstance(port, int) or not 1024 <= port <= 65535:
        raise DockerProvisionError("container_port must be between 1024 and 65535")
    for field in ("health_path", "inference_path"):
        path = profile[field]
        if (
            not isinstance(path, str)
            or not _PATH_RE.fullmatch(path)
            or ".." in path
            or "//" in path
        ):
            raise DockerProvisionError(f"{field} must be a fixed absolute URL path")
    if profile["health_path"] == profile["inference_path"]:
        raise DockerProvisionError("Health and inference paths must differ")
    _bounded_text(profile["model"], field="model", minimum=1, maximum=200)

    tool = profile["tool"]
    if not isinstance(tool, dict) or set(tool) != {
        "name",
        "description",
        "max_prompt_chars",
        "max_tokens_cap",
        "default_temperature",
    }:
        raise DockerProvisionError("tool fields do not match the reviewed schema")
    if not isinstance(tool["name"], str) or not _TOOL_NAME_RE.fullmatch(tool["name"]):
        raise DockerProvisionError("tool.name is not MCP-compatible")
    _bounded_text(
        tool["description"], field="tool.description", minimum=20, maximum=1000
    )
    prompt_limit = tool["max_prompt_chars"]
    token_limit = tool["max_tokens_cap"]
    temperature = tool["default_temperature"]
    if (
        isinstance(prompt_limit, bool)
        or not isinstance(prompt_limit, int)
        or not 100 <= prompt_limit <= 100_000
    ):
        raise DockerProvisionError("tool.max_prompt_chars must be 100-100000")
    if (
        isinstance(token_limit, bool)
        or not isinstance(token_limit, int)
        or not 1 <= token_limit <= 8192
    ):
        raise DockerProvisionError("tool.max_tokens_cap must be 1-8192")
    if (
        isinstance(temperature, bool)
        or not isinstance(temperature, (int, float))
        or not 0 <= temperature <= 2
    ):
        raise DockerProvisionError("tool.default_temperature must be between 0 and 2")

    resources = profile["resources"]
    if not isinstance(resources, dict) or set(resources) != {
        "cpus",
        "memory_mb",
        "pids_limit",
        "tmpfs_mb",
    }:
        raise DockerProvisionError("resources fields do not match the reviewed schema")
    cpus = resources["cpus"]
    if (
        isinstance(cpus, bool)
        or not isinstance(cpus, (int, float))
        or not 0.25 <= cpus <= 32
    ):
        raise DockerProvisionError("resources.cpus must be between 0.25 and 32")
    for field, minimum, maximum in (
        ("memory_mb", 128, 131_072),
        ("pids_limit", 32, 4096),
        ("tmpfs_mb", 16, 4096),
    ):
        value = resources[field]
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not minimum <= value <= maximum
        ):
            raise DockerProvisionError(
                f"resources.{field} must be an integer between {minimum} and {maximum}"
            )

    timeouts = profile["timeouts"]
    if not isinstance(timeouts, dict) or set(timeouts) != {
        "health_seconds",
        "inference_seconds",
    }:
        raise DockerProvisionError("timeouts fields do not match the reviewed schema")
    for field, maximum in (("health_seconds", 300), ("inference_seconds", 120)):
        value = timeouts[field]
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 1 <= value <= maximum
        ):
            raise DockerProvisionError(
                f"timeouts.{field} must be between 1 and {maximum}"
            )
    return profile, _canonical_digest(profile)


def _docker_environment() -> dict[str, str]:
    allowed = ("PATH", "SystemRoot", "HOME", "USERPROFILE", "TEMP", "TMP")
    return {name: os.environ[name] for name in allowed if name in os.environ}


def _run_docker(
    arguments: Sequence[str], *, check: bool = True, timeout: int = 60
) -> subprocess.CompletedProcess:
    if not isinstance(arguments, (list, tuple)) or any(
        not isinstance(item, str) for item in arguments
    ):
        raise DockerProvisionError("Docker arguments must be a sequence of strings")
    try:
        result = subprocess.run(
            ["docker", *arguments],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=_docker_environment(),
        )
    except FileNotFoundError as exc:
        raise DockerProvisionError("Docker CLI is not installed") from exc
    except subprocess.TimeoutExpired as exc:
        raise DockerProvisionError("Docker command exceeded its timeout") from exc
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout or "unknown Docker error").strip()[
            :1000
        ]
        raise DockerProvisionError(f"Docker command failed: {detail}")
    return result


def _check_docker() -> tuple[str, str]:
    context_result = _run_docker(["context", "show"])
    context = context_result.stdout.strip()
    if not context or len(context) > 100:
        raise DockerProvisionError("Docker returned an invalid context name")
    inspect_result = _run_docker(["context", "inspect", context])
    try:
        contexts = json.loads(inspect_result.stdout)
        daemon_host = contexts[0]["Endpoints"]["docker"]["Host"]
    except (json.JSONDecodeError, IndexError, KeyError, TypeError) as exc:
        raise DockerProvisionError(
            "Docker context inspection returned invalid data"
        ) from exc
    local_unix = isinstance(daemon_host, str) and daemon_host.startswith("unix:///")
    local_pipe = isinstance(daemon_host, str) and daemon_host.startswith(
        "npipe:////./pipe/"
    )
    if not local_unix and not local_pipe:
        raise DockerProvisionError(
            "Docker context must use a local socket or named pipe"
        )
    result = _run_docker(["version", "--format", "{{.Server.Version}}"])
    version = result.stdout.strip()
    if not version or len(version) > 100:
        raise DockerProvisionError("Docker server returned an invalid version")
    return version, context


def _image_id(image: str) -> str:
    result = _run_docker(["image", "inspect", "--format", "{{.Id}}", image])
    image_id = result.stdout.strip()
    if not _SHA256_RE.fullmatch(image_id):
        raise DockerProvisionError("Docker image did not resolve to a content ID")
    return image_id


def _inspect_container(container_name: str) -> dict[str, Any] | None:
    result = _run_docker(["container", "inspect", container_name], check=False)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).casefold()
        if "no such" in detail:
            return None
        raise DockerProvisionError("Docker could not inspect the requested container")
    try:
        records = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise DockerProvisionError("Docker inspect returned invalid JSON") from exc
    if (
        not isinstance(records, list)
        or len(records) != 1
        or not isinstance(records[0], dict)
    ):
        raise DockerProvisionError("Docker inspect returned an unexpected record set")
    return records[0]


def _container_name(value: str | None, profile: dict[str, Any]) -> str:
    name = value or f"tooluniverse-{profile['profile_name']}"
    if not isinstance(name, str) or not _NAME_RE.fullmatch(name):
        raise DockerProvisionError(
            "Container name must be a lowercase stable identifier"
        )
    return name


def _host_port(value: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1024 <= value <= 65535
    ):
        raise DockerProvisionError("Host port must be between 1024 and 65535")
    return value


def _expected_labels(profile: dict[str, Any], profile_sha256: str) -> dict[str, str]:
    return {
        _MANAGED_LABEL: "true",
        _PROFILE_LABEL: profile_sha256,
        _SERVICE_LABEL: profile["service_id"],
    }


def _run_arguments(
    profile: dict[str, Any], profile_sha256: str, name: str, host_port: int
) -> list[str]:
    resources = profile["resources"]
    arguments = [
        "run",
        "--detach",
        "--name",
        name,
        "--pull",
        "never",
    ]
    for key, value in _expected_labels(profile, profile_sha256).items():
        arguments.extend(["--label", f"{key}={value}"])
    arguments.extend(
        [
            "--publish",
            f"127.0.0.1:{host_port}:{profile['container_port']}",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges:true",
            "--pids-limit",
            str(resources["pids_limit"]),
            "--memory",
            f"{resources['memory_mb']}m",
            "--cpus",
            str(resources["cpus"]),
            "--tmpfs",
            f"/tmp:rw,noexec,nosuid,size={resources['tmpfs_mb']}m",
            profile["image"],
        ]
    )
    return arguments


def _security_summary(
    record: dict[str, Any],
    profile: dict[str, Any],
    profile_sha256: str,
    image_id: str,
    name: str,
    host_port: int,
) -> dict[str, Any]:
    config = record.get("Config") or {}
    host = record.get("HostConfig") or {}
    state = record.get("State") or {}
    labels = config.get("Labels") or {}
    expected_labels = _expected_labels(profile, profile_sha256)
    if record.get("Name", "").lstrip("/") != name:
        raise DockerProvisionError("Container inspect name does not match")
    if any(labels.get(key) != value for key, value in expected_labels.items()):
        raise DockerProvisionError(
            "Existing container is not managed by this exact profile"
        )
    if record.get("Image") != image_id or config.get("Image") != profile["image"]:
        raise DockerProvisionError("Container image does not match the reviewed image")
    port_key = f"{profile['container_port']}/tcp"
    bindings = (host.get("PortBindings") or {}).get(port_key)
    if bindings != [{"HostIp": "127.0.0.1", "HostPort": str(host_port)}]:
        raise DockerProvisionError("Container port is not bound exactly to loopback")
    security_opt = host.get("SecurityOpt") or []
    cap_drop = host.get("CapDrop") or []
    resources = profile["resources"]
    expected_nano_cpus = int(float(resources["cpus"]) * 1_000_000_000)
    if (
        host.get("ReadonlyRootfs") is not True
        or "ALL" not in cap_drop
        or not any(item.startswith("no-new-privileges") for item in security_opt)
        or host.get("Privileged") is True
        or host.get("NetworkMode") == "host"
        or host.get("PidMode") == "host"
        or host.get("IpcMode") == "host"
        or (host.get("Binds") or [])
        or host.get("PidsLimit") != resources["pids_limit"]
        or host.get("Memory") != resources["memory_mb"] * 1024 * 1024
        or host.get("NanoCpus") != expected_nano_cpus
    ):
        raise DockerProvisionError(
            "Container security settings do not match the profile"
        )
    return {
        "running": state.get("Running") is True,
        "read_only_rootfs": True,
        "cap_drop": sorted(cap_drop),
        "no_new_privileges": True,
        "privileged": False,
        "bind_mounts": 0,
        "host_binding": f"127.0.0.1:{host_port}",
        "pids_limit": host["PidsLimit"],
        "memory_mb": host["Memory"] // (1024 * 1024),
        "cpus": host["NanoCpus"] / 1_000_000_000,
    }


def _port_is_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        try:
            listener.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _health_url(profile: dict[str, Any], host_port: int) -> str:
    return f"http://127.0.0.1:{host_port}{profile['health_path']}"


def _wait_for_health(profile: dict[str, Any], host_port: int) -> dict[str, Any]:
    deadline = time.monotonic() + profile["timeouts"]["health_seconds"]
    session = requests.Session()
    session.trust_env = False
    last_error = "service did not answer"
    try:
        while time.monotonic() < deadline:
            response = None
            try:
                response = session.get(
                    _health_url(profile, host_port),
                    timeout=min(5, profile["timeouts"]["health_seconds"]),
                    allow_redirects=False,
                    stream=True,
                    headers={"Accept": "application/json"},
                )
                if response.is_redirect or response.status_code != 200:
                    last_error = f"HTTP {response.status_code}"
                else:
                    content_type = (
                        response.headers.get("Content-Type", "")
                        .split(";", 1)[0]
                        .lower()
                    )
                    content_length = response.headers.get("Content-Length")
                    declared_too_large = False
                    if content_length:
                        try:
                            declared_too_large = int(content_length) > 65_536
                        except ValueError:
                            declared_too_large = True
                    if content_type != "application/json":
                        last_error = "health response was not application/json"
                    elif declared_too_large:
                        last_error = "health response exceeded 64 KiB"
                    else:
                        body = response.raw.read(65_537, decode_content=True)
                        if len(body) > 65_536:
                            last_error = "health response exceeded 64 KiB"
                        else:
                            payload = json.loads(body)
                            if (
                                isinstance(payload, dict)
                                and payload.get("status") == "ok"
                                and payload.get("service_id") == profile["service_id"]
                                and payload.get("model") == profile["model"]
                            ):
                                return payload
                            last_error = "health identity did not match the profile"
            except (
                requests.RequestException,
                json.JSONDecodeError,
                UnicodeDecodeError,
            ) as exc:
                last_error = type(exc).__name__
            finally:
                if response is not None:
                    response.close()
            time.sleep(0.25)
    finally:
        session.close()
    raise DockerProvisionError(f"Container health check failed: {last_error}")


def _client_config(
    profile: dict[str, Any], profile_sha256: str, image_id: str, host_port: int
) -> dict[str, Any]:
    tool = profile["tool"]
    config = {
        "name": tool["name"],
        "type": "DockerLLMClientTool",
        "description": tool["description"],
        "category": "special_tools",
        "cacheable": False,
        "mcp_annotations": {"readOnlyHint": True, "destructiveHint": False},
        "parameter": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": tool["max_prompt_chars"],
                },
                "temperature": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 2,
                    "default": tool["default_temperature"],
                },
                "max_tokens": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": tool["max_tokens_cap"],
                    "default": min(512, tool["max_tokens_cap"]),
                },
            },
            "required": ["prompt"],
            "additionalProperties": False,
        },
        "return_schema": {
            "type": "object",
            "properties": {
                "response": {"type": "string"},
                "model": {"type": "string"},
                "usage": {"type": ["object", "null"]},
                "provenance": {"type": "object"},
            },
            "required": ["response", "model", "provenance"],
        },
        "docker_llm": {
            "endpoint": f"http://127.0.0.1:{host_port}{profile['inference_path']}",
            "health_endpoint": f"http://127.0.0.1:{host_port}{profile['health_path']}",
            "service_id": profile["service_id"],
            "model": profile["model"],
            "request_timeout_seconds": profile["timeouts"]["inference_seconds"],
            "max_prompt_chars": tool["max_prompt_chars"],
            "max_tokens_cap": tool["max_tokens_cap"],
            "default_temperature": tool["default_temperature"],
            "image_id": image_id,
            "profile_sha256": profile_sha256,
        },
    }
    return _validated_client_config(config)


def _write_record(
    workspace: str | Path | None,
    profile: dict[str, Any],
    profile_sha256: str,
    image_id: str,
    docker_version: str,
    docker_context: str,
    container_name: str,
    host_port: int,
    security: dict[str, Any],
    health: dict[str, Any],
) -> dict[str, Any]:
    config = _client_config(profile, profile_sha256, image_id, host_port)
    body = {
        "version": _VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "profile_name": profile["profile_name"],
        "profile_sha256": profile_sha256,
        "image": profile["image"],
        "image_id": image_id,
        "docker_server_version": docker_version,
        "docker_context": docker_context,
        "container_name": container_name,
        "host_port": host_port,
        "security": security,
        "health": {
            "status": health["status"],
            "service_id": health["service_id"],
            "model": health.get("model"),
        },
        "tool_config": config,
    }
    record = {**body, "record_sha256": _canonical_digest(body)}
    path = _workspace_root(workspace) / "approved" / f"{config['name']}.json"
    _atomic_write_json(path, record)
    return {**record, "record_path": str(path)}


def plan_container(
    profile_path: str | Path,
    *,
    host_port: int = 9000,
    container_name: str | None = None,
) -> dict[str, Any]:
    """Return the exact bounded Docker command without contacting Docker."""
    profile, digest = load_profile(profile_path)
    port = _host_port(host_port)
    name = _container_name(container_name, profile)
    return {
        "profile_name": profile["profile_name"],
        "profile_sha256": digest,
        "container_name": name,
        "image": profile["image"],
        "host_binding": f"127.0.0.1:{port}:{profile['container_port']}",
        "docker_argv": ["docker", *_run_arguments(profile, digest, name, port)],
    }


def provision_container(
    profile_path: str | Path,
    *,
    host_port: int = 9000,
    container_name: str | None = None,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Start or reuse an exact managed container, verify it, then publish its client."""
    profile, digest = load_profile(profile_path)
    port = _host_port(host_port)
    name = _container_name(container_name, profile)
    docker_version, docker_context = _check_docker()
    image_id = _image_id(profile["image"])
    existing = _inspect_container(name)
    created = False
    started_existing = False
    try:
        if existing is None:
            if not _port_is_available(port):
                raise DockerProvisionError("Requested loopback port is already in use")
            _run_docker(_run_arguments(profile, digest, name, port), timeout=180)
            created = True
        else:
            existing_security = _security_summary(
                existing, profile, digest, image_id, name, port
            )
            if not existing_security["running"]:
                _run_docker(["container", "start", name])
                started_existing = True
        inspected = _inspect_container(name)
        if inspected is None:
            raise DockerProvisionError("Container disappeared after start")
        security = _security_summary(inspected, profile, digest, image_id, name, port)
        if not security["running"]:
            raise DockerProvisionError("Container is not running after start")
        health = _wait_for_health(profile, port)
        return _write_record(
            workspace,
            profile,
            digest,
            image_id,
            docker_version,
            docker_context,
            name,
            port,
            security,
            health,
        )
    except Exception:
        current = _inspect_container(name)
        if current is not None:
            try:
                _security_summary(current, profile, digest, image_id, name, port)
            except DockerProvisionError:
                pass
            else:
                if created:
                    _run_docker(["container", "rm", "--force", name], check=False)
                elif started_existing:
                    _run_docker(
                        ["container", "stop", "--time", "10", name], check=False
                    )
        raise


def status_container(
    profile_path: str | Path,
    *,
    host_port: int = 9000,
    container_name: str | None = None,
) -> dict[str, Any]:
    profile, digest = load_profile(profile_path)
    port = _host_port(host_port)
    name = _container_name(container_name, profile)
    docker_version, docker_context = _check_docker()
    record = _inspect_container(name)
    if record is None:
        return {
            "exists": False,
            "container_name": name,
            "docker_server_version": docker_version,
            "docker_context": docker_context,
        }
    image_id = _image_id(profile["image"])
    security = _security_summary(record, profile, digest, image_id, name, port)
    return {
        "exists": True,
        "container_name": name,
        "image_id": image_id,
        "docker_server_version": docker_version,
        "docker_context": docker_context,
        "security": security,
    }


def stop_container(
    profile_path: str | Path,
    *,
    host_port: int = 9000,
    container_name: str | None = None,
) -> dict[str, Any]:
    profile, digest = load_profile(profile_path)
    port = _host_port(host_port)
    name = _container_name(container_name, profile)
    _check_docker()
    image_id = _image_id(profile["image"])
    record = _inspect_container(name)
    if record is None:
        raise DockerProvisionError("Managed container does not exist")
    security = _security_summary(record, profile, digest, image_id, name, port)
    if security["running"]:
        _run_docker(["container", "stop", "--time", "10", name], timeout=30)
    return {"container_name": name, "stopped": True, "was_running": security["running"]}


def remove_container(
    profile_path: str | Path,
    *,
    host_port: int = 9000,
    container_name: str | None = None,
    workspace: str | Path | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    if confirm is not True:
        raise DockerProvisionError("Container removal requires explicit confirmation")
    profile, digest = load_profile(profile_path)
    port = _host_port(host_port)
    name = _container_name(container_name, profile)
    _check_docker()
    image_id = _image_id(profile["image"])
    record = _inspect_container(name)
    if record is None:
        raise DockerProvisionError("Managed container does not exist")
    _security_summary(record, profile, digest, image_id, name, port)
    config_path = (
        _workspace_root(workspace) / "approved" / f"{profile['tool']['name']}.json"
    )
    client_record_removed = config_path.exists()
    if config_path.exists():
        provisioned = _validated_record(_read_json(config_path))
        if not (
            provisioned["profile_sha256"] == digest
            and provisioned["image_id"] == image_id
            and provisioned["container_name"] == name
            and provisioned["host_port"] == port
        ):
            raise DockerProvisionError(
                "Client record does not match the managed container"
            )
    _run_docker(["container", "rm", "--force", name], timeout=30)
    if client_record_removed:
        config_path.unlink()
    return {
        "container_name": name,
        "removed": True,
        "client_record_removed": client_record_removed,
    }


def _validated_record(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict) or record.get("version") != _VERSION:
        raise DockerProvisionError("Provisioning record has an unsupported structure")
    if set(record) != {
        "version",
        "created_at",
        "profile_name",
        "profile_sha256",
        "image",
        "image_id",
        "docker_server_version",
        "docker_context",
        "container_name",
        "host_port",
        "security",
        "health",
        "tool_config",
        "record_sha256",
    }:
        raise DockerProvisionError(
            "Provisioning record fields do not match the contract"
        )
    body = {key: value for key, value in record.items() if key != "record_sha256"}
    if record.get("record_sha256") != _canonical_digest(body):
        raise DockerProvisionError(
            "Provisioning record digest does not match its content"
        )
    if not re.fullmatch(r"[0-9a-f]{64}", str(record.get("profile_sha256", ""))):
        raise DockerProvisionError("Provisioning profile digest is invalid")
    if not _SHA256_RE.fullmatch(str(record.get("image_id", ""))):
        raise DockerProvisionError("Provisioning image ID is invalid")
    if (
        not isinstance(record.get("profile_name"), str)
        or not _NAME_RE.fullmatch(record["profile_name"])
        or not isinstance(record.get("container_name"), str)
        or not _NAME_RE.fullmatch(record["container_name"])
        or not isinstance(record.get("host_port"), int)
        or not 1024 <= record["host_port"] <= 65535
        or not isinstance(record.get("security"), dict)
        or record["security"].get("read_only_rootfs") is not True
        or not isinstance(record.get("health"), dict)
        or record["health"].get("status") != "ok"
    ):
        raise DockerProvisionError("Provisioning record identity or policy is invalid")
    config = _validated_client_config(record.get("tool_config"))
    if (
        config["docker_llm"]["profile_sha256"] != record["profile_sha256"]
        or config["docker_llm"]["image_id"] != record["image_id"]
        or urlsplit(config["docker_llm"]["endpoint"]).port != record["host_port"]
        or config["docker_llm"]["service_id"] != record["health"].get("service_id")
        or config["docker_llm"]["model"] != record["health"].get("model")
    ):
        raise DockerProvisionError(
            "Client config does not match provisioning provenance"
        )
    return record


def load_provisioned_tool(
    tooluniverse,
    tool_name: str,
    *,
    workspace: str | Path | None = None,
) -> str:
    """Explicitly load one validated provisioned client into one ToolUniverse instance."""
    if not isinstance(tool_name, str) or not _TOOL_NAME_RE.fullmatch(tool_name):
        raise DockerProvisionError("Tool name is not valid")
    path = _workspace_root(workspace) / "approved" / f"{tool_name}.json"
    record = _validated_record(_read_json(path))
    config = record["tool_config"]
    if config["name"] != tool_name:
        raise DockerProvisionError("Provisioned tool name does not match its filename")
    if tool_name in tooluniverse.all_tool_dict:
        raise DockerProvisionError("Provisioned tool would replace an existing tool")
    return tooluniverse.register_custom_tool(
        tool_class=DockerLLMClientTool,
        tool_name=tool_name,
        tool_config=config,
        tool_instance=DockerLLMClientTool(config),
    )


__all__ = [
    "DockerProvisionError",
    "load_profile",
    "load_provisioned_tool",
    "plan_container",
    "provision_container",
    "remove_container",
    "status_container",
    "stop_container",
]
