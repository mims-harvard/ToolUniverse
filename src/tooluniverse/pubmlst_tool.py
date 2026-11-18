# pubmlst_tool.py
"""
PubMLST REST API tools for ToolUniverse.

PubMLST (University of Oxford) hosts the reference allele and sequence-type
(ST) definitions for multilocus sequence typing (MLST), core-genome MLST and
other schemes, for more than 100 bacterial and eukaryotic genera. Public
health labs use it to name the strain type of an isolate (for example
Neisseria meningitidis ST-11, the hypervirulent ST-11 clonal complex).

ToolUniverse had no MLST typing source. These tools list the databases and
schemes, read the alleles of a sequence type, and type a sequence (one
locus or a whole assembly) against a scheme.

API: https://rest.pubmlst.org (BIGSdb REST interface).
No authentication is needed for the routes used here. Without a login,
PubMLST serves only data submitted on or before a cutoff date (2024-12-31 on
2026-11-18). When PubMLST sends that notice, the tools pass it on in
``metadata.access_note``.
"""

from typing import Any, Dict, List, Optional

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

PUBMLST_BASE_URL = "https://rest.pubmlst.org"

# Profile keys that are links to curator records, not typing data.
_PROFILE_SKIP = {"alleles", "curator", "sender"}
# Partial-match keys worth returning. The full allele and flanking sequence
# are left out: for a whole assembly they make the answer megabytes long.
_PARTIAL_KEEP = (
    "allele",
    "identity",
    "length",
    "alignment",
    "mismatches",
    "gaps",
    "contig",
    "start",
    "end",
    "predicted_start",
    "predicted_end",
    "reverse",
)


def _last(url: Any) -> str:
    """The last path segment of a PubMLST link ('.../loci/abcZ' -> 'abcZ')."""
    return str(url).rstrip("/").rsplit("/", 1)[-1]


def _locus_and_allele(url: str) -> Optional[tuple]:
    """('abcZ', '2') from '.../loci/abcZ/alleles/2'; None for other links."""
    parts = str(url).rstrip("/").split("/")
    if len(parts) >= 4 and parts[-2] == "alleles" and parts[-4] == "loci":
        return parts[-3], parts[-1]
    return None


class _PubMLSTError(Exception):
    """A PubMLST answer that the tool reports as an error."""


