"""STITCH's interaction tools read the API formats stitch-db.org still serves.

Both tools returned "endpoint appears unavailable" for every call -- the
/json/interactions and /json/network routes 404 on stitch-db.org -- and the
weekly sweep (run 37273817054) counted 4 failures. The same API still answers
psi-mi-tab/interactionsList and tsv-no-header/interactors (confirmed live
2026-10-05), which carry the same data.

Two identifier bugs came out with it: "CID000002244" was rewritten to
"CIDm00002244", a form interactionsList finds nothing for, and the "%0D"
separator was itself URL-encoded to "%250D", so a multi-identifier query was
one unrecognisable string.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.stitch_tool import STITCHTool, _parse_psi_mi_tab, _stitch_identifier

pytestmark = pytest.mark.unit

ROW = (
    "string:9606.ENSP00000354612\tstring:-1.CID100002244\tPTGS1\taspirin\t"
    "-\t-\t-\t-\t-\ttaxid:-2\ttaxid:-2\t-\t-\t-\t"
    "score:0.999|escore:0.725|dscore:0.9|tscore:0.986"
)


def _resp(text="", status_code=200):
    r = MagicMock()
    r.status_code = status_code
    r.text = text
    r.raise_for_status = MagicMock()
    return r


@pytest.mark.parametrize(
    ("given", "sent"),
    [
        ("CIDm00002244", "CID100002244"),
        ("CIDs00002244", "CID000002244"),
        ("-1.CID100002244", "CID100002244"),  # what STITCH_resolve_identifier returns
        ("CID000002244", "CID000002244"),  # worked already; no longer rewritten
        ("aspirin", "aspirin"),
        ("9606.ENSP00000269305", "9606.ENSP00000269305"),
    ],
)
def test_identifiers_are_sent_in_a_form_the_network_finds(given, sent):
    assert _stitch_identifier(given) == sent


def test_psi_mi_tab_rows_become_the_declared_objects():
    (row,) = _parse_psi_mi_tab(ROW + "\n\n")

    assert row == {
        "stringId_A": "9606.ENSP00000354612",
        "stringId_B": "-1.CID100002244",
        "preferredName_A": "PTGS1",
        "preferredName_B": "aspirin",
        "score": 0.999,
        "escore": 0.725,
        "dscore": 0.9,
        "tscore": 0.986,
    }


def test_interactions_query_the_served_route_with_a_real_separator():
    tool = STITCHTool({"fields": {"operation": "get_interactions"}})

    with patch("tooluniverse.stitch_tool.requests.get", return_value=_resp(ROW)) as get:
        result = tool.run({"identifiers": ["aspirin", "CIDm00002244"]})

    url, kwargs = get.call_args[0][0], get.call_args[1]
    assert url.endswith("/psi-mi-tab/interactionsList")
    assert kwargs["params"]["identifiers"] == "aspirin\rCID100002244"
    assert result["status"] == "success" and result["data"][0]["score"] == 0.999


def test_no_interactions_says_how_to_check_the_name():
    tool = STITCHTool({"fields": {"operation": "get_interactions"}})

    with patch("tooluniverse.stitch_tool.requests.get", return_value=_resp("\n")):
        result = tool.run({"identifiers": ["notachemical"]})

    assert result["status"] == "success" and result["data"] == []
    assert "STITCH_resolve_identifier" in result["note"]


def test_partners_are_ranked_and_named_by_exact_id():
    tool = STITCHTool({"fields": {"operation": "get_interactors"}})
    interactors = _resp("9606.P53\n9606.MDM2\n9606.CDKN1A\n")
    # resolveList is fuzzy for names, so a stray match must not be used.
    names = _resp(
        "queryIndex\tstringId\tncbiTaxonId\ttaxonName\tpreferredName\tannotation\n"
        "0\t9606.MDM2\t9606\tHomo sapiens\tMDM2\tp53 E3 ligase\n"
        "0\t9606.OTHER\t9606\tHomo sapiens\tRPRM\tunrelated\n"
        "1\t9606.CDKN1A\t9606\tHomo sapiens\tCDKN1A\tp21\n"
    )

    with patch("tooluniverse.stitch_tool.requests.get", side_effect=[interactors, names]):
        result = tool.run({"identifiers": ["TP53"]})

    assert result["status"] == "success"
    assert [(p["rank"], p["preferredName"], p["query"]) for p in result["data"]] == [
        (1, "MDM2", "TP53"),
        (2, "CDKN1A", "TP53"),
    ]


def test_an_unrecognised_partner_query_is_named_as_such():
    tool = STITCHTool({"fields": {"operation": "get_interactors"}})

    with patch(
        "tooluniverse.stitch_tool.requests.get",
        return_value=_resp("Error\tErrorMessage\tnot found", status_code=400),
    ):
        result = tool.run({"identifiers": ["notachemical"]})

    assert result["status"] == "error"
    assert "did not recognise 'notachemical'" in result["error"]
