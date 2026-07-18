"""Regression guard for two round-9 ClinicalTrials_search_studies fixes:

Fix-R9D-1: an unquoted multi-word query.cond/query.intr value is treated
by CTG API v2's Essie search engine as an implicit-OR keyword match, not a
phrase, so "cervical cancer" ranked unrelated head/neck and esophageal
trials above actual cervical cancer trials (confirmed live: 11215 vs. 2519
matches, with the quoted results correctly topped by cervical-cancer-
specific trials). Plain multi-word values are now phrase-quoted; values
already using quotes/parens/boolean operators (which query_cond's own
docs advertise support for) are left untouched.

Fix-R9D-2: `intervention` and `sponsor` were live, functional parameter
aliases in the tool's Python code but undeclared in its JSON schema, so
`tu info` didn't show them -- and once additionalProperties: false lands
(a separate round-8 fix), these undocumented aliases would start being
silently rejected as unrecognized properties.
"""

import json
from unittest.mock import MagicMock, patch

import jsonschema
import pytest

from tooluniverse.ctg_tool import ClinicalTrialsTool, _phrase_quote_if_plain

pytestmark = pytest.mark.unit


def _tool():
    return ClinicalTrialsTool(
        {
            "name": "ClinicalTrials_search_studies",
            "type": "ClinicalTrialsTool",
            "fields": {"operation": "search"},
            "query_schema": {},
            "parameter": {"type": "object", "properties": {}},
        }
    )


def _mock_response():
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"studies": [], "totalCount": 0}
    return resp


def test_plain_multiword_condition_is_phrase_quoted():
    assert _phrase_quote_if_plain("cervical cancer") == '"cervical cancer"'


def test_single_word_condition_is_not_quoted():
    assert _phrase_quote_if_plain("melanoma") == "melanoma"


def test_boolean_operator_query_is_not_quoted():
    assert _phrase_quote_if_plain("breast cancer AND HER2") == "breast cancer AND HER2"


def test_already_quoted_value_is_not_double_quoted():
    assert _phrase_quote_if_plain('"cervical cancer"') == '"cervical cancer"'


def test_condition_and_intervention_are_quoted_in_live_request():
    tool = _tool()
    with patch("requests.get", return_value=_mock_response()) as mock_get:
        tool.run(
            {
                "condition": "cervical cancer",
                "intervention": "immunotherapy radiotherapy",
                "max_results": 5,
            }
        )

    params = mock_get.call_args.kwargs["params"]
    assert params["query.cond"] == '"cervical cancer"'
    assert params["query.intr"] == '"immunotherapy radiotherapy"'


def test_sponsor_alias_maps_to_query_spons():
    tool = _tool()
    with patch("requests.get", return_value=_mock_response()) as mock_get:
        tool.run({"sponsor": "National Cancer Institute"})

    params = mock_get.call_args.kwargs["params"]
    assert params["query.spons"] == "National Cancer Institute"


def test_schema_declares_intervention_and_sponsor():
    with open("src/tooluniverse/data/clinicaltrials_gov_tools.json") as f:
        tools = json.load(f)
    schema = next(
        t for t in tools if t["name"] == "ClinicalTrials_search_studies"
    )["parameter"]

    assert "intervention" in schema["properties"]
    assert "sponsor" in schema["properties"]
    jsonschema.validate({"condition": "hearing loss", "intervention": "gene therapy"}, schema)
