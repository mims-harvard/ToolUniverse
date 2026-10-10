"""EuropePMC_search_case_reports: case reports on a condition, with abstracts.

The tool searches title and abstract (``TITLE_ABS``) of records Europe PMC
types as ``PUB_TYPE:"Case Reports"``. Measured live (2026-10-10):

    TITLE_ABS:(intussusception adult) AND PUB_TYPE:"Case Reports"     973
    TITLE_ABS:(intussusception AND adult) ...                          973  (AND is the default)
    TITLE_ABS:(intussusceptions) ...                                   351  (vs 4,845: no stemming)
    TITLE_ABS:(intussusception (adult) ...                           2,147  (unbalanced paren)
    TITLE_ABS:(scaphoid "fracture) ...                                   0  (unbalanced quote)

so the query keeps only words and balanced quoted phrases, and a query whose
words never all occur together falls back to any of them (ranked by relevance)
and says so.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.europe_pmc_tool import (
    EuropePMCCaseReportsTool,
    EuropePMCTool,
    _search_terms,
)

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "src" / "tooluniverse" / "data" / "europe_pmc_tools.json"


def _record(idx, first_pdate="2023-12-07"):
    return {
        "id": f"MED{idx}",
        "source": "MED",
        "pmid": f"{idx}",
        "title": f"Case {idx}",
        "abstractText": "A <b>rare</b> case.",
        "pubYear": "2024",
        "firstPublicationDate": first_pdate,
    }


def _response(payload, status_code=200):
    response = MagicMock()
    response.status_code = status_code
    response.reason = "OK" if status_code == 200 else "Service Unavailable"
    response.json.return_value = payload
    return response


def _run(arguments, hit_count=2, n_records=2, status_code=200, or_hits=None):
    """Run the tool against canned responses. ``or_hits`` is the hit count for
    the any-word fallback query (default: same as ``hit_count``)."""
    tool = EuropePMCCaseReportsTool({"name": "EuropePMC_search_case_reports"})

    def respond(session, method, url, params=None, **kwargs):
        hits = hit_count
        if or_hits is not None and " OR " in params["query"]:
            hits = or_hits
        payload = {
            "hitCount": hits,
            "resultList": {"result": [_record(i) for i in range(min(n_records, hits))]},
        }
        return _response(payload, status_code)

    with patch(
        "tooluniverse.europe_pmc_tool.request_with_retry", side_effect=respond
    ) as request:
        result = tool.run(arguments)
    return result, request


def _sent_queries(request):
    return [call.kwargs["params"]["query"] for call in request.call_args_list]


def test_query_restricts_to_case_reports_in_title_or_abstract():
    result, request = _run({"query": "Meckel diverticulum torsion", "limit": 3})

    expected = 'TITLE_ABS:(Meckel diverticulum torsion) AND PUB_TYPE:"Case Reports"'
    assert set(_sent_queries(request)) == {expected}
    assert all(c.kwargs["params"]["pageSize"] == 3 for c in request.call_args_list)
    assert result["status"] == "success"
    assert result["metadata"]["query"] == expected
    assert result["metadata"]["total_results"] == 2
    assert result["truncated"] is False
    first = result["data"][0]
    assert first["abstract"] == "A rare case."
    assert first["first_publication_date"] == "2023-12-07"


@pytest.mark.parametrize(
    "arguments, clause",
    [
        ({"published_before": "2023"}, "FIRST_PDATE:[1800-01-01 TO 2023-12-31]"),
        ({"published_before": "2023-06-30"}, "FIRST_PDATE:[1800-01-01 TO 2023-06-30]"),
        ({"published_after": "2015"}, "FIRST_PDATE:[2015-01-01 TO 3000-12-31]"),
        (
            {"published_after": "2015-03-01", "published_before": 2020},
            "FIRST_PDATE:[2015-03-01 TO 2020-12-31]",
        ),
    ],
)
def test_publication_date_bounds(arguments, clause):
    result, request = _run({"query": "retrocaval ureter", **arguments})

    assert all(q.endswith(" AND " + clause) for q in _sent_queries(request))
    assert result["metadata"]["query"].endswith(clause)


@pytest.mark.parametrize("value", ["June 2020", "2020/06/30", "20", "2020-6-1"])
def test_malformed_dates_are_rejected_before_searching(value):
    result, request = _run({"query": "retrocaval ureter", "published_before": value})

    assert result["status"] == "error"
    assert "published_before" in result["error"]
    request.assert_not_called()


@pytest.mark.parametrize(
    "raw, terms",
    [
        ("intussusception (adult", ["intussusception", "adult"]),
        ('scaphoid "fracture', ["scaphoid", "fracture"]),
        ('"Meckel diverticulum" torsion', ['"Meckel diverticulum"', "torsion"]),
        ("ITP (immune thrombocytopenia)", ["ITP", "immune", "thrombocytopenia"]),
        ("TITLE:foo -bar [rare]^2", ["TITLE", "foo", "bar", "rare", "2"]),
        ("adult or child AND NOT infant", ["adult", "child", "infant"]),
        ("anti-GFAP Meckel's 45-year-old", ["anti-GFAP", "Meckel's", "45-year-old"]),
        ('"" ( ) :', []),
    ],
)
def test_search_terms_keep_only_words_and_balanced_phrases(raw, terms):
    assert _search_terms(raw) == terms


def test_unbalanced_parenthesis_is_not_sent():
    _result, request = _run({"query": "intussusception (adult"})

    assert set(_sent_queries(request)) == {
        'TITLE_ABS:(intussusception adult) AND PUB_TYPE:"Case Reports"'
    }


def test_no_report_with_every_word_falls_back_to_any_word():
    result, request = _run(
        {"query": "axial torsion of Meckel diverticulum in a 45-year-old man"},
        hit_count=0,
        or_hits=710316,
    )

    queries = list(dict.fromkeys(_sent_queries(request)))
    assert queries == [
        'TITLE_ABS:(axial torsion of Meckel diverticulum in a 45-year-old man)'
        ' AND PUB_TYPE:"Case Reports"',
        'TITLE_ABS:(axial OR torsion OR of OR Meckel OR diverticulum OR in OR a OR '
        '45-year-old OR man) AND PUB_TYPE:"Case Reports"',
    ]
    assert result["status"] == "success"
    assert len(result["data"]) == 2
    assert result["metadata"]["query"] == queries[1]
    assert result["metadata"]["matching"].startswith("ANY query word")
    assert result["truncated"] is True
    assert "hint" not in result["metadata"]


def test_a_single_word_with_no_hits_is_reported_with_a_hint():
    result, request = _run({"query": "intussusceptions"}, hit_count=0, n_records=0)

    assert len(set(_sent_queries(request))) == 1  # nothing to relax
    assert result["data"] == []
    assert result["metadata"]["total_results"] == 0
    assert "singular" in result["metadata"]["hint"]
    assert result["truncated"] is False


def test_truncation_is_disclosed_like_the_article_search():
    result, _ = _run({"query": "intussusception adult", "limit": 2}, hit_count=973)

    assert "hint" not in result["metadata"]
    assert result["truncated"] is True
    assert "973" in result["truncation_note"] and "up to 25" in result["truncation_note"]
    assert result["metadata"]["count"] == 2
    assert result["metadata"]["matching"].startswith("every query word")


@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"query": ""},
        {"query": "  ( ) "},
        {"query": "and or"},
        {"query": 5},
        {"query": "x", "limit": "many"},
    ],
)
def test_invalid_arguments(arguments):
    result, request = _run(arguments)

    assert result["status"] == "error"
    request.assert_not_called()


def test_limit_is_clamped():
    _result, request = _run({"query": "x", "limit": 500})
    assert {c.kwargs["params"]["pageSize"] for c in request.call_args_list} == {25}
    _result, request = _run({"query": "x", "limit": 0})
    assert {c.kwargs["params"]["pageSize"] for c in request.call_args_list} == {5}


def test_upstream_failure_is_an_error_not_an_empty_success():
    result, _ = _run({"query": "retrocaval ureter"}, status_code=503)

    assert result["status"] == "error"
    assert "503" in result["error"]
    assert result["retryable"] is True
    assert "PUB_TYPE" in result["query"]


def test_article_search_also_reports_first_publication_date():
    tool = EuropePMCTool({"name": "EuropePMC_search_articles"})
    payload = {"hitCount": 1, "resultList": {"result": [_record(1, "2019-02-03")]}}
    with patch(
        "tooluniverse.europe_pmc_tool.request_with_retry",
        return_value=_response(payload),
    ):
        result = tool.run({"query": "x"})

    assert result["data"][0]["first_publication_date"] == "2019-02-03"
    assert result["data"][0]["year"] == "2024"


def test_config_parameters_match_what_the_tool_reads():
    import inspect
    import re

    tools = {t["name"]: t for t in json.loads(CONFIG.read_text())}
    spec = tools["EuropePMC_search_case_reports"]
    assert spec["type"] == "EuropePMCCaseReportsTool"
    read = set(
        re.findall(
            r'arguments\.get\("(\w+)"', inspect.getsource(EuropePMCCaseReportsTool.run)
        )
    )
    assert read == set(spec["parameter"]["properties"])
    assert spec["parameter"]["required"] == ["query"]
    jsonschema = pytest.importorskip("jsonschema")
    for example in spec["test_examples"]:
        jsonschema.validate(example, spec["parameter"])
    item = spec["return_schema"]["oneOf"][0]["items"]["properties"]
    assert "first_publication_date" in item
    assert (
        "first_publication_date"
        in tools["EuropePMC_search_articles"]["return_schema"]["oneOf"][0]["items"][
            "properties"
        ]
    )
