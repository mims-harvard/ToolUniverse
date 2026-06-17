"""
IBM RXN for Chemistry API tool for ToolUniverse.

IBM RXN for Chemistry provides ML-based chemical reaction prediction:
  * Forward reaction prediction: given reactant SMILES (dot-separated),
    predict the most likely product SMILES.
  * Retrosynthesis: given a target product SMILES, predict precursor
    routes (disconnections back to purchasable building blocks).

API:  Direct REST against https://rxn.app.accelerate.science
      (formerly https://rxn.res.ibm.com). This tool uses plain `requests`;
      it does NOT depend on the optional `rxn4chemistry` Python package.
Auth: Requires a free API key. Read ONLY from the environment variable
      RXN4CHEMISTRY_API_KEY. Register at https://rxn.app.accelerate.science
      (Profile -> "My profile" -> API key). The key is sent verbatim in the
      `Authorization` header (NOT a Bearer token).

Documented request shape (verified against the official rxn4chemistry
wrapper route definitions, api_version "v1"):

  Base path:        {base}/rxn/api/api/v1
  Headers:          {"Authorization": <api_key>, "Content-Type": "application/json"}

  Project context (a project id is required for predictions):
    GET  {base}/rxn/api/api/v1/projects
         -> {"payload": [{"id": "<project_id>", "name": "...", ...}, ...]}
         The tool uses an explicit `project_id` arg if given, otherwise the
         first project returned, otherwise it creates one:
    POST {base}/rxn/api/api/v1/projects   body {"name": "<name>"}

  Forward reaction prediction (async submit -> poll):
    POST {base}/rxn/api/api/v1/predictions/pr?projectId=<pid>&aiModel=<model>
         body {"reactants": "<smiles.smiles>", "aiModel": "<model>"}
         -> {"payload": {"id": "<prediction_id>"}}
    GET  {base}/rxn/api/api/v1/predictions/<prediction_id>
         -> poll until payload.status == "SUCCESS";
            product at payload.attempts[0].smiles (+ confidence).

  Retrosynthesis (async submit -> poll):
    POST {base}/rxn/api/api/v1/retrosynthesis/rs?projectId=<pid>&aiModel=<model>
         body {"product": "<smiles>", "aiModel": "<model>",
               "isInteractive": false, "parameters": {...}}
         -> {"payload": {"id": "<prediction_id>"}}
    GET  {base}/rxn/api/api/v1/retrosynthesis/<prediction_id>
         -> poll until payload.status == "SUCCESS";
            routes at payload.retrosyntheticPaths (each with sequences of
            reactant SMILES and a confidence score).

Polling is bounded: each HTTP request uses a 30s timeout, and the poll loop
is capped by `max_wait_time` (default 60s) at `poll_interval` (default 5s).
On timeout the tool returns a clean error (status="error"), never raises.
"""

import os
import time
from typing import Any, Dict, List, Optional

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

DEFAULT_BASE_URL = "https://rxn.app.accelerate.science"
API_VERSION = "v1"
DEFAULT_AI_MODEL = "2020-08-10"
DEFAULT_PROJECT_NAME = "tooluniverse"
ENV_KEY = "RXN4CHEMISTRY_API_KEY"

REQUEST_TIMEOUT = 30  # seconds, per HTTP request
DEFAULT_POLL_INTERVAL = 5  # seconds between polls
DEFAULT_MAX_WAIT_TIME = 60  # seconds total polling budget


