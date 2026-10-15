# stitch_tool.py
"""
STITCH (Search Tool for Interacting Chemicals) API tool for ToolUniverse.

STITCH is a database of known and predicted interactions between
chemicals and proteins, combining data from various sources.

API Documentation: https://stitch-db.org/
"""

import re
from typing import Any, Dict, List

import requests
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URL for STITCH REST API (chemical-protein interactions).
# Fix-R19E-3/R28: STITCH and STRING are separate sister databases sharing
# the same API software, NOT the same database -- confirmed live that
# string-db.org genuinely doesn't recognize chemical identifiers (its own
# /resolve fuzzy-matched "aspirin" to an unrelated protein, SLC17A4, and
# /interaction_partners rejected the real STITCH chemical id
# "-1.CID100002244" as "not found"), so pointing STITCH queries at
# string-db.org was silently returning wrong, mislabeled protein-protein
# data as chemical-protein interactions. stitch.embl.de now redirects to
# stitch-db.org (the correct current STITCH host per the shared API docs'
# own "List of databases" table); use that instead. Note: the
# network/interactions sub-endpoints still 404 on the new domain even with
# a correctly-resolved identifier (confirmed live). The same API still serves
# them in its older formats, though -- psi-mi-tab/interactionsList for the
# network and tsv-no-header/interactors for the ranked partners (confirmed
# live 2026-10-05) -- so the two tools read those instead.
STITCH_BASE_URL = "https://stitch-db.org/api"


def _stitch_identifier(identifier: str) -> str:
    """An identifier in a form the interaction endpoints accept.

    STITCH's own ids do not round-trip: resolve returns "-1.CID100002244",
    and interactionsList finds nothing for it, nor for "CIDm00002244" or
    "CIDs00002244" -- the forms its documentation and this tool's own
    examples used. The flat/stereo letters map to the digit the network uses
    (m -> 1, s -> 0), and the leading "<taxon>." is dropped (confirmed live).
    The old rewrite, CID000002244 -> CIDm00002244, turned an id that worked
    into one that returns nothing.
    """
    value = str(identifier).strip()
    value = re.sub(r"^-\d+\.(?=CID)", "", value, flags=re.IGNORECASE)
    match = re.match(r"^CID([ms])0*(\d+)$", value, re.IGNORECASE)
    if match:
        digit = "1" if match.group(1).lower() == "m" else "0"
        return f"CID{digit}{int(match.group(2)):08d}"
    return value


def _parse_psi_mi_tab(text: str) -> List[Dict[str, Any]]:
    """PSI-MI-TAB rows as the STRING-style JSON objects the schema declares.

    Columns 1-2 are "string:<id>", 3-4 the preferred names and 15 the scores,
    "score:0.999|escore:0.725|dscore:0.9|tscore:0.986".
    """
    rows = []
    for line in text.splitlines():
        cols = line.split("\t")
        if len(cols) < 15:
            continue
        scores = {}
        for part in cols[14].split("|"):
            key, _, value = part.partition(":")
            try:
                scores[key] = float(value)
            except ValueError:
                continue
        row = {
            "stringId_A": cols[0].split(":", 1)[-1],
            "stringId_B": cols[1].split(":", 1)[-1],
            "preferredName_A": cols[2],
            "preferredName_B": cols[3],
            "score": scores.pop("score", None),
        }
        row.update(scores)
        rows.append(row)
    return rows


def _endpoint_unavailable_error(endpoint_path: str, identifiers: Any) -> Dict[str, Any]:
    """Fix-R19E-3: STITCH's /json interaction sub-endpoints 404 on the
    migrated stitch-db.org site even for a correctly-resolved identifier
    (confirmed live) -- the endpoint path itself appears unavailable, not a
    bad identifier. Return an error saying so honestly instead of implying
    the identifier format is the problem."""
    return {
        "status": "error",
        "error": (
            f"STITCH's {endpoint_path} endpoint returned 404 for "
            f"{identifiers}. This endpoint appears unavailable on "
            "STITCH's current site (stitch-db.org) even for a "
            "correctly-resolved identifier -- not necessarily a bad "
            "identifier. Use STITCH_resolve_identifier to confirm the "
            "identifier resolves, or browse interactions directly at "
            "https://stitch-db.org/."
        ),
    }


