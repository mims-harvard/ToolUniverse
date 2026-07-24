"""Replicate API wrapper for ToolUniverse.

A single tool class (``ReplicateTool``) that runs a prediction on any model
hosted on `Replicate <https://replicate.com>`_ — the platform that serves
thousands of community ML models (image generation, protein structure,
language, embeddings, audio, ...). This complements the HuggingFace inference
tool by reaching the large catalogue of models published only on Replicate.

Flow (Replicate's documented predictions API)
---------------------------------------------
Replicate predictions are asynchronous:

1. **Create** a prediction:

   * by *version hash* — ``POST /v1/predictions`` with
     ``{"version": "<64-hex-hash>", "input": {...}}``; or
   * by *model* (owner/name) — ``POST /v1/models/{owner}/{name}/predictions``
     with ``{"input": {...}}`` (runs the model's default/latest version).

   The response is a *prediction object* with an ``id``, a ``status``
   (``starting`` | ``processing`` | ``succeeded`` | ``failed`` | ``canceled``),
   a ``urls.get`` poll URL, and — once finished — an ``output`` field.

2. **Poll** ``urls.get`` (equivalently ``GET /v1/predictions/{id}``) until
   ``status`` is terminal (``succeeded`` / ``failed`` / ``canceled``).

3. Return ``output`` (and ``logs`` / ``error`` on failure).

This tool performs bounded polling so a single call stays within ~30 s. If the
prediction is still running when the budget is exhausted, it returns a
``processing`` status together with the prediction ``id`` and poll URL so the
caller can check again later (via ``get_prediction``) rather than hanging.

Authentication
--------------
A token is **required** and is read only from the ``REPLICATE_API_TOKEN``
environment variable — never from a tool parameter. The header sent is
``Authorization: Bearer <token>`` (Replicate also accepts the ``Token``
scheme, but ``Bearer`` is used here).

The tool never raises: every path returns a ``{"status": ...}`` dict. A missing
token returns a clean, actionable error.
"""

import os
import time
from typing import Any, Dict, Optional

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

_BASE_URL = "https://api.replicate.com/v1"
_HTTP_TIMEOUT = 25  # per-request socket timeout (s)
_POLL_BUDGET = 22  # total wall-clock budget spent polling (s)
_POLL_INTERVAL = 2  # sleep between polls (s)
_TERMINAL = {"succeeded", "failed", "canceled"}
_VERSION_HASH_LEN = 64  # Replicate version ids are 64-char hex


def _err(msg: str, **extra: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"status": "error", "error": msg}
    out.update(extra)
    return out


def _ok(data: Any, **metadata: Any) -> Dict[str, Any]:
    meta = {"provider": "replicate"}
    meta.update(metadata)
    return {"status": "success", "data": data, "metadata": meta}