@register_tool("RXNChemistryTool")
class RXNChemistryTool(BaseTool):
    """
    Wrap IBM RXN for Chemistry ML reaction-prediction endpoints.

    Operations (selected via the fixed `operation` parameter per tool config):
      * predict_reaction       -- forward prediction: reactants -> product
      * predict_retrosynthesis -- retrosynthesis: product -> precursor routes

    The API key is read ONLY from os.environ[RXN4CHEMISTRY_API_KEY]; it is
    never accepted as a parameter. If the key is missing the tool returns a
    structured error rather than raising.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.base_url = os.environ.get(
            "RXN4CHEMISTRY_BASE_URL", DEFAULT_BASE_URL
        ).rstrip("/")
        self.api_url = f"{self.base_url}/rxn/api/api/{API_VERSION}"

    # ------------------------------------------------------------------ #
    # Key / header helpers
    # ------------------------------------------------------------------ #
    def _api_key(self) -> str:
        return os.environ.get(ENV_KEY, "")

    def _headers(self, api_key: str) -> Dict[str, str]:
        return {"Authorization": api_key, "Content-Type": "application/json"}

    @staticmethod
    def _missing_key_error() -> Dict[str, Any]:
        return {
            "status": "error",
            "error": (
                f"IBM RXN for Chemistry requires an API key. Set the "
                f"{ENV_KEY} environment variable. Register for a free key at "
                f"https://rxn.app.accelerate.science (Profile -> My profile -> "
                f"API key)."
            ),
        }

    # ------------------------------------------------------------------ #
    # Dispatch
    # ------------------------------------------------------------------ #
    def run(self, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        arguments = arguments or {}
        operation = arguments.get("operation", "") or self.get_schema_const_operation()

        dispatch = {
            "predict_reaction": self._predict_reaction,
            "predict_retrosynthesis": self._predict_retrosynthesis,
        }
        handler = dispatch.get(operation)
        if handler is None:
            return {
                "status": "error",
                "error": (
                    f"Unknown operation: {operation!r}. "
                    f"Supported: {', '.join(dispatch)}"
                ),
            }

        api_key = self._api_key()
        if not api_key:
            return self._missing_key_error()

        try:
            return handler(arguments, api_key)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"IBM RXN request timed out after {REQUEST_TIMEOUT}s.",
            }
        except requests.exceptions.RequestException as exc:
            return {"status": "error", "error": f"IBM RXN request failed: {exc}"}
        except Exception as exc:  # never raise out of run()
            return {"status": "error", "error": f"Unexpected error: {exc}"}

    # ------------------------------------------------------------------ #
    # Project resolution
    # ------------------------------------------------------------------ #
    def _resolve_project_id(
        self, arguments: Dict[str, Any], headers: Dict[str, str]
    ) -> str:
        """Return a usable project id (explicit arg, first existing, or new)."""
        explicit = arguments.get("project_id")
        if explicit:
            return str(explicit)

        resp = requests.get(
            f"{self.api_url}/projects", headers=headers, timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        payload = resp.json().get("payload", [])
        if isinstance(payload, list) and payload:
            pid = payload[0].get("id") or payload[0].get("_id")
            if pid:
                return str(pid)

        # No project yet -> create one.
        create = requests.post(
            f"{self.api_url}/projects",
            headers=headers,
            json={"name": DEFAULT_PROJECT_NAME},
            timeout=REQUEST_TIMEOUT,
        )
        create.raise_for_status()
        created = create.json().get("payload", {})
        pid = created.get("id") or created.get("_id")
        if not pid:
            raise RuntimeError("Could not resolve or create an IBM RXN project id.")
        return str(pid)

    # ------------------------------------------------------------------ #
    # Async polling helper
    # ------------------------------------------------------------------ #
    def _poll(
        self,
        results_url: str,
        headers: Dict[str, str],
        poll_interval: float,
        max_wait_time: float,
    ) -> Dict[str, Any]:
        """Poll a results URL until status == SUCCESS or budget exhausted.

        Returns the `payload` dict on success. Raises RuntimeError on a
        terminal failure status; raises TimeoutError when the budget runs out.
        """
        deadline = time.time() + max_wait_time
        last_status = "NEW"
        while time.time() < deadline:
            resp = requests.get(results_url, headers=headers, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            payload = resp.json().get("payload", {}) or {}
            last_status = str(payload.get("status", "")).upper()
            if last_status == "SUCCESS":
                return payload
            if last_status in {"ERROR", "FAILED"}:
                raise RuntimeError(
                    f"IBM RXN prediction failed with status {last_status}."
                )
            time.sleep(poll_interval)
        raise TimeoutError(
            f"IBM RXN prediction did not finish within {max_wait_time}s "
            f"(last status: {last_status})."
        )

    @staticmethod
    def _polling_settings(arguments: Dict[str, Any]) -> tuple:
        try:
            poll_interval = float(
                arguments.get("poll_interval") or DEFAULT_POLL_INTERVAL
            )
        except (TypeError, ValueError):
            poll_interval = DEFAULT_POLL_INTERVAL
        try:
            max_wait = float(arguments.get("max_wait_time") or DEFAULT_MAX_WAIT_TIME)
        except (TypeError, ValueError):
            max_wait = DEFAULT_MAX_WAIT_TIME
        return max(1.0, poll_interval), max(1.0, max_wait)

    # ------------------------------------------------------------------ #
    # Operation: forward reaction prediction
    # ------------------------------------------------------------------ #
    def _predict_reaction(
        self, arguments: Dict[str, Any], api_key: str
    ) -> Dict[str, Any]:
        reactants = (arguments.get("reactants") or "").strip()
        if not reactants:
            return {
                "status": "error",
                "error": (
                    "Missing required parameter: reactants (dot-separated SMILES, "
                    "e.g. 'BrBr.c1ccc2cc3ccccc3cc2c1')."
                ),
            }
        ai_model = arguments.get("ai_model") or DEFAULT_AI_MODEL
        headers = self._headers(api_key)
        poll_interval, max_wait = self._polling_settings(arguments)

        project_id = self._resolve_project_id(arguments, headers)
        submit = requests.post(
            f"{self.api_url}/predictions/pr",
            headers=headers,
            params={"projectId": project_id, "aiModel": ai_model},
            json={"reactants": reactants, "aiModel": ai_model},
            timeout=REQUEST_TIMEOUT,
        )
        submit.raise_for_status()
        prediction_id = (submit.json().get("payload", {}) or {}).get("id")
        if not prediction_id:
            return {
                "status": "error",
                "error": "IBM RXN did not return a prediction id for forward prediction.",
            }

        results_url = f"{self.api_url}/predictions/{prediction_id}"
        payload = self._poll(results_url, headers, poll_interval, max_wait)

        attempts = payload.get("attempts") or []
        products: List[Dict[str, Any]] = [
            {
                "smiles": att.get("smiles"),
                "confidence": att.get("confidence"),
            }
            for att in attempts
            if isinstance(att, dict)
        ]
        top = products[0] if products else {}
        return {
            "status": "success",
            "data": {
                "reactants": reactants,
                "product_smiles": top.get("smiles"),
                "confidence": top.get("confidence"),
                "attempts": products,
                "prediction_id": prediction_id,
                "ai_model": ai_model,
            },
        }

    # ------------------------------------------------------------------ #
    # Operation: retrosynthesis
    # ------------------------------------------------------------------ #
    def _predict_retrosynthesis(
        self, arguments: Dict[str, Any], api_key: str
    ) -> Dict[str, Any]:
        product = (arguments.get("product") or "").strip()
        if not product:
            return {
                "status": "error",
                "error": (
                    "Missing required parameter: product (target SMILES, "
                    "e.g. 'CC(=O)Oc1ccccc1C(=O)O' for aspirin)."
                ),
            }
        ai_model = arguments.get("ai_model") or DEFAULT_AI_MODEL
        max_steps = arguments.get("max_steps")
        headers = self._headers(api_key)
        poll_interval, max_wait = self._polling_settings(arguments)

        parameters: Dict[str, Any] = {}
        if max_steps is not None:
            parameters["maxSteps"] = max_steps

        project_id = self._resolve_project_id(arguments, headers)
        body: Dict[str, Any] = {
            "product": product,
            "aiModel": ai_model,
            "isInteractive": False,
        }
        if parameters:
            body["parameters"] = parameters

        submit = requests.post(
            f"{self.api_url}/retrosynthesis/rs",
            headers=headers,
            params={"projectId": project_id, "aiModel": ai_model},
            json=body,
            timeout=REQUEST_TIMEOUT,
        )
        submit.raise_for_status()
        prediction_id = (submit.json().get("payload", {}) or {}).get("id")
        if not prediction_id:
            return {
                "status": "error",
                "error": "IBM RXN did not return a prediction id for retrosynthesis.",
            }

        results_url = f"{self.api_url}/retrosynthesis/{prediction_id}"
        payload = self._poll(results_url, headers, poll_interval, max_wait)

        raw_paths = payload.get("retrosyntheticPaths") or payload.get("paths") or []
        routes: List[Dict[str, Any]] = []
        for path in raw_paths:
            if not isinstance(path, dict):
                continue
            routes.append(
                {
                    "smiles": path.get("smiles"),
                    "confidence": path.get("confidence"),
                    "count": path.get("count"),
                }
            )
        return {
            "status": "success",
            "data": {
                "product": product,
                "routes": routes,
                "route_count": len(routes),
                "prediction_id": prediction_id,
                "ai_model": ai_model,
            },
        }