@register_tool("STITCHTool")
class STITCHTool(BaseTool):
    """
    Tool for querying STITCH database.

    STITCH provides chemical-protein interaction data including:
    - Known drug-target interactions
    - Predicted chemical-protein interactions
    - Interaction scores and evidence
    - Network analysis data

    No authentication required. Free for academic/research use.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "get_interactions"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the STITCH API call."""
        operation = self.operation

        if operation == "get_interactions":
            return self._get_interactions(arguments)
        elif operation == "get_interactors":
            return self._get_interactors(arguments)
        elif operation == "resolve":
            return self._resolve_identifiers(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

    def _get_interactions(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get chemical-protein interactions.

        Endpoint: GET /psi-mi-tab/interactionsList
        """
        # Accept 'chemical' or 'chemicals' as alias for 'identifiers'
        identifiers = (
            arguments.get("identifiers")
            or arguments.get("chemical")
            or arguments.get("chemicals")
            or []
        )

        if not identifiers:
            return {
                "status": "error",
                "error": "identifiers parameter is required (chemical names or IDs)",
            }

        if isinstance(identifiers, str):
            identifiers = [identifiers]

        identifiers = [_stitch_identifier(i) for i in identifiers]

        params = {
            # requests encodes "\r" as %0D, the separator STITCH expects. A
            # literal "%0D" here was itself encoded, to %250D.
            "identifiers": "\r".join(identifiers),
            "species": arguments.get("species", 9606),  # Default: human
            "limit": arguments.get("limit", 10),
            "required_score": arguments.get("required_score", 400),  # Medium confidence
        }

        try:
            response = requests.get(
                f"{STITCH_BASE_URL}/psi-mi-tab/interactionsList",
                params=params,
                timeout=self.timeout,
            )
            if response.status_code == 404:
                return _endpoint_unavailable_error(
                    "/psi-mi-tab/interactionsList", identifiers
                )
            response.raise_for_status()
        except requests.RequestException as e:
            return {"status": "error", "error": f"STITCH API request failed: {str(e)}"}

        rows = _parse_psi_mi_tab(response.text)
        result: Dict[str, Any] = {"status": "success", "data": rows}
        if not rows:
            result["note"] = (
                f"STITCH returned no interactions for {identifiers} at "
                f"required_score {params['required_score']}. It answers an "
                "unrecognised name the same way, so check it with "
                "STITCH_resolve_identifier, or lower required_score."
            )
        return result

    def _get_interactors(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get interaction partners for a chemical or protein.

        Endpoint: GET /tsv-no-header/interactors, then /tsv/resolveList
        """
        identifiers = arguments.get("identifiers", [])

        if not identifiers:
            return {"status": "error", "error": "identifiers parameter is required"}

        if isinstance(identifiers, str):
            identifiers = [identifiers]

        species = arguments.get("species", 9606)
        limit = arguments.get("limit", 10)
        partners: List[Dict[str, Any]] = []
        try:
            for query in identifiers:
                # One identifier per call: the first line is the query's own
                # id, the rest its partners in STITCH's ranking.
                response = requests.get(
                    f"{STITCH_BASE_URL}/tsv-no-header/interactors",
                    params={
                        "identifier": _stitch_identifier(query),
                        "species": species,
                        "limit": limit,
                    },
                    timeout=self.timeout,
                )
                if response.status_code == 404:
                    return _endpoint_unavailable_error(
                        "/tsv-no-header/interactors", identifiers
                    )
                if response.status_code == 400:
                    return {
                        "status": "error",
                        "error": f"STITCH did not recognise '{query}' in taxon "
                        f"{species}. Check it with STITCH_resolve_identifier.",
                    }
                response.raise_for_status()
                ids = response.text.split()
                partners += [
                    {"stringId": pid, "query": query, "rank": rank}
                    for rank, pid in enumerate(ids[1:], start=1)
                ]
            names = self._names_for([p["stringId"] for p in partners], species)
        except requests.RequestException as e:
            return {"status": "error", "error": f"STITCH API request failed: {str(e)}"}

        for partner in partners:
            partner.update(names.get(partner["stringId"], {}))
        return {"status": "success", "data": partners}

    def _names_for(self, ids: List[str], species: Any) -> Dict[str, Dict[str, str]]:
        """{stringId: {preferredName, annotation}}, one call for all of them.

        resolveList is fuzzy for a name ("TP53" lists RPRM first) but exact for
        an id, which is all this passes it.
        """
        if not ids:
            return {}
        response = requests.get(
            f"{STITCH_BASE_URL}/tsv/resolveList",
            params={"identifiers": "\r".join(dict.fromkeys(ids)), "species": species},
            timeout=self.timeout,
        )
        response.raise_for_status()
        names: Dict[str, Dict[str, str]] = {}
        lines = response.text.splitlines()
        header = lines[0].split("\t") if lines else []
        for line in lines[1:]:
            row = dict(zip(header, line.split("\t")))
            if row.get("stringId") in ids and row["stringId"] not in names:
                names[row["stringId"]] = {
                    "preferredName": row.get("preferredName", ""),
                    "annotation": row.get("annotation", ""),
                }
        return names

    def _resolve_identifiers(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve chemical/protein names to STITCH identifiers.

        Endpoint: GET /json/resolve
        """
        identifier = arguments.get("identifier", "")

        if not identifier:
            return {"status": "error", "error": "identifier parameter is required"}

        params = {"identifier": identifier, "species": arguments.get("species", 9606)}

        try:
            response = requests.get(
                f"{STITCH_BASE_URL}/json/resolve",
                params=params,
                timeout=self.timeout,
            )
            if response.status_code == 404:
                return {
                    "status": "error",
                    "error": f"Identifier '{identifier}' not found in STITCH. "
                    "Try using CID identifiers or check at https://stitch-db.org/",
                }
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except requests.RequestException as e:
            return {"status": "error", "error": f"STITCH API request failed: {str(e)}"}
