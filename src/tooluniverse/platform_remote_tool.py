"""A narrow proxy for one explicitly connected ToolUniverse Platform resource."""

from __future__ import annotations

import json
import math
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict

from .base_tool import BaseTool
from .remote_connections import BORROWER_KEY_ENV, api_keys_page, global_env_file
from .tool_registry import register_tool


_MAX_RESPONSE_BYTES = 16 << 20
_DEFAULT_TIMEOUT = 930.0
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
        # The platform enforces each published tool's own deadline, up to 15 minutes, and
        # answers when it passes. Waiting a little longer than that lets its answer arrive. The
        # default was 120 seconds: measured, a tool its owner configured for 300 seconds failed
        # for the person calling it at 121 with "Error: timed out".
        self.timeout = float(tool_config.get("timeout", _DEFAULT_TIMEOUT))
        if not math.isfinite(self.timeout) or not 1 <= self.timeout <= _DEFAULT_TIMEOUT:
            raise ValueError(
                f"PlatformRemoteTool timeout must be between 1 and {_DEFAULT_TIMEOUT:.0f} seconds"
            )
        self._opener = urllib.request.build_opener(_NoRedirect)

    def _request(
        self,
        path: str,
        api_key: str,
        *,
        method: str = "GET",
        payload=None,
        timeout: float | None = None,
    ):
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError("platform returned an unsafe job status URL")
        body = None
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "User-Agent": "tooluniverse-platform-remote/1",
        }
        if payload is not None:
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self.base_url + path, data=body, method=method, headers=headers
        )
        # The whole remaining deadline: a synchronous call is one request that lasts as long as
        # the tool does, so a fixed per-request cap was a second, shorter deadline.
        request_timeout = self.timeout if timeout is None else timeout
        if request_timeout <= 0:
            raise TimeoutError("platform tool deadline expired")
        with self._opener.open(request, timeout=request_timeout) as response:
            raw = response.read(_MAX_RESPONSE_BYTES + 1)
        if len(raw) > _MAX_RESPONSE_BYTES:
            raise ValueError("platform tool response exceeded 16 MiB")
        return json.loads(raw.decode("utf-8"))

    def _wait_for_job(self, api_key: str, payload: dict, deadline: float):
        status_path = str(payload.get("status_url", ""))
        job_id = str(payload.get("job_id", ""))
        expected_path = f"/remote-tool-jobs/{job_id}"
        if not job_id or status_path != expected_path:
            raise ValueError("platform returned an invalid asynchronous job handle")

        def request_cancellation() -> None:
            try:
                self._request(
                    status_path,
                    api_key,
                    method="DELETE",
                    timeout=min(5, self.timeout),
                )
            except Exception:
                pass

        try:
            while time.monotonic() < deadline:
                remaining = deadline - time.monotonic()
                job = self._request(status_path, api_key, timeout=remaining)
                status = job.get("status")
                if status == "succeeded":
                    result = job.get("result")
                    if isinstance(result, dict) and "value" in result:
                        return result["value"]
                    return result
                if status in {"failed", "cancelled"}:
                    return {
                        "status": "error",
                        "error": str(job.get("error") or f"remote job {status}"),
                        "job_id": job_id,
                    }
                time.sleep(min(1, max(0, deadline - time.monotonic())))
        except KeyboardInterrupt:
            request_cancellation()
            raise
        except Exception:
            # A timed-out poll can otherwise leave an expensive provider job
            # running after the local caller has already given up.
            request_cancellation()
            raise
        request_cancellation()
        return {
            "status": "error",
            "error": "remote job timed out and cancellation was requested",
            "job_id": job_id,
        }

    @staticmethod
    def _api_key_and_source() -> tuple[str, str]:
        for name in (BORROWER_KEY_ENV, "TOOLUNIVERSE_SERVICE_KEY"):
            value = (os.getenv(name) or "").strip()
            if value:
                return value, name
        return "", ""

    @classmethod
    def _api_key(cls) -> str:
        return cls._api_key_and_source()[0]

    def _missing_key_message(self) -> str:
        # The old text said to "set the variable", which in practice means export it in one
        # shell -- and the tool is then missing again from the next terminal. The global .env
        # is loaded on every start without overriding the shell, so saving it there once works.
        return (
            f"This connected platform tool requires {BORROWER_KEY_ENV}. Create a private "
            f"connection at {api_keys_page(self.base_url)} and save it once as "
            f"{BORROWER_KEY_ENV}=<your key> in {global_env_file()} so every terminal has it."
        )

    def run(self, arguments: Dict[str, Any]):
        api_key, key_source = self._api_key_and_source()
        if not api_key:
            return {"status": "error", "error": self._missing_key_message()}

        try:
            deadline = time.monotonic() + self.timeout
            payload = self._request(
                "/tools/call",
                api_key,
                method="POST",
                payload={"tool": self.resource_id, "arguments": arguments},
                timeout=deadline - time.monotonic(),
            )
            if payload.get("job_id"):
                return self._wait_for_job(api_key, payload, deadline)
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
            if exc.code == 403 and "computer-only connection" in detail:
                # Someone who also shares their own machine has the computer-only key in
                # TOOLUNIVERSE_SERVICE_KEY, and with no TU_API_KEY that is what got sent. The
                # platform's sentence is accurate but assumes the reader knows there are two
                # kinds of key.
                detail = (
                    f"{key_source} holds this computer's sharing connection, which can "
                    f"register this machine but cannot call tools. "
                    + self._missing_key_message()
                )
            return {"status": "error", "error": detail}
        except TimeoutError:
            return {
                "status": "error",
                "error": (
                    f"The tool did not answer within {self.timeout:.0f} seconds. It may still be "
                    f"running on its owner's machine, so wait before calling it again rather "
                    f"than starting it twice."
                ),
            }
        except Exception as exc:
            return {"status": "error", "error": str(exc)}
