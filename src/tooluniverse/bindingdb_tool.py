"""
BindingDB Tool - Query protein-ligand binding affinity data.

BindingDB contains 3.2M data points for 1.4M compounds and 11.4K targets.
Provides binding affinities (Ki, IC50, Kd) for drug discovery research.

NOTE: BindingDB's singular-form REST endpoints (``getLigandsByUniprot``,
``getLigandsByPDB``, ``getTargetByCompound``) hang indefinitely as of
2026. The plural-form siblings (``getLigandsByUniprots``,
``getLigandsByPDBs``) respond normally (~100 ms) and accept either a
single id or a semicolon-delimited list — so we route every operation
through the plural endpoint.
"""

from typing import Any, Dict, List

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool


BASE_URL = "https://www.bindingdb.org/rest"
DEFAULT_TIMEOUT = 30


def _http_get(
    path: str, params: Dict[str, Any], timeout: int = DEFAULT_TIMEOUT
) -> Dict[str, Any]:
    """Common GET wrapper with JSON parse + clear error envelope."""
    try:
        resp = requests.get(
            f"{BASE_URL}/{path}",
            params=params,
            headers={
                "User-Agent": "ToolUniverse/BindingDB",
                "Accept": "application/json",
            },
            timeout=timeout,
        )
    except requests.exceptions.Timeout:
        return {
            "_err": f"BindingDB request timed out after {timeout}s (try a shorter request)"
        }
    except requests.exceptions.ConnectionError as e:
        return {"_err": f"BindingDB connection failed: {e}"}
    if resp.status_code != 200:
        return {"_err": f"BindingDB HTTP {resp.status_code}: {resp.text[:200]}"}
    try:
        return resp.json()
    except ValueError as e:
        return {"_err": f"BindingDB returned non-JSON response: {e}"}


def _envelope_response_key(payload: Dict[str, Any]) -> str:
    """BindingDB wraps each endpoint's response in a *Response key whose
    name matches the endpoint. Find it dynamically so callers don't have
    to track the camelCase casing."""
    for k in payload:
        if isinstance(k, str) and k.endswith("Response"):
            return k
    return ""


def _affinities(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Pull the affinities list out of any BindingDB *Response envelope."""
    key = _envelope_response_key(payload)
    body = payload.get(key, {}) if key else payload
    aff = body.get("affinities") or body.get("ligands") or []
    return aff if isinstance(aff, list) else [aff]


@register_tool("BindingDBTool")
class BindingDBTool(BaseTool):
    """Tool for querying BindingDB binding affinity database."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        self.operation = tool_config.get("fields", {}).get(
            "operation", "get_ligands_by_uniprot"
        )
        self.timeout = int(tool_config.get("timeout", DEFAULT_TIMEOUT))

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if self.operation in ("get_ligands_by_uniprot",):
                return self._get_ligands_by_uniprots(arguments, plural=False)
            if self.operation in ("get_ligands_by_uniprots",):
                return self._get_ligands_by_uniprots(arguments, plural=True)
            if self.operation in ("get_ligands_by_pdbs", "get_ligands_by_pdb"):
                return self._get_ligands_by_pdbs(arguments)
            if self.operation in ("get_target_by_compound", "get_targets_by_compound"):
                return self._get_target_by_compound(arguments)
            if self.operation in ("search_by_target",):
                return self._search_by_target(arguments)
            return {"status": "error", "error": f"Unknown operation: {self.operation}"}
        except Exception as e:  # noqa: BLE001
            return {"status": "error", "error": f"BindingDB tool error: {e}"}

    def _get_ligands_by_uniprots(
        self, arguments: Dict[str, Any], plural: bool
    ) -> Dict[str, Any]:
        """Singular and plural callers funnel into the same plural endpoint —
        the singular ``getLigandsByUniprot`` hangs upstream."""
        if plural:
            ids = arguments.get("uniprots") or arguments.get("uniprot_ids") or []
            if isinstance(ids, str):
                ids = [s.strip() for s in ids.split(",") if s.strip()]
        else:
            single = arguments.get("uniprot") or arguments.get("uniprot_id") or ""
            ids = [single] if single else []
        if not ids:
            return {"status": "error", "error": "Provide uniprot accession(s)."}
        cutoff = int(arguments.get("cutoff", 10000))
        result = _http_get(
            "getLigandsByUniprots",
            {
                "uniprots": ";".join(ids),
                "cutoff": cutoff,
                "response": "application/json",
            },
            timeout=self.timeout,
        )
        if "_err" in result:
            return {"status": "error", "error": result["_err"]}
        return {
            "status": "success",
            "data": {
                "uniprots": ids,
                "cutoff": cutoff,
                "affinities": _affinities(result),
            },
            "metadata": {"source": "BindingDB REST"},
        }

    def _get_ligands_by_pdbs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        ids = arguments.get("pdbs") or arguments.get("pdb_ids") or []
        if isinstance(ids, str):
            ids = [s.strip() for s in ids.split(",") if s.strip()]
        if not ids:
            return {"status": "error", "error": "Provide pdb id(s)."}
        cutoff = int(arguments.get("cutoff", 10000))
        result = _http_get(
            "getLigandsByPDBs",
            {"pdbs": ";".join(ids), "cutoff": cutoff, "response": "application/json"},
            timeout=self.timeout,
        )
        if "_err" in result:
            return {"status": "error", "error": result["_err"]}
        return {
            "status": "success",
            "data": {"pdbs": ids, "cutoff": cutoff, "affinities": _affinities(result)},
            "metadata": {"source": "BindingDB REST"},
        }

    def _get_target_by_compound(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        # BindingDB exposes getTargetByCompound; it accepts SMILES + similarity cutoff.
        smiles = arguments.get("smiles") or arguments.get("compound_smiles") or ""
        if not smiles:
            return {"status": "error", "error": "Provide a SMILES string."}
        similarity = float(arguments.get("similarity", 0.85))
        result = _http_get(
            "getTargetByCompound",
            {
                "smiles": smiles,
                "similarity": similarity,
                "response": "application/json",
            },
            timeout=self.timeout,
        )
        if "_err" in result:
            return {"status": "error", "error": result["_err"]}
        return {
            "status": "success",
            "data": {
                "smiles": smiles,
                "similarity": similarity,
                "affinities": _affinities(result),
            },
            "metadata": {"source": "BindingDB REST"},
        }

    def _search_by_target(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Convenience: search-by-target dispatches to the plural-uniprot path
        when the caller passes a UniProt accession, otherwise returns a
        descriptive error pointing at the right alternative."""
        target = (
            arguments.get("query")
            or arguments.get("target")
            or arguments.get("target_name")
            or ""
        )
        # If it looks like a UniProt accession, route to plural endpoint.
        if target and len(target) <= 12 and target[0].isalpha() and target[1].isdigit():
            return self._get_ligands_by_uniprots(
                {"uniprots": [target], "cutoff": arguments.get("cutoff", 10000)},
                plural=True,
            )
        return {
            "status": "error",
            "error": (
                "BindingDB search-by-target requires a UniProt accession "
                "(e.g. 'P00533'). For free-text target name search, use "
                "ChEMBL_search_target or PubChem BioAssay."
            ),
        }