@register_tool("ReplicateTool")
class ReplicateTool(BaseTool):
    """Run / fetch predictions on Replicate-hosted models (async, polled)."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})

    # ------------------------------------------------------------------ #
    # dispatch
    # ------------------------------------------------------------------ #
    def run(self, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        arguments = arguments or {}
        operation = arguments.get("operation")
        handlers = {
            "run_prediction": self._run_prediction,
            "get_prediction": self._get_prediction,
        }
        handler = handlers.get(operation)
        if handler is None:
            return _err(
                f"Unknown or missing operation: {operation!r}. "
                f"Expected one of {sorted(handlers)}."
            )

        token = os.environ.get("REPLICATE_API_TOKEN", "")
        if not token:
            return _err(
                "Missing REPLICATE_API_TOKEN. Replicate requires an API token. "
                "Create one at https://replicate.com/account/api-tokens and set "
                "it in the environment: export REPLICATE_API_TOKEN=r8_...  "
                "(the token is read from the environment only, never passed as "
                "a tool parameter)."
            )

        try:
            return handler(arguments, token)
        except Exception as exc:  # never raise out of run()
            return _err(f"Unexpected error: {type(exc).__name__}: {exc}")

    # ------------------------------------------------------------------ #
    # shared HTTP helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _headers(token: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def _request(
        self,
        method: str,
        url: str,
        token: str,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make one HTTP call; return {"_json": body} or a ready error dict."""
        try:
            resp = requests.request(
                method,
                url,
                headers=self._headers(token),
                json=json_body,
                timeout=_HTTP_TIMEOUT,
            )
        except requests.exceptions.Timeout:
            return _err(f"Timeout after {_HTTP_TIMEOUT}s contacting Replicate ({url}).")
        except requests.exceptions.RequestException as exc:
            return _err(f"Network error contacting Replicate: {exc}")

        if resp.status_code in (401, 403):
            return _err(
                "Unauthorized (HTTP "
                f"{resp.status_code}). Check that REPLICATE_API_TOKEN is valid "
                "and has access to this model."
            )
        if resp.status_code == 404:
            return _err(
                f"Not found (HTTP 404) at {url}. Check the model owner/name or "
                "version hash, or the prediction id."
            )
        if resp.status_code == 429:
            return _err("Rate limited by Replicate (HTTP 429). Retry later.")
        # Prediction create returns 201; GET returns 200.
        if resp.status_code not in (200, 201):
            detail = ""
            try:
                body = resp.json()
                detail = body.get("detail") or body.get("title") or str(body)
            except Exception:
                detail = resp.text[:300]
            return _err(f"HTTP {resp.status_code} from Replicate: {detail}")

        try:
            return {"_json": resp.json()}
        except ValueError:
            return _err(f"Non-JSON response from Replicate: {resp.text[:200]}")

    # ------------------------------------------------------------------ #
    # create + poll a prediction
    # ------------------------------------------------------------------ #
    def _run_prediction(self, args: Dict[str, Any], token: str) -> Dict[str, Any]:
        model = args.get("model")
        version = args.get("version")
        model_input = args.get("input")

        if not model and not version:
            return _err(
                "Provide either 'model' (owner/name, e.g. "
                "'replicate/hello-world') or 'version' (a 64-char version hash)."
            )
        if model and version:
            return _err(
                "Provide only one of 'model' or 'version', not both. Use "
                "'version' to pin an exact version hash; use 'model' to run the "
                "model's latest/default version."
            )
        if not isinstance(model_input, dict):
            return _err(
                "'input' must be an object (dict) of the model's inputs, e.g. "
                '{"text": "hello"}. Consult the model page on replicate.com for '
                "its exact input schema."
            )

        # Build the create request per Replicate's documented endpoints.
        if version:
            if not self._looks_like_version_hash(version):
                return _err(
                    f"'version' should be a {_VERSION_HASH_LEN}-char hex version "
                    "hash (find it on the model's API page). To run by name "
                    "instead, pass 'model' as 'owner/name'."
                )
            create_url = f"{_BASE_URL}/predictions"
            body = {"version": version, "input": model_input}
        else:
            owner_name = str(model).strip().strip("/")
            if owner_name.count("/") != 1:
                return _err(
                    f"'model' must be 'owner/name' (got {model!r}), e.g. "
                    "'replicate/hello-world'."
                )
            create_url = f"{_BASE_URL}/models/{owner_name}/predictions"
            body = {"input": model_input}

        created = self._request("POST", create_url, token, json_body=body)
        if "_json" not in created:
            return created
        prediction = created["_json"]

        prediction = self._poll_until_done(prediction, token)
        return self._format_prediction(prediction)

    def _poll_until_done(
        self, prediction: Dict[str, Any], token: str
    ) -> Dict[str, Any]:
        """Poll urls.get until terminal status or the time budget runs out."""
        deadline = time.monotonic() + _POLL_BUDGET
        poll_url = (prediction.get("urls") or {}).get("get")
        if not poll_url:
            pred_id = prediction.get("id")
            poll_url = f"{_BASE_URL}/predictions/{pred_id}" if pred_id else None

        while prediction.get("status") not in _TERMINAL:
            if not poll_url or time.monotonic() >= deadline:
                break
            time.sleep(_POLL_INTERVAL)
            polled = self._request("GET", poll_url, token)
            if "_json" not in polled:
                # Surface the error but keep the last known prediction state.
                prediction["_poll_error"] = polled.get("error")
                break
            prediction = polled["_json"]

        return prediction

    # ------------------------------------------------------------------ #
    # fetch an existing prediction by id
    # ------------------------------------------------------------------ #
    def _get_prediction(self, args: Dict[str, Any], token: str) -> Dict[str, Any]:
        prediction_id = args.get("prediction_id")
        if not prediction_id or not str(prediction_id).strip():
            return _err("Missing required parameter: prediction_id")
        url = f"{_BASE_URL}/predictions/{str(prediction_id).strip()}"
        fetched = self._request("GET", url, token)
        if "_json" not in fetched:
            return fetched
        return self._format_prediction(fetched["_json"])

    # ------------------------------------------------------------------ #
    # formatting
    # ------------------------------------------------------------------ #
    def _format_prediction(self, prediction: Dict[str, Any]) -> Dict[str, Any]:
        status = prediction.get("status")
        pred_id = prediction.get("id")
        poll_url = (prediction.get("urls") or {}).get("get")

        data = {
            "id": pred_id,
            "status": status,
            "model": prediction.get("model"),
            "version": prediction.get("version"),
            "output": prediction.get("output"),
            "error": prediction.get("error"),
            "logs": prediction.get("logs"),
            "poll_url": poll_url,
        }

        if status == "failed":
            return _err(
                f"Replicate prediction {pred_id} failed: "
                f"{prediction.get('error') or 'unknown error'}",
                prediction_id=pred_id,
                logs=prediction.get("logs"),
            )

        meta: Dict[str, Any] = {"prediction_status": status}
        if status not in _TERMINAL:
            # Still running when the budget expired — return id so the caller
            # can poll later with get_prediction.
            meta["note"] = (
                "Prediction is still running. Call this tool again with "
                f"operation='get_prediction' and prediction_id='{pred_id}' to "
                "retrieve the result, or poll the returned poll_url."
            )
        return _ok(data, **meta)

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _looks_like_version_hash(value: Any) -> bool:
        s = str(value).strip()
        return len(s) == _VERSION_HASH_LEN and all(
            c in "0123456789abcdefABCDEF" for c in s
        )
