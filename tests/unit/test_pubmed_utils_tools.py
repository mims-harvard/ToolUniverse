"""PubMed_convert_article_ids and PubMed_lookup_article_by_citation (mocked NCBI)."""

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _response(payload=None, text="", status=200):
    response = MagicMock()
    response.status_code = status
    response.text = text or (str(payload) if payload is not None else "")
    response.json.return_value = payload
    return response


def _convert(arguments, responder):
    from tooluniverse.pubmed_utils_tool import PubMedConvertIDsTool

    tool = PubMedConvertIDsTool({"name": "PubMed_convert_article_ids"})
    calls = []

    def fake(session, method, url, params=None, **kwargs):
        calls.append(dict(params))
        return responder(params)

    with patch("tooluniverse.pubmed_utils_tool.request_with_retry", fake):
        return tool.run(arguments), calls


def _idconv(params):
    records = []
    for requested in params["ids"].split(","):
        if requested == "99999999999":
            records.append(
                {
                    "pmid": 99999999999,
                    "requested-id": requested,
                    "status": "error",
                    "errmsg": "Identifier not found in PMC",
                }
            )
        else:
            records.append(
                {
                    "doi": "10.1093/nar/gks1195",
                    "pmcid": "PMC3531190",
                    "pmid": 23193287,
                    "requested-id": requested,
                }
            )
    return _response({"status": "ok", "records": records})


def test_mixed_identifiers_are_grouped_by_detected_type():
    result, calls = _convert(
        {"ids": ["23193287", "PMC3531190", "10.1093/nar/gks1195"]}, _idconv
    )
    assert {c["idtype"] for c in calls} == {"pmid", "pmcid", "doi"}
    assert [r["requested_id"] for r in result["data"]] == [
        "23193287",
        "PMC3531190",
        "10.1093/nar/gks1195",
    ]
    assert all(
        r["pmid"] == "23193287" and r["pmcid"] == "PMC3531190" for r in result["data"]
    )
    assert result["metadata"]["found"] == 3


def test_identifier_missing_from_pmc_is_reported_not_invented():
    result, _ = _convert({"ids": "23193287, 99999999999", "id_type": "pmid"}, _idconv)
    ok, missing = result["data"]
    assert ok["found"] is True
    assert missing["found"] is False
    assert missing["pmcid"] is None and missing["doi"] is None
    assert missing["error"] == "Identifier not found in PMC"
    assert result["metadata"]["found"] == 1


def test_unrecognised_identifier_asks_for_id_type():
    result, calls = _convert({"ids": ["not-an-id"]}, _idconv)
    assert calls == []
    assert result["data"][0]["found"] is False
    assert "id_type" in result["data"][0]["error"]


def test_server_rejection_is_an_error():
    def reject(params):
        return _response(
            {"status": "error", "errors": [{"message": "bad ids"}]}, status=400
        )

    result, _ = _convert({"ids": ["23193287"]}, reject)
    assert result["status"] == "error"
    assert "bad ids" in result["error"]


def test_too_many_ids_and_missing_ids_are_errors():
    assert _convert({"ids": []}, _idconv)[0]["status"] == "error"
    assert (
        _convert({"ids": [str(i) for i in range(201)]}, _idconv)[0]["status"] == "error"
    )


def _lookup(arguments, body):
    from tooluniverse.pubmed_utils_tool import PubMedCitationLookupTool

    tool = PubMedCitationLookupTool({"name": "PubMed_lookup_article_by_citation"})
    sent = {}

    def fake(session, method, url, params=None, **kwargs):
        sent.update(params)
        return _response(text=body)

    with patch("tooluniverse.pubmed_utils_tool.request_with_retry", fake):
        return tool.run(arguments), sent


def test_single_citation_is_sent_in_ecitmatch_format_and_parsed():
    result, sent = _lookup(
        {
            "journal": "Nature",
            "year": 2015,
            "volume": 521,
            "first_page": 436,
            "author": "lecun y",
        },
        "nature|2015|521|436|lecun y|c1|26017442\n",
    )
    assert sent["bdata"] == "Nature|2015|521|436|lecun y|c1|"
    assert sent["db"] == "pubmed"
    row = result["data"][0]
    assert (row["pmid"], row["status"]) == ("26017442", "found")


def test_batch_keeps_input_keys_and_reports_not_found():
    body = (
        "proc natl acad sci u s a|1991|88|3248|mann bj|mann1991|2014248\n"
        "nature|1900|1|1||nope|NOT_FOUND\n"
    )
    result, sent = _lookup(
        {
            "citations": [
                {
                    "journal": "proc natl acad sci u s a",
                    "year": 1991,
                    "volume": 88,
                    "first_page": 3248,
                    "author": "mann bj",
                    "key": "mann1991",
                },
                {
                    "journal": "nature",
                    "year": 1900,
                    "volume": 1,
                    "first_page": 1,
                    "key": "nope",
                },
            ]
        },
        body,
    )
    assert sent["bdata"].count("\r") == 1
    found, missing = result["data"]
    assert (found["key"], found["pmid"], found["status"]) == (
        "mann1991",
        "2014248",
        "found",
    )
    assert (missing["key"], missing["pmid"], missing["status"]) == (
        "nope",
        None,
        "not_found",
    )
    assert result["metadata"]["found"] == 1


def test_pipe_characters_in_fields_cannot_shift_the_columns():
    _, sent = _lookup(
        {
            "journal": "Na|ture",
            "year": 2015,
            "volume": 1,
            "first_page": 2,
            "author": "x",
        },
        "",
    )
    assert sent["bdata"].split("|")[0] == "Na ture"
    assert sent["bdata"].count("|") == 6


def test_no_citation_is_an_error():
    result, _ = _lookup({}, "")
    assert result["status"] == "error"
