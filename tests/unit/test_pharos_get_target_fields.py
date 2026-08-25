"""Unit tests for Pharos_get_target's returned fields. Network mocked.

The tool advertises diseases, ligands and druggability data, but its GraphQL
selection hard-coded only eight scalar fields, so none of those ever arrived.
The selection now also requests diseaseCounts/diseases and ligandCounts/ligands.

Field names were verified against the live Pharos GraphQL schema by introspecting
the Target type before they were added; these tests pin the selection so a
regression that quietly drops a field is caught offline.
"""

import json
from unittest.mock import MagicMock, patch

from tooluniverse.pharos_tool import _TARGET_DETAIL_TOP, PharosTool

_CONFIG = {
    "name": "Pharos_get_target",
    "type": "PharosTool",
    "parameter": {"type": "object", "properties": {}},
    "fields": {"operation": "get_target"},
}

_TARGET = {
    "name": "Glutamate carboxypeptidase 2",
    "sym": "FOLH1",
    "uniprot": "Q04609",
    "tdl": "Tclin",
    "fam": "Enzyme",
    "novelty": 0.0002861,
    "description": "This gene encodes a type II transmembrane glycoprotein.",
    "publicationCount": 204,
    "diseaseCounts": [
        {"name": "prostate cancer", "value": 1195},
        {"name": "schizophrenia", "value": 1103},
    ],
    "diseases": [
        {
            "name": "prostate cancer",
            "associationCount": 1195,
            "mondoID": "MONDO:0008315",
        }
    ],
    "ligandCounts": [{"name": "ligand", "value": 240}, {"name": "drug", "value": 1}],
    "ligands": [{"ligid": "F4UUBLMDA38Q", "name": "2-PMPA", "isdrug": False}],
}


def _tool():
    return PharosTool(dict(_CONFIG))


def _resp(data):
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = {"data": data}
    r.raise_for_status.return_value = None
    return r


def test_get_target_returns_the_promised_disease_and_ligand_fields():
    with patch(
        "tooluniverse.pharos_tool.requests.post", return_value=_resp({"target": _TARGET})
    ):
        out = _tool().run({"gene": "FOLH1"})

    assert out["status"] == "success"
    data = out["data"]
    # The eight original scalars are still there.
    for key in ("name", "sym", "uniprot", "tdl", "fam", "novelty", "publicationCount"):
        assert key in data
    # ...and so are the fields the description promises.
    assert data["diseaseCounts"][0]["name"] == "prostate cancer"
    assert data["diseases"][0]["mondoID"] == "MONDO:0008315"
    assert data["ligandCounts"] == [
        {"name": "ligand", "value": 240},
        {"name": "drug", "value": 1},
    ]
    assert data["ligands"][0]["ligid"] == "F4UUBLMDA38Q"


def test_disease_count_and_truncation_note_are_reported():
    """The lists are samples; the caller must not read them as the full set."""
    with patch(
        "tooluniverse.pharos_tool.requests.post", return_value=_resp({"target": _TARGET})
    ):
        out = _tool().run({"gene": "FOLH1"})

    assert out["data"]["disease_count"] == len(_TARGET["diseaseCounts"])
    assert str(_TARGET_DETAIL_TOP) in out["data"]["ligands_note"]


def test_graphql_selection_requests_the_promised_fields():
    with patch("tooluniverse.pharos_tool.requests.post") as post:
        post.return_value = _resp({"target": _TARGET})
        _tool().run({"gene": "FOLH1"})

    payload = post.call_args.kwargs["json"]
    query = payload["query"]
    for field in ("diseaseCounts", "diseases(top: $top)", "ligandCounts", "ligands("):
        assert field in query
    assert payload["variables"] == {"q": {"sym": "FOLH1"}, "top": _TARGET_DETAIL_TOP}


def test_uniprot_and_gene_use_the_same_selection():
    """The uniprot and gene branches used to be byte-identical duplicates."""
    queries = []
    with patch("tooluniverse.pharos_tool.requests.post") as post:
        post.return_value = _resp({"target": _TARGET})
        for args in ({"gene": "FOLH1"}, {"uniprot": "Q04609"}):
            _tool().run(args)
            queries.append(post.call_args.kwargs["json"]["query"])

    assert queries[0] == queries[1]


def test_uniprot_argument_builds_a_uniprot_filter():
    with patch("tooluniverse.pharos_tool.requests.post") as post:
        post.return_value = _resp({"target": _TARGET})
        _tool().run({"uniprot": "Q04609"})

    assert post.call_args.kwargs["json"]["variables"]["q"] == {"uniprot": "Q04609"}


def test_missing_identifier_is_an_input_error():
    out = _tool().run({})
    assert out["status"] == "error"
    assert "gene" in out["error"] and "uniprot" in out["error"]


def test_unknown_target_is_an_empty_success():
    with patch(
        "tooluniverse.pharos_tool.requests.post", return_value=_resp({"target": None})
    ):
        out = _tool().run({"gene": "NOTAGENE"})

    assert out["status"] == "success"
    assert out["data"] is None
    assert "No target found" in out["message"]


def test_return_schema_documents_the_new_fields():
    from importlib.resources import files

    data = json.loads((files("tooluniverse.data") / "pharos_tools.json").read_text())
    cfg = next(t for t in data if t["name"] == "Pharos_get_target")
    props = cfg["return_schema"]["properties"]["data"]["properties"]
    for field in ("diseaseCounts", "diseases", "ligandCounts", "ligands", "tdl"):
        assert field in props


def test_ligand_targets_documents_pactivity_units():
    """Pharos activity values are pKi/pIC50 (-log10 M), never nanomolar."""
    from importlib.resources import files

    data = json.loads((files("tooluniverse.data") / "pharos_tools.json").read_text())
    cfg = next(t for t in data if t["name"] == "Pharos_get_ligand_targets")
    assert "pActivity" in cfg["description"]

    value_schema = cfg["return_schema"]["oneOf"][0]["properties"]["activities"]["items"][
        "properties"
    ]["value"]
    assert "pActivity" in value_schema["description"]
    assert "NOT nanomolar" in value_schema["description"]
