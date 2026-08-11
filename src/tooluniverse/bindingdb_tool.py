"""
BindingDB Tool - Query protein-ligand binding affinity data.

BindingDB contains 3.2M data points for 1.4M compounds and 11.4K targets.
Provides binding affinities (Ki, IC50, Kd) for drug discovery research.

NOTE: BindingDB's singular-form ``getLigandsByUniprot`` endpoint hangs
indefinitely (a 60 s request times out). Its plural sibling
``getLigandsByUniprots`` responds normally (~100 ms) and accepts either a
single id or a comma-delimited list, so we route both the single-id and
multi-id operations through the plural endpoint.

Parameter names follow BindingDB's published REST spec
(https://bindingdb.org/rwd/bind/BindingDBRESTfulAPI.jsp), which documents
the *singular* query-parameter names even on the plural endpoints:

    getLigandsByUniprots?uniprot={UNIPROTs}&cutoff={affinity_cutoff}
    getLigandsByPDBs?pdb={PDBs}&cutoff={affinity_cutoff}&identity={identity}

Multiple ids are joined with a comma; the spec states UniProt identifiers are
"separated by comma". Sending the plural spellings (``uniprots=``/``pdbs=``)
does not error usefully -- ``uniprots=`` returns HTTP 200 with an empty
affinities list and ``pdbs=`` returns HTTP 500 -- so the names below are
load-bearing and are pinned by tests in
``tests/unit/test_bindingdb_cutoff_param_names.py``.
"""

import re
from typing import Any, Dict, List

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool


BASE_URL = "https://www.bindingdb.org/rest"
DEFAULT_TIMEOUT = 30


def _error_detail(resp: "requests.Response") -> str:
    """Readable one-line summary of an error response body.

    BindingDB serves Tomcat's HTML error page on failures, and echoing its
    first 200 characters put a doctype and a stylesheet fragment in front of
    the caller instead of anything diagnostic.
    """
    body = (resp.text or "").strip()
    if "<html" in body[:200].lower() or body[:20].lower().startswith("<!doctype"):
        title = re.search(r"<title>(.*?)</title>", body, re.IGNORECASE | re.DOTALL)
        summary = title.group(1).strip() if title else "HTML error page"
        return f"upstream returned an HTML error page ({summary})"
    return body[:200] or "empty response body"


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
        return {"_err": f"BindingDB HTTP {resp.status_code}: {_error_detail(resp)}"}
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


_BDB_PREFIX = "bdb."


def _strip_bdb_prefix(obj: Any) -> Any:
    """Drop BindingDB's ``bdb.`` key prefix.

    ``getTargetByCompound`` returns its payload with every key namespaced --
    ``bdb.affinities``, ``bdb.monomerid``, ``bdb.target``, ``bdb.species`` --
    while the uniprot/pdb endpoints return the same fields unprefixed. Callers
    should not have to care which endpoint produced a record, so normalise to
    the unprefixed spelling. Note this keeps fields the other endpoints do not
    supply (notably ``species``, which is scientifically load-bearing: hits are
    frequently non-human orthologs).
    """
    if isinstance(obj, dict):
        return {
            (
                k[len(_BDB_PREFIX) :]
                if isinstance(k, str) and k.startswith(_BDB_PREFIX)
                else k
            ): _strip_bdb_prefix(v)
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_strip_bdb_prefix(v) for v in obj]
    return obj


