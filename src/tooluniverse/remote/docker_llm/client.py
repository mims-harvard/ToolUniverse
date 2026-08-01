"""Bounded loopback client for an administrator-provisioned LLM container."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any
from urllib.parse import urlsplit

import requests

from ...base_tool import BaseTool
from ...tool_registry import register_tool

_MAX_RESPONSE_BYTES = 1_000_000
_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{2,44}$")
_SHA256_RE = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")


class DockerLLMClientError(RuntimeError):
    """Raised when a provisioned client contract or response fails closed."""


def _validated_client_config(config: Any) -> dict[str, Any]:
    if not isinstance(config, dict):
        raise DockerLLMClientError("Client configuration must be an object")
    allowed = {
        "name",
        "type",
        "description",
        "category",
        "cacheable",
        "mcp_annotations",
        "parameter",
        "return_schema",
        "docker_llm",
    }
    if set(config) - allowed:
        raise DockerLLMClientError("Client configuration contains unknown fields")
    name = config.get("name")
    if not isinstance(name, str) or not _NAME_RE.fullmatch(name):
        raise DockerLLMClientError("Client tool name is not valid")
    description = config.get("description")
    if not isinstance(description, str) or not 20 <= len(description.strip()) <= 1000:
        raise DockerLLMClientError("Client description must contain 20-1000 characters")
    if config.get("type") != "DockerLLMClientTool":
        raise DockerLLMClientError("Client type must be DockerLLMClientTool")
    runtime = config.get("docker_llm")
    if not isinstance(runtime, dict):
        raise DockerLLMClientError("docker_llm runtime configuration is required")
    if set(runtime) != {
        "endpoint",
        "service_id",
        "model",
        "request_timeout_seconds",
        "max_prompt_chars",
        "max_tokens_cap",
        "image_id",
        "profile_sha256",
    }:
        raise DockerLLMClientError(
            "docker_llm runtime fields do not match the contract"
        )
    endpoint = runtime["endpoint"]
    parsed = urlsplit(endpoint) if isinstance(endpoint, str) else None
    if (
        parsed is None
        or parsed.scheme != "http"
        or parsed.hostname != "127.0.0.1"
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is None
        or not 1024 <= parsed.port <= 65535
        or not parsed.path.startswith("/")
        or ".." in parsed.path
    ):
        raise DockerLLMClientError(
            "Inference endpoint must be a fixed loopback HTTP URL"
        )
    for field, maximum in (("service_id", 80), ("model", 200)):
        value = runtime[field]
        if (
            not isinstance(value, str)
            or not value
            or len(value) > maximum
            or any(ord(character) < 32 for character in value)
        ):
            raise DockerLLMClientError(f"docker_llm.{field} is invalid")
    timeout = runtime["request_timeout_seconds"]
    prompt_limit = runtime["max_prompt_chars"]
    token_limit = runtime["max_tokens_cap"]
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, int)
        or not 1 <= timeout <= 120
    ):
        raise DockerLLMClientError("Request timeout must be 1-120 seconds")
    if (
        isinstance(prompt_limit, bool)
        or not isinstance(prompt_limit, int)
        or not 100 <= prompt_limit <= 100_000
    ):
        raise DockerLLMClientError("Prompt limit must be 100-100000 characters")
    if (
        isinstance(token_limit, bool)
        or not isinstance(token_limit, int)
        or not 1 <= token_limit <= 8192
    ):
        raise DockerLLMClientError("Token limit must be 1-8192")
    if not _SHA256_RE.fullmatch(str(runtime["image_id"])):
        raise DockerLLMClientError("Container image ID is invalid")
    if not re.fullmatch(r"[0-9a-f]{64}", str(runtime["profile_sha256"])):
        raise DockerLLMClientError("Profile digest is invalid")
    parameter = config.get("parameter")
    if (
        not isinstance(parameter, dict)
        or parameter.get("additionalProperties") is not False
    ):
        raise DockerLLMClientError(
            "Client parameters must reject additional properties"
        )
    return config


def _read_bounded_response(response: requests.Response) -> tuple[bytes, dict[str, Any]]:
    if response.is_redirect or response.is_permanent_redirect:
        raise DockerLLMClientError("Inference redirects are prohibited")
    if response.status_code != 200:
        raise DockerLLMClientError(
            f"Inference endpoint returned HTTP {response.status_code}"
        )
    content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
    if content_type != "application/json":
        raise DockerLLMClientError("Inference endpoint did not return application/json")
    length = response.headers.get("Content-Length")
    if length:
        try:
            if int(length) > _MAX_RESPONSE_BYTES:
                raise DockerLLMClientError("Inference response exceeds the 1 MB limit")
        except ValueError as exc:
            raise DockerLLMClientError("Inference Content-Length is invalid") from exc
    body = bytearray()
    for chunk in response.iter_content(chunk_size=65_536):
        body.extend(chunk)
        if len(body) > _MAX_RESPONSE_BYTES:
            raise DockerLLMClientError("Inference response exceeds the 1 MB limit")
    try:
        payload = json.loads(bytes(body))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DockerLLMClientError("Inference response is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise DockerLLMClientError("Inference response must be a JSON object")
    return bytes(body), payload


@register_tool("DockerLLMClientTool")
class DockerLLMClientTool(BaseTool):
    """Call one fixed, loopback-only OpenAI-compatible inference endpoint."""

    def __init__(self, tool_config):
        super().__init__(_validated_client_config(tool_config))

    def run(self, arguments=None, **_: Any):
        values = {} if arguments is None else arguments
        if not isinstance(values, dict):
            raise DockerLLMClientError("Tool arguments must be an object")
        runtime = self.tool_config["docker_llm"]
        prompt = values.get("prompt")
        if (
            not isinstance(prompt, str)
            or not prompt.strip()
            or len(prompt) > runtime["max_prompt_chars"]
            or any(
                ord(character) < 32 and character not in "\n\r\t"
                for character in prompt
            )
        ):
            raise DockerLLMClientError(
                "prompt is empty, too long, or contains control characters"
            )
        temperature = values.get("temperature", 0.0)
        max_tokens = values.get("max_tokens", min(512, runtime["max_tokens_cap"]))
        if (
            isinstance(temperature, bool)
            or not isinstance(temperature, (int, float))
            or not 0 <= temperature <= 2
        ):
            raise DockerLLMClientError("temperature must be between 0 and 2")
        if (
            isinstance(max_tokens, bool)
            or not isinstance(max_tokens, int)
            or not 1 <= max_tokens <= runtime["max_tokens_cap"]
        ):
            raise DockerLLMClientError("max_tokens exceeds the reviewed limit")
        request_body = {
            "model": runtime["model"],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        session = requests.Session()
        session.trust_env = False
        response = None
        try:
            response = session.post(
                runtime["endpoint"],
                json=request_body,
                timeout=runtime["request_timeout_seconds"],
                allow_redirects=False,
                stream=True,
                headers={"Accept": "application/json"},
            )
            raw, payload = _read_bounded_response(response)
        except requests.RequestException as exc:
            raise DockerLLMClientError("Loopback inference request failed") from exc
        finally:
            if response is not None:
                response.close()
            session.close()
        choices = payload.get("choices")
        if not isinstance(choices, list) or len(choices) != 1:
            raise DockerLLMClientError(
                "Inference response must contain exactly one choice"
            )
        choice = choices[0]
        message = choice.get("message") if isinstance(choice, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if (
            not isinstance(content, str)
            or not content
            or len(content) > _MAX_RESPONSE_BYTES
        ):
            raise DockerLLMClientError("Inference choice content is invalid")
        usage = payload.get("usage")
        if usage is not None and not isinstance(usage, dict):
            raise DockerLLMClientError("Inference usage must be an object")
        response_model = payload.get("model", runtime["model"])
        if (
            not isinstance(response_model, str)
            or not response_model
            or len(response_model) > 200
            or any(ord(character) < 32 for character in response_model)
        ):
            raise DockerLLMClientError("Inference model identifier is invalid")
        return {
            "status": "success",
            "data": {
                "response": content,
                "model": response_model,
                "usage": usage,
                "provenance": {
                    "endpoint": runtime["endpoint"],
                    "service_id": runtime["service_id"],
                    "image_id": runtime["image_id"],
                    "profile_sha256": runtime["profile_sha256"],
                    "payload_sha256": hashlib.sha256(raw).hexdigest(),
                    "http_status": 200,
                    "redirects": 0,
                },
            },
        }


__all__ = ["DockerLLMClientError", "DockerLLMClientTool"]