@register_tool("PubMLSTTool")
class PubMLSTTool(BaseTool):
    """
    Query PubMLST typing schemes and sequence-type definitions.

    Operations (``fields.operation`` in the tool config):

    - ``list_databases``: the organisms and their database names.
    - ``list_schemes``: the typing schemes of one database.
    - ``get_profile``: the alleles and clonal complex of one sequence type.
    - ``type_sequence``: allele numbers and sequence type of a DNA sequence.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "list_databases"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Run the configured PubMLST operation."""
        arguments = arguments or {}
        operations = {
            "list_databases": self._list_databases,
            "list_schemes": self._list_schemes,
            "get_profile": self._get_profile,
            "type_sequence": self._type_sequence,
        }
        handler = operations.get(self.operation)
        if handler is None:
            return {"status": "error", "error": f"Unknown operation: {self.operation}"}
        try:
            return handler(arguments)
        except _PubMLSTError as e:
            return {"status": "error", "error": str(e)}
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"PubMLST request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to PubMLST. Check network.",
            }
        except ValueError:
            return {"status": "error", "error": "PubMLST returned a non-JSON response"}
        except Exception as e:  # never raise out of run()
            return {"status": "error", "error": f"Error querying PubMLST: {e}"}

    # -- HTTP -------------------------------------------------------------

    def _request(self, method: str, path: str, body: Optional[dict] = None) -> Any:
        """GET or POST a PubMLST path; raise _PubMLSTError with its message."""
        url = f"{PUBMLST_BASE_URL}/{path.lstrip('/')}"
        if method == "POST":
            response = requests.post(url, json=body, timeout=self.timeout)
        else:
            response = requests.get(url, timeout=self.timeout)
        if response.status_code >= 400:
            message = None
            try:
                payload = response.json()
                if isinstance(payload, dict):
                    message = payload.get("message")
            except ValueError:
                pass
            raise _PubMLSTError(
                f"PubMLST returned HTTP {response.status_code}"
                + (f": {message}" if message else "")
            )
        return response.json()

    @staticmethod
    def _metadata(payload: Any, **extra: Any) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {"source": "PubMLST (rest.pubmlst.org)"}
        if isinstance(payload, dict) and payload.get("message"):
            # e.g. "you are currently restricted to accessing data that was
            # submitted on or prior to 2024-12-31"
            metadata["access_note"] = payload["message"]
        metadata.update({k: v for k, v in extra.items() if v is not None})
        return metadata

    def _resolve_database(self, arguments: Dict[str, Any]) -> str:
        """A seqdef database name from 'pubmlst_neisseria_seqdef' or 'neisseria'."""
        database = str(arguments.get("database") or "").strip()
        if not database:
            raise _PubMLSTError(
                "database is required, e.g. 'pubmlst_neisseria_seqdef' or the "
                "organism group 'neisseria'. PubMLST_list_databases lists them."
            )
        if database.startswith("pubmlst_") or "_seqdef" in database:
            return database
        groups = self._request("GET", "db")
        for group in groups if isinstance(groups, list) else []:
            if str(group.get("name", "")).lower() != database.lower():
                continue
            for db in group.get("databases") or []:
                if str(db.get("name", "")).endswith("_seqdef"):
                    return db["name"]
        raise _PubMLSTError(
            f"No PubMLST sequence-definition database for '{database}'. "
            "Use PubMLST_list_databases to find the database name."
        )

    @staticmethod
    def _scheme_id(arguments: Dict[str, Any]) -> int:
        try:
            return int(arguments.get("scheme_id") or 1)
        except (TypeError, ValueError):
            raise _PubMLSTError("scheme_id must be an integer, e.g. 1 for MLST")

    # -- operations -------------------------------------------------------

    def _list_databases(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Organism groups with their sequence-definition and isolate databases."""
        groups = self._request("GET", "db")
        if not isinstance(groups, list):
            raise _PubMLSTError("PubMLST returned an unexpected database list")
        query = str(arguments.get("query") or "").strip().lower()
        rows: List[Dict[str, Any]] = []
        for group in groups:
            databases = group.get("databases") or []
            text = " ".join(
                [str(group.get("name", "")), str(group.get("description", ""))]
                + [str(db.get("description", "")) for db in databases]
            ).lower()
            if query and query not in text:
                continue
            names = [str(db.get("name", "")) for db in databases]
            seqdef = [n for n in names if n.endswith("_seqdef")]
            isolates = [n for n in names if n.endswith("_isolates")]
            rows.append(
                {
                    "group": group.get("name"),
                    "description": group.get("description"),
                    # e.g. "Authenticated access only" for rMLST
                    "long_description": group.get("long_description"),
                    "seqdef_database": seqdef[0] if seqdef else None,
                    "isolates_database": isolates[0] if isolates else None,
                    "databases": [
                        {"name": db.get("name"), "description": db.get("description")}
                        for db in databases
                    ],
                }
            )
        return {
            "status": "success",
            "data": rows,
            "metadata": self._metadata(
                groups,
                total_groups=len(groups),
                returned=len(rows),
                query=query or None,
                note="Pass seqdef_database to PubMLST_list_schemes.",
            ),
        }

    def _list_schemes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Typing schemes of one sequence-definition database."""
        database = self._resolve_database(arguments)
        payload = self._request("GET", f"db/{database}/schemes")
        schemes = payload.get("schemes") if isinstance(payload, dict) else None
        if not isinstance(schemes, list):
            raise _PubMLSTError(f"PubMLST returned no scheme list for {database}")
        query = str(arguments.get("query") or "").strip().lower()
        rows = [
            {
                "scheme_id": int(_last(s.get("scheme"))),
                "description": s.get("description"),
            }
            for s in schemes
            if not query or query in str(s.get("description", "")).lower()
        ]
        return {
            "status": "success",
            "data": rows,
            "metadata": self._metadata(
                payload,
                database=database,
                total_schemes=payload.get("records", len(schemes)),
                returned=len(rows),
                note="Scheme 1 is usually the 7-locus MLST scheme. Pass scheme_id "
                "to PubMLST_get_profile or PubMLST_type_sequence.",
            ),
        }

    def _get_profile(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Alleles and scheme fields (e.g. clonal complex) of one sequence type."""
        database = self._resolve_database(arguments)
        scheme_id = self._scheme_id(arguments)
        st = str(arguments.get("st") or "").strip()
        if st.upper().startswith("ST"):
            st = st[2:].lstrip("-")
        if not st:
            raise _PubMLSTError("st is required, e.g. 11 for ST-11")
        try:
            payload = self._request(
                "GET", f"db/{database}/schemes/{scheme_id}/profiles/{st}"
            )
        except _PubMLSTError as e:
            if "HTTP 404" in str(e) and "Profile" in str(e):
                raise _PubMLSTError(
                    f"{e}. Without a PubMLST login, sequence types submitted "
                    "after the public cutoff date are not served either."
                )
            raise
        if not isinstance(payload, dict):
            raise _PubMLSTError("PubMLST returned an unexpected profile")
        alleles: Dict[str, str] = {}
        for link in payload.get("alleles") or []:
            pair = _locus_and_allele(link)
            if pair:
                alleles[pair[0]] = pair[1]
        data = {k: v for k, v in payload.items() if k not in _PROFILE_SKIP}
        data["alleles"] = alleles
        return {
            "status": "success",
            "data": data,
            "metadata": self._metadata(
                payload,
                database=database,
                scheme_id=scheme_id,
                locus_count=len(alleles),
            ),
        }

    def _type_sequence(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Exact allele matches and the sequence type of a DNA sequence."""
        database = self._resolve_database(arguments)
        scheme_id = self._scheme_id(arguments)
        sequence = str(arguments.get("sequence") or "").strip()
        if not sequence:
            raise _PubMLSTError(
                "sequence is required: DNA of one locus, or a FASTA of contigs"
            )
        partial = bool(arguments.get("partial_matches"))
        body: Dict[str, Any] = {"sequence": sequence}
        if partial:
            body["partial_matches"] = 1
        payload = self._request(
            "POST", f"db/{database}/schemes/{scheme_id}/sequence", body
        )
        if not isinstance(payload, dict):
            raise _PubMLSTError("PubMLST returned an unexpected typing result")

        exact: Dict[str, List[str]] = {}
        for locus, matches in (payload.get("exact_matches") or {}).items():
            exact[locus] = [str(m.get("allele_id")) for m in matches or []]

        partial_rows: Dict[str, Dict[str, Any]] = {}
        for locus, match in (payload.get("partial_matches") or {}).items():
            # PubMLST lists every locus; loci with no hit come back as {}.
            if isinstance(match, dict) and match:
                partial_rows[locus] = {k: match[k] for k in _PARTIAL_KEEP if k in match}

        fields = payload.get("fields") or {}
        if fields:
            note = "A sequence type was assigned from the exact allele matches."
        elif exact or partial_rows:
            note = (
                "No sequence type assigned: not every locus of the scheme matched "
                "a known allele exactly, or the allele combination is not defined."
            )
        else:
            note = "No locus of this scheme matched the sequence."
            if not partial:
                note += " Set partial_matches=true to see the closest alleles."
        data: Dict[str, Any] = {
            "exact_matches": exact,
            "fields": fields,
        }
        if partial:
            data["partial_matches"] = partial_rows
        return {
            "status": "success",
            "data": data,
            "metadata": self._metadata(
                payload,
                database=database,
                scheme_id=scheme_id,
                loci_matched=len(exact),
                note=note,
            ),
        }
