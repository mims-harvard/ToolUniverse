"""A narrow proxy for one explicitly connected ToolUniverse Platform resource."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict

from .base_tool import BaseTool
from .tool_registry import register_tool


_MAX_RESPONSE_BYTES = 16 << 20
_DEFAULT_BASE_URL = "https://tooluniverse-backend.onrender.com"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(
            req.full_url, code, "unexpected authenticated redirect", headers, fp
        )


def _validated_base_url(value: str) -> str:
    candidate = value.rstrip("/")
    parsed = urllib.parse.urlsplit(candidate)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname:
        raise ValueError("platform base URL must use https://")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("platform base URL must not contain credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("platform base URL must not contain a query or fragment")
    if parsed.scheme == "http" and parsed.hostname not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        raise ValueError(
            "platform base URL must use https:// outside local development"
        )
    return candidate


@register_tool("PlatformRemoteTool")
class PlatformRemoteTool(BaseTool):
    """Call exactly one published platform tool through ``/tools/call``."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.resource_id = str(tool_config.get("resource_id", "")).strip()
        if not self.resource_id:
            raise ValueError("PlatformRemoteTool requires resource_id")
        configured_url = tool_config.get("base_url") or os.getenv("TU_BASE_URL")
        self.base_url = _validated_base_url(configured_url or _DEFAULT_BASE_URL)
        self.timeout = float(tool_config.get("timeout", 120))
        self._opener = urllib.request.build_opener(_NoRedirect)

    @staticmethod
    def _api_key() -> str:
        return (
            os.getenv("TU_API_KEY") or os.getenv("TOOLUNIVERSE_SERVICE_KEY") or ""
        ).strip()

    def run(self, arguments: Dict[str, Any]):
        api_key = self._api_key()
        if not api_key:
            return {
                "status": "error",
                "error": (
                    "This connected platform tool requires TU_API_KEY. "
                    "Create a private connection at "
                    "https://connect.aiscientist.tools/api-keys and set the variable."
                ),
            }

        body = json.dumps(
            {"tool": self.resource_id, "arguments": arguments},
            separators=(",", ":"),
        ).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + "/tools/call",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "tooluniverse-platform-remote/1",
            },
        )
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                raw = response.read(_MAX_RESPONSE_BYTES + 1)
            if len(raw) > _MAX_RESPONSE_BYTES:
                raise ValueError("platform tool response exceeded 16 MiB")
            payload = json.loads(raw.decode("utf-8"))
            return payload.get("result", payload)
        except urllib.error.HTTPError as exc:
            detail = f"platform returned HTTP {exc.code}"
            try:
                raw = exc.read(_MAX_RESPONSE_BYTES + 1)
                parsed = json.loads(raw.decode("utf-8"))
                if isinstance(parsed, dict) and parsed.get("detail"):
                    detail = str(parsed["detail"])
            except Exception:
                pass
            return {"status": "error", "error": detail}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}
