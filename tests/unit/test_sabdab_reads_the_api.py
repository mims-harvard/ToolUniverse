"""SAbDab has a JSON API; the tool was looking in the wrong place.

The site answers 200 text/html for every path, including ones that look like
data routes, so the tool concluded "SAbDab appears to have migrated to a new
site (SAbDab2) with no public summary-data API currently reachable". The API is
reachable: GET .../sabdab/api/ returns {"message": "Welcome to the SAbDab
API!"} and .../api/openapi.json identifies SAbDab 2.1.4.

Two things hid it. The entries are keyed by the extended PDB ID, so
/api/pdb/3hfm answers 404 "No PDB entry found with pdb_id='3hfm'" -- a real
route rejecting a real structure -- while /api/pdb/pdb_00003hfm returns it.

The chain vocabulary matters as much. Tallied over 286 chains in 40 structures:
H heavy (98), N non-antibody (92), K kappa light (50), L lambda light (42), M
single-chain construct (4). Light chains are K *or* L, and 3hfm is the case
that proves it: its light chain is kappa on auth_asym_id "L", so matching on
"L" dropped it and an antigen rule of "not H or L" then reported the antibody's
own light chain as the antigen.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tooluniverse.sabdab_tool import SAbDabTool

pytestmark = pytest.mark.unit

DATA = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"


def _config(operation):
    return {
        "name": f"SAbDab_{operation}",
        "type": "SAbDabTool",
        "fields": {"operation": operation},
        "parameter": {"type": "object", "properties": {}},
    }


# 3hfm as the API returns it: heavy H, kappa light on chain "L", lysozyme antigen.
_ENTRY_3HFM = {
    "id": "pdb_00003hfm",
    "name": "STRUCTURE OF AN ANTIBODY-ANTIGEN COMPLEX",
    "head": "COMPLEX(ANTIBODY-ANTIGEN)",
    "resolution": 3.0,
    "structure_method": "X-ray diffraction",
    "deposition_date": "1988-08-11",
    "release_date": "1988-08-11",
    "r_work": None,
    "r_free": None,
    "polymer_instances": [
        {
            "sabdab_auth_asym_id": "H",
            "sabdab_chain_type": "H",
            "name": "HYHEL-10 IGG1 FAB (HEAVY CHAIN)",
            "organism_scientific": "mus musculus",
            "sequence": "DVQ",
        },
        {
            "sabdab_auth_asym_id": "L",
            "sabdab_chain_type": "K",
            "name": "HYHEL-10 IGG1 FAB (LIGHT CHAIN)",
            "organism_scientific": "mus musculus",
            "sequence": "DIV",
        },
        {
            "sabdab_auth_asym_id": "Y",
            "sabdab_chain_type": "N",
            "name": "HEN EGG WHITE LYSOZYME",
            "organism_scientific": "gallus gallus",
            "sequence": "KVF",
        },
    ],
    "antibody_instances": [
        {
            "id": "pdb_00003hfm-H-L",
            "antibody_id": "sabdab2_H0009L001N",
            "type": "FAB",
            "pairing_distance": 17.8,
            "any_cdr_coords_resolved": True,
            "all_cdr_coords_resolved": True,
        }
    ],
}


class _Response:
    def __init__(self, status=200, payload=None):
        self.status_code = status
        self._payload = payload
        self.headers = {"Content-Type": "application/json"}

    def json(self):
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


def _run(operation, arguments, response, capture=None):
    tool = SAbDabTool(_config(operation))

    def fake_get(url, params=None, timeout=None, headers=None):
        if capture is not None:
            capture.setdefault("urls", []).append(url)
        return response if not callable(response) else response(url)

    with patch("tooluniverse.sabdab_tool.requests.get", fake_get):
        return tool.run({"operation": operation, **arguments})


def test_a_four_character_pdb_id_is_sent_as_the_extended_form():
    """/api/pdb/3hfm is a real route that 404s; pdb_00003hfm is the key."""
    seen = {}
    _run(
        "get_structure_summary",
        {"pdb_id": "3hfm"},
        _Response(200, _ENTRY_3HFM),
        capture=seen,
    )

    assert seen["urls"], "no request was made"
    url = seen["urls"][0]
    assert url.endswith("/api/pdb/pdb_00003hfm"), (
        f"requested {url}; SAbDab 2 keys entries by the extended PDB ID"
    )


def test_an_already_extended_id_is_not_mangled():
    seen = {}
    _run(
        "get_structure_summary",
        {"pdb_id": "pdb_00003hfm"},
        _Response(200, _ENTRY_3HFM),
        capture=seen,
    )

    assert seen["urls"][0].endswith("/api/pdb/pdb_00003hfm")


def test_a_kappa_light_chain_is_a_light_chain_not_an_antigen():
    """3hfm's light chain is typed K on auth_asym_id "L"."""
    data = _run("get_structure_summary", {"pdb_id": "3hfm"}, _Response(200, _ENTRY_3HFM))[
        "data"
    ]

    assert data["heavy_chains"] == ["H"]
    assert data["light_chains"] == ["L"], (
        "the kappa chain must be reported as light; matching only on type 'L' "
        "drops it"
    )
    assert [a["name"] for a in data["antigen_chains"]] == ["HEN EGG WHITE LYSOZYME"], (
        "only chains typed N are antigen; 'not heavy or light' files the "
        "antibody's own kappa chain as the antigen"
    )
    assert data["unclassified_chains"] == []