def _affinities(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Pull the affinities list out of any BindingDB *Response envelope."""
    key = _envelope_response_key(payload)
    body = payload.get(key, {}) if key else payload
    body = _strip_bdb_prefix(body)
    if not isinstance(body, dict):
        return []
    aff = body.get("affinities") or body.get("ligands") or []
    return aff if isinstance(aff, list) else [aff]


_EMPTY_NOTE = (
    "BindingDB returned no matching records for this query. Per BindingDB's "
    "REST spec an unmatched identifier yields an empty result, so this is a "
    "genuine no-data answer rather than a rejected request; widen the affinity "
    "cutoff or check the identifier if records were expected."
)


_SIMILARITY_IGNORED_NOTE = (
    "BindingDB's getTargetByCompound endpoint does not apply a similarity "
    "threshold: probing four chemically diverse compounds with values from 0.4 "
    "to 1.0 -- and with the parameter omitted -- returned byte-identical result "
    "sets. The `similarity` field above only echoes the value you supplied; it "
    "did not narrow these results, so do not treat them as filtered."
)


def _split_ids(raw: Any) -> List[str]:
    """Normalise a caller-supplied id list to a list of bare ids.

    Accepts a list or a delimited string. Semicolons are accepted on input
    because BindingDB's own docs use ``;`` for the singular endpoint and older
    callers copied that spelling, but the wire format is always comma-joined --
    a semicolon-joined list is accepted upstream with HTTP 200 and matches
    nothing.
    """
    if isinstance(raw, str):
        raw = re.split(r"[,;]", raw)
    if not isinstance(raw, list):
        return []
    return [str(s).strip() for s in raw if str(s).strip()]


def _add_note(data: Dict[str, Any], note: str) -> Dict[str, Any]:
    """Attach a caller-facing note, appending to any note already present.

    Several disclosures can apply to the same payload (an empty result set that
    also came back from an endpoint that ignores its filter), so notes are
    joined rather than overwriting one another.
    """
    existing = data.get("note")
    data["note"] = f"{existing} {note}" if existing else note
    return data


def _with_empty_note(data: Dict[str, Any]) -> Dict[str, Any]:
    """Mark a successful-but-empty result so it reads as 'no data', not 'no query'."""
    if not data.get("affinities"):
        _add_note(data, _EMPTY_NOTE)
    return data


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
            ids = _split_ids(arguments.get("uniprots") or arguments.get("uniprot_ids"))
        else:
            single = arguments.get("uniprot") or arguments.get("uniprot_id") or ""
            ids = [single.strip()] if single.strip() else []
        if not ids:
            return {"status": "error", "error": "Provide uniprot accession(s)."}
        # Schema declares this param as `affinity_cutoff`; the legacy `cutoff`
        # name is kept as a fallback (the internal search_by_target caller and
        # any older callers pass `cutoff`). Reading only `cutoff` silently
        # ignored a user-supplied `affinity_cutoff` and always used the 10000 nM
        # default -- confirmed live: passing affinity_cutoff=1 echoed cutoff=10000.
        cutoff = int(arguments.get("affinity_cutoff", arguments.get("cutoff", 10000)))
        # Parameter is `uniprot` (singular) even on the plural endpoint, and ids
        # are comma-joined -- both per BindingDB's REST spec. The plural spelling
        # `uniprots=` is silently ignored upstream: HTTP 200 with zero affinities
        # for a target that has thousands.
        result = _http_get(
            "getLigandsByUniprots",
            {
                "uniprot": ",".join(ids),
                "cutoff": cutoff,
                "response": "application/json",
            },
            timeout=self.timeout,
        )
        if "_err" in result:
            return {"status": "error", "error": result["_err"]}
        return {
            "status": "success",
            "data": _with_empty_note(
                {
                    "uniprots": ids,
                    "cutoff": cutoff,
                    "affinities": _affinities(result),
                }
            ),
            "metadata": {"source": "BindingDB REST"},
        }

    def _get_ligands_by_pdbs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        ids = _split_ids(arguments.get("pdbs") or arguments.get("pdb_ids"))
        if not ids:
            return {"status": "error", "error": "Provide pdb id(s)."}
        # Schema declares this param as `affinity_cutoff` (see uniprot handler).
        cutoff = int(arguments.get("affinity_cutoff", arguments.get("cutoff", 10000)))
        # Spec: `identity` is a sequence-identity cutoff in percent. The schema
        # already declares it as `sequence_identity` with a default of 100, which
        # matches what the endpoint does when the parameter is omitted, so wire
        # the declared knob through instead of dropping it.
        identity = int(
            arguments.get("sequence_identity", arguments.get("identity", 100))
        )
        # Parameter is `pdb` (singular) even on the plural endpoint, and ids are
        # comma-joined -- both per BindingDB's REST spec. The plural spelling
        # `pdbs=` makes the endpoint answer HTTP 500.
        result = _http_get(
            "getLigandsByPDBs",
            {
                "pdb": ",".join(ids),
                "cutoff": cutoff,
                "identity": identity,
                "response": "application/json",
            },
            timeout=self.timeout,
        )
        if "_err" in result:
            return {"status": "error", "error": result["_err"]}
        return {
            "status": "success",
            "data": _with_empty_note(
                {
                    "pdbs": ids,
                    "cutoff": cutoff,
                    "sequence_identity": identity,
                    "affinities": _affinities(result),
                }
            ),
            "metadata": {"source": "BindingDB REST"},
        }

    def _get_target_by_compound(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        # BindingDB exposes getTargetByCompound; it accepts SMILES + similarity cutoff.
        smiles = arguments.get("smiles") or arguments.get("compound_smiles") or ""
        if not smiles:
            return {"status": "error", "error": "Provide a SMILES string."}
        # Schema declares this param as `similarity_cutoff`; `similarity` is a
        # legacy fallback. Reading only `similarity` silently ignored a
        # user-supplied `similarity_cutoff` and always used the 0.85 default.
        similarity = float(
            arguments.get("similarity_cutoff", arguments.get("similarity", 0.85))
        )
        # The spec names this endpoint's threshold `cutoff` rather than
        # `similarity`, but the endpoint ignores it under either spelling and at
        # every value tested (0.4 through 1.0 all return the same hits, as does
        # omitting it entirely), so the name here is not load-bearing and is left
        # as-is. Unlike the uniprot/pdb parameters below, renaming it would
        # change no observable behaviour. The value is still forwarded for
        # forward compatibility, and _SIMILARITY_IGNORED_NOTE tells the caller
        # not to read the echoed `similarity` as evidence of filtering.
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
            "data": _add_note(
                _with_empty_note(
                    {
                        "smiles": smiles,
                        "similarity": similarity,
                        "affinities": _affinities(result),
                    }
                ),
                _SIMILARITY_IGNORED_NOTE,
            ),
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
