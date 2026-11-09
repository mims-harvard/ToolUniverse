"""Regression tests for complete HPO synonyms and translations."""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.hpo_tool import HPOTool

pytestmark = pytest.mark.unit


def _response(payload):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    return response


def _tool(endpoint):
    return HPOTool({"fields": {"endpoint": endpoint}})


def test_search_keeps_all_synonyms_and_count():
    synonyms = [f"developmental-delay-synonym-{index}" for index in range(23)]
    payload = {
        "totalCount": 1,
        "terms": [
            {
                "id": "HP:0001263",
                "name": "Global developmental delay",
                "definition": "A delay in several areas of development.",
                "descendantCount": 10,
                "synonyms": synonyms,
            }
        ],
    }
    with patch("tooluniverse.hpo_tool.requests.get", return_value=_response(payload)):
        result = _tool("search_terms").run(
            {"query": "developmental delay", "max_results": 1}
        )

    term = result["data"][0]
    assert term["synonyms"] == synonyms
    assert term["synonym_count"] == 23


def test_term_keeps_every_translation_and_reports_qualifier_counts():
    languages = ["TR", "DE", "FR", "ES", "NL", "IT", "JA", "CS", "ZH"]
    translations = [
        {
            "language": language,
            "name": f"translated-{language}",
            # HPO marks each label OFFICIAL or CANDIDATE, and a CANDIDATE is
            # a proposal rather than a name the ontology stands behind.
            "status": "OFFICIAL" if language == "JA" else "CANDIDATE",
            "definition": f"definition-{language}" if language == "DE" else None,
        }
        for language in languages
    ]
    payload = {
        "id": "HP:0001263",
        "name": "Global developmental delay",
        "synonyms": [f"synonym-{index}" for index in range(23)],
        "xrefs": [f"UMLS:{index}" for index in range(4)],
        "translations": translations,
    }
    with patch("tooluniverse.hpo_tool.requests.get", return_value=_response(payload)):
        result = _tool("get_term").run({"term_id": "HP:0001263"})

    data = result["data"]
    assert data["translations"] == translations, (
        "every translation must survive, in order, with its status and its "
        "translated definition"
    )
    assert data["translation_count"] == 9
    assert data["translations_truncated"] is False
    assert [t["status"] for t in data["translations"]].count("OFFICIAL") == 1
    assert data["synonym_count"] == 23
    assert data["xref_count"] == 4
