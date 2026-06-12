"""DBAASP antimicrobial peptide tools (live REST, keyless).

DBAASP — Database of Antimicrobial Activity and Structure of Peptides
(https://dbaasp.org). Two tools:

- ``DBAASPGetPeptideTool`` (DBAASP_get_peptide): full peptide record by ID.
- ``DBAASPSearchPeptidesTool`` (DBAASP_search_peptides): paginated search/filter.

The public API is keyless, with no login or CAPTCHA. The OpenAPI 3.0 spec is
served at https://dbaasp.org/v3/api-docs. Parameter names are exact (e.g.
``sequence.value`` not ``sequence``) and pagination uses ``limit``/``offset``.
"""

from typing import Any, Dict

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

_BASE_URL = "https://dbaasp.org/peptides"
_TIMEOUT = 30
_HEADERS = {"Accept": "application/json"}


def _err(message: str, **extra: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"status": "error", "error": message}
    out.update(extra)
    return out


@register_tool(
    "DBAASPGetPeptideTool",
    config={
        "name": "DBAASP_get_peptide",
        "type": "DBAASPGetPeptideTool",
        "description": (
            "Get a full DBAASP antimicrobial peptide record by numeric peptide "
            "ID. Returns the sequence, N/C-terminus modifications, structure "
            "(PDB / 3D model), per-target activity measurements (MIC values "
            "with units, medium, CFU), hemolytic/cytotoxic activity, "
            "antibiofilm activity, source genes, UniProt cross-references, "
            "SMILES, and references. Keyless DBAASP v3/v4 API."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "peptideId": {
                    "type": ["integer", "string"],
                    "description": (
                        "DBAASP numeric peptide ID. Example: 107 (Dermaseptin "
                        "S4 (1-16)[M4K], sequence ALWKTLLKKVLKAAAK). Accepts a "
                        "bare integer or a 'DBAASPR_107'-style ID (digits are "
                        "extracted)."
                    ),
                }
            },
            "required": ["peptideId"],
        },
    },
)
class DBAASPGetPeptideTool(BaseTool):
    """Fetch a single DBAASP peptide record by ID."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        raw = arguments.get("peptideId")
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            return _err("peptideId is required")

        # Extract digits to tolerate 'DBAASPR_107' / '107' / 107
        pid = "".join(ch for ch in str(raw) if ch.isdigit())
        if not pid:
            return _err(f"Invalid peptideId: {raw!r} (no numeric ID found)")

        url = f"{_BASE_URL}/{pid}"
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        except requests.exceptions.RequestException as exc:
            return _err(f"Request to DBAASP failed: {exc}", url=url)

        if resp.status_code == 404:
            return _err(f"No DBAASP peptide found with ID {pid}", url=url)
        if resp.status_code != 200:
            return _err(
                f"DBAASP returned HTTP {resp.status_code}",
                url=url,
                response_snippet=(resp.text or "")[:200],
            )

        try:
            data = resp.json()
        except ValueError:
            return _err(
                "DBAASP returned a non-JSON response",
                url=url,
                response_snippet=(resp.text or "")[:200],
            )

        if not isinstance(data, dict) or not data.get("id"):
            return _err(f"No DBAASP peptide record for ID {pid}", url=url)

        target_activities = data.get("targetActivities") or []
        return {
            "status": "success",
            "data": data,
            "metadata": {
                "source": "DBAASP v3/v4 (dbaasp.org)",
                "url": url,
                "peptide_id": data.get("id"),
                "dbaasp_id": data.get("dbaaspId"),
                "name": data.get("name"),
                "sequence": data.get("sequence"),
                "sequence_length": data.get("sequenceLength"),
                "target_activity_count": len(target_activities),
            },
        }


@register_tool(
    "DBAASPSearchPeptidesTool",
    config={
        "name": "DBAASP_search_peptides",
        "type": "DBAASPSearchPeptidesTool",
        "description": (
            "Search/filter DBAASP antimicrobial peptides by sequence "
            "(exact/substring), peptide name, target organism/species, target "
            "group, sequence length, synthesis type, source kingdom, UniProt "
            "xref, or DBAASP ID. Returns a paginated list of matching AMPs "
            "with a total count. Enables sequence->AMP lookup, 'what peptides "
            "are active against organism X', and target-organism activity "
            "surveys. Keyless DBAASP v3/v4 API; pagination is limit/offset."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "sequence": {
                    "type": "string",
                    "description": (
                        "Amino-acid sequence to match (single-letter code). "
                        "Pair with sequence_option ('full' for exact, 'part' "
                        "for substring). Example: 'GLFDIVKKVVGALGSL'."
                    ),
                },
                "sequence_option": {
                    "type": "string",
                    "description": (
                        "How to match 'sequence': 'full' (exact, default) or "
                        "'part' (substring). Maps to DBAASP sequence.option."
                    ),
                },
                "name": {
                    "type": "string",
                    "description": "Peptide name substring. Example: 'Magainin'.",
                },
                "target_species": {
                    "type": "string",
                    "description": (
                        "Target organism / species name. Example: "
                        "'Staphylococcus aureus'. Maps to targetSpecies.value."
                    ),
                },
                "target_group": {
                    "type": "string",
                    "description": (
                        "Target group (e.g. 'Gram+', 'Gram-'). Maps to "
                        "targetGroup.value."
                    ),
                },
                "sequence_length": {
                    "type": ["integer", "string"],
                    "description": (
                        "Exact peptide length filter. Maps to sequenceLength.value."
                    ),
                },
                "synthesis_type": {
                    "type": "string",
                    "description": (
                        "Synthesis type, e.g. 'Ribosomal', 'Synthetic'. Maps "
                        "to synthesisType.value."
                    ),
                },
                "kingdom": {
                    "type": "string",
                    "description": (
                        "Source kingdom/taxonomy filter. Maps to kingdom.value."
                    ),
                },
                "uniprot": {
                    "type": "string",
                    "description": (
                        "UniProt accession cross-reference. Maps to uniprot.value."
                    ),
                },
                "dbaasp_id": {
                    "type": ["integer", "string"],
                    "description": "DBAASP numeric ID filter. Maps to id.value.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return (default 25).",
                },
                "offset": {
                    "type": "integer",
                    "description": "Result offset for pagination (default 0).",
                },
            },
            "required": [],
        },
    },
)
class DBAASPSearchPeptidesTool(BaseTool):
    """Search / filter DBAASP peptides; returns paginated list + total count."""

    # user-arg -> DBAASP API query parameter. "sequence_option" only refines a
    # sequence match, so it is excluded from the substantive-filter check below.
    _PARAM_MAP = {
        "sequence": "sequence.value",
        "sequence_option": "sequence.option",
        "name": "name.value",
        "target_species": "targetSpecies.value",
        "target_group": "targetGroup.value",
        "sequence_length": "sequenceLength.value",
        "synthesis_type": "synthesisType.value",
        "kingdom": "kingdom.value",
        "uniprot": "uniprot.value",
        "dbaasp_id": "id.value",
    }
    _FILTER_KEYS = tuple(k for k in _PARAM_MAP if k != "sequence_option")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        arguments = arguments or {}

        def _provided(key: str) -> bool:
            val = arguments.get(key)
            return val is not None and str(val).strip() != ""

        params: Dict[str, Any] = {}
        for arg_key, api_key in self._PARAM_MAP.items():
            if _provided(arg_key):
                params[api_key] = arguments[arg_key]

        # Require at least one substantive filter (not just sequence_option).
        if not any(_provided(k) for k in self._FILTER_KEYS):
            return _err(
                "At least one search filter is required (e.g. sequence, name, "
                "target_species, target_group, sequence_length, synthesis_type, "
                "kingdom, uniprot, or dbaasp_id)."
            )

        # Default the sequence match option when a sequence is given.
        if arguments.get("sequence") and "sequence.option" not in params:
            params["sequence.option"] = "full"

        def _as_int(value: Any, default: int) -> int:
            try:
                return int(value)
            except (TypeError, ValueError):
                return default

        params["limit"] = _as_int(arguments.get("limit", 25), 25)
        params["offset"] = _as_int(arguments.get("offset", 0), 0)

        try:
            resp = requests.get(
                _BASE_URL, params=params, headers=_HEADERS, timeout=_TIMEOUT
            )
        except requests.exceptions.RequestException as exc:
            return _err(f"Request to DBAASP failed: {exc}")

        if resp.status_code != 200:
            return _err(
                f"DBAASP returned HTTP {resp.status_code}",
                url=resp.url,
                response_snippet=(resp.text or "")[:200],
            )

        try:
            payload = resp.json()
        except ValueError:
            return _err(
                "DBAASP returned a non-JSON response",
                url=resp.url,
                response_snippet=(resp.text or "")[:200],
            )

        if not isinstance(payload, dict):
            return _err("Unexpected DBAASP response shape", url=resp.url)

        results = payload.get("data") or []
        total = payload.get("totalCount", 0)
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "DBAASP v3/v4 (dbaasp.org)",
                "url": resp.url,
                "total_count": total,
                "returned_count": len(results),
                "limit": params["limit"],
                "offset": params["offset"],
            },
        }