def test_an_unknown_chain_type_is_surfaced_rather_than_called_antigen():
    """A type SAbDab adds later must not be silently reported as antigen."""
    entry = json.loads(json.dumps(_ENTRY_3HFM))
    entry["polymer_instances"].append(
        {
            "sabdab_auth_asym_id": "Z",
            "sabdab_chain_type": "Q",
            "name": "something new",
        }
    )
    data = _run("get_structure_summary", {"pdb_id": "3hfm"}, _Response(200, entry))["data"]

    assert [c["chain"] for c in data["antigen_chains"]] == ["Y"]
    assert data["unclassified_chains"] == [{"chain": "Z", "chain_type": "Q"}]


def test_a_structure_sabdab_does_not_hold_is_an_error_naming_why():
    result = _run("get_structure_summary", {"pdb_id": "1crn"}, _Response(404))

    assert result["status"] == "error"
    assert "1crn" in result["error"]
    assert "antibody" in result["error"].lower(), (
        "say that SAbDab holds antibody structures only, so the caller knows "
        "this is not a lookup failure"
    )


def test_get_structure_says_where_coordinates_come_from():
    """It never returned coordinates, and SAbDab 2 has no route for them."""
    data = _run("get_structure", {"pdb_id": "3hfm"}, _Response(200, _ENTRY_3HFM))["data"]

    assert len(data["chains"]) == 3
    assert len(data["antibodies"]) == 1
    assert "rcsb" in data["coordinates"].lower()


def test_search_reports_that_it_did_not_search():
    """Every filter parameter on /api/pdb is accepted and ignored."""
    data = _run(
        "search_structures",
        {"query": "anti-CD20"},
        _Response(200, {"total": 11667, "limit": 1, "offset": 0, "results": []}),
    )["data"]

    assert data["searched"] is False, (
        "an empty answer from a search that never ran must not look like "
        "evidence of absence"
    )
    assert data["catalogue_size"] == 11667
    assert data["next_steps"]


def test_the_summary_counts_come_from_the_api_not_a_hardcoded_string():
    """It used to return a fixed blurb with status success and no request."""
    payloads = iter(
        [
            _Response(200, {"total": 11667, "results": []}),
            _Response(200, {"total": 6927, "results": []}),
        ]
    )
    data = _run("get_summary", {}, lambda url: next(payloads))["data"]

    assert data["structures"] == 11667
    assert data["unique_antibodies"] == 6927


def test_a_non_json_200_is_not_treated_as_data():
    """The surrounding site answers 200 text/html for unknown paths."""
    result = _run("get_structure_summary", {"pdb_id": "3hfm"}, _Response(200, None))

    assert result["status"] == "error"
    assert "not JSON" in result["error"] or "not an API route" in result["error"]


def test_the_schema_describes_what_the_tool_returns():
    """A flat schema, so the validator checks the envelope (#692)."""
    tools = {t["name"]: t for t in json.loads((DATA / "sabdab_tools.json").read_text("utf-8"))}
    schema = tools["SAbDab_get_structure_summary"]["return_schema"]

    assert "oneOf" not in schema, (
        "`data` must sit at the schema's top level or the validator unwraps "
        "past it and checks nothing"
    )
    assert "data" in schema["properties"]
    declared = schema["properties"]["data"]["properties"]
    for field in ("heavy_chains", "light_chains", "antigen_chains", "unclassified_chains"):
        assert field in declared, f"{field} is returned but not declared"
