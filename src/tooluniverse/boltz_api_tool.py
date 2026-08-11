"""ToolUniverse wrappers for the official hosted Boltz API Python SDK."""

from __future__ import annotations

import os
from typing import Any, Dict

from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("BoltzAPITool")
class BoltzAPITool(BaseTool):
    """Dispatch approved Boltz SDK resources while preserving SDK response data."""

    SUPPORTED_RESOURCES = {
        "predictions.structure_and_binding": {
            "retrieve",
            "list",
            "delete_data",
            "estimate_cost",
            "start",
            "run",
        },
        "predictions.adme": {
            "retrieve",
            "list",
            "delete_data",
            "estimate_cost",
            "start",
            "run",
        },
        "protein.design": {
            "retrieve",
            "list",
            "delete_data",
            "estimate_cost",
            "list_results",
            "resume",
            "start",
            "stop",
            "run",
        },
        "protein.sequence_redesign": {
            "retrieve",
            "list",
            "delete_data",
            "estimate_cost",
            "list_results",
            "resume",
            "start",
            "stop",
        },
        "protein.library_screen": {
            "retrieve",
            "list",
            "delete_data",
            "estimate_cost",
            "list_results",
            "resume",
            "start",
            "stop",
            "run",
        },
        "small_molecule.design": {
            "retrieve",
            "list",
            "delete_data",
            "estimate_cost",
            "list_results",
            "resume",
            "start",
            "stop",
            "run",
        },
        "small_molecule.library_screen": {
            "retrieve",
            "list",
            "delete_data",
            "estimate_cost",
            "list_results",
            "resume",
            "start",
            "stop",
            "run",
        },
        "admin.workspaces": {
            "create",
            "retrieve",
            "update",
            "list",
            "archive",
            "retrieve_spending_limit",
            "set_spending_limit",
        },
        "admin.api_keys": {"create", "list", "revoke"},
        "admin.usage": {"list"},
        "auth": {"me"},
        "cli": {"version"},
    }
    DEFAULT_RESOURCE = "predictions.structure_and_binding"
    DEFAULT_MODEL = "boltz-2.1"
    LOCAL_ARGUMENTS = {"confirm"}

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        fields = tool_config.get("fields", {})
        self.resource_path = fields.get("resource", self.DEFAULT_RESOURCE)
        self.operation = fields.get("operation")
        self.positional_parameters = fields.get("positional_parameters", [])
        self.require_idempotency = fields.get("require_idempotency", False)
        self.confirmation_message = fields.get("confirmation_message")
        self.timeout = tool_config.get("timeout", 60)
        self.max_retries = tool_config.get("max_retries", 2)
        self._client = None

    def _get_client(self):
        """Create the official SDK client lazily so tool loading stays offline."""
        if self._client is not None:
            return self._client

        api_key = os.environ.get("BOLTZ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "BOLTZ_API_KEY is required. Create a workspace or test key in "
                "the Boltz API Console and expose it through the environment."
            )

        try:
            from boltz_api import Boltz
        except ImportError as exc:
            raise RuntimeError(
                "The official 'boltz-api' package is required. Reinstall "
                "ToolUniverse or run: pip install boltz-api"
            ) from exc

        self._client = Boltz(
            api_key=api_key,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )
        return self._client

    @staticmethod
    def _serialize_response(response: Any) -> Any:
        """Convert SDK models and pages into JSON-safe values."""
        if isinstance(response, os.PathLike):
            return os.fspath(response)
        if hasattr(response, "to_dict"):
            return response.to_dict(mode="json")
        if hasattr(response, "model_dump"):
            return response.model_dump(mode="json")
        return response

    @staticmethod
    def _error_response(exc: Exception) -> Dict[str, Any]:
        """Normalize official SDK errors without exposing credentials."""
        body = getattr(exc, "body", None)
        message = getattr(exc, "message", None) or str(exc)
        result: Dict[str, Any] = {"status": "error", "error": message}

        status_code = getattr(exc, "status_code", None)
        if status_code is not None:
            result["status_code"] = status_code

        if isinstance(body, dict):
            payload = body.get("error", body)
            if isinstance(payload, dict):
                if payload.get("code"):
                    result["code"] = str(payload["code"])
                if payload.get("message"):
                    result["error"] = str(payload["message"])
                if payload.get("details") is not None:
                    result["details"] = payload["details"]

        return result

    def _get_resource(self):
        resource = self._get_client()
        for component in self.resource_path.split("."):
            resource = getattr(resource, component)
        return resource

    def _validate_dispatch(self, arguments: Dict[str, Any]) -> None:
        operations = self.SUPPORTED_RESOURCES.get(self.resource_path)
        if operations is None or self.operation not in operations:
            raise ValueError(
                f"Unsupported Boltz API operation: {self.resource_path}.{self.operation}"
            )

        if self.confirmation_message and arguments.get("confirm") is not True:
            raise ValueError(self.confirmation_message)

        if self.require_idempotency:
            key = arguments.get("idempotency_key")
            if not isinstance(key, str) or not key.strip():
                raise ValueError(
                    "idempotency_key is required for submission to prevent duplicate billing"
                )

        for name in self.positional_parameters:
            value = arguments.get(name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")

        # Preserve the validation and default model behavior of the original
        # three structure-and-binding wrappers.
        if self.resource_path == self.DEFAULT_RESOURCE and self.operation in {
            "estimate_cost",
            "start",
        }:
            input_data = arguments.get("input")
            if not isinstance(input_data, dict) or not input_data.get("entities"):
                raise ValueError("input.entities must be a non-empty array")
            model = arguments.get("model", self.DEFAULT_MODEL)
            if model != self.DEFAULT_MODEL:
                raise ValueError("model must be 'boltz-2.1'")

    def _invoke(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        self._validate_dispatch(arguments)
        kwargs = {
            key: value
            for key, value in arguments.items()
            if key not in self.LOCAL_ARGUMENTS and value is not None
        }

        if self.resource_path == self.DEFAULT_RESOURCE and self.operation in {
            "estimate_cost",
            "start",
        }:
            kwargs.setdefault("model", self.DEFAULT_MODEL)

        positional = [kwargs.pop(name) for name in self.positional_parameters]
        method = getattr(self._get_resource(), self.operation)
        response = method(*positional, **kwargs)
        return {"status": "success", "data": self._serialize_response(response)}

    def run(self, arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Execute one configured official Boltz SDK method."""
        try:
            return self._invoke(arguments or {})
        except Exception as exc:
            return self._error_response(exc)
