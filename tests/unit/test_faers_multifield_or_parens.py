"""Regression guard: FDA/FAERS multi-field OR groups must be parenthesized.

FDADrugAdverseEventTool maps some params to multiple openFDA fields joined with
OR (e.g. medicinalproduct -> patient.drug.medicinalproduct OR
patient.drug.openfda.generic_name; reactionmeddraverse -> reactionmeddrapt OR
reactionmeddraverse). Those OR groups were NOT parenthesized, and openFDA/Lucene
binds AND tighter than OR, so a filtered query
    a:x OR b:x AND c:y OR d:y
parsed as  a:x OR (b:x AND c:y) OR d:y  -- wrong. That silently broke every
filtered multi-field query: FAERS colistin + reaction "acute kidney injury"
returned 0 (HTTP 404) even though the unfiltered count shows
ACUTE KIDNEY INJURY = 151.
"""
import re
import urllib.parse
from unittest.mock import patch

import pytest

from tooluniverse.openfda_adv_tool import FDADrugAdverseEventTool


def _tool():
    cfg = {
        "name": "FAERS_count_reactions_by_drug_event",
        "type": "FDADrugAdverseEventTool",
        "parameter": {"type": "object", "properties": {}},
        "fields": {
            "search_fields": {
                "medicinalproduct": [
                    "patient.drug.medicinalproduct",
                    "patient.drug.openfda.generic_name",
                ],
                "reactionmeddraverse": [
                    "patient.reaction.reactionmeddrapt",
                    "patient.reaction.reactionmeddraverse",
                ],
            },
            "return_fields": ["patient.reaction.reactionmeddrapt.exact"],
        },
    }
    return FDADrugAdverseEventTool(cfg, api_key=None)


class _Resp:
    status_code = 200

    def json(self):
        return {"results": [{"term": "ACUTE KIDNEY INJURY", "count": 151}]}

    def raise_for_status(self):
        pass


def _captured_query(arguments):
    captured = {}

    def fake_get(url, timeout=None):
        captured["url"] = url
        return _Resp()

    with patch("tooluniverse.openfda_adv_tool.requests.get", side_effect=fake_get):
        _tool().run(arguments)
    # The tool url-encodes the query; decode to inspect the Lucene expression.
    q = re.search(r"search=([^&]+)", captured["url"]).group(1)
    return urllib.parse.unquote(q)


@pytest.mark.unit
def test_multifield_or_group_is_parenthesized_and_anded():
    query = _captured_query(
        {"medicinalproduct": "colistin", "reactionmeddraverse": "acute kidney injury"}
    )
    # Each multi-field OR group must be wrapped in parentheses...
    assert (
        "(patient.drug.medicinalproduct:colistin+OR+"
        "patient.drug.openfda.generic_name:colistin)"
    ) in query
    assert (
        '(patient.reaction.reactionmeddrapt:"acute kidney injury"+OR+'
        'patient.reaction.reactionmeddraverse:"acute kidney injury")'
    ) in query
    # ...and the two groups joined by AND.
    assert ")+AND+(" in query


@pytest.mark.unit
def test_single_field_param_still_unparenthesized_but_valid():
    query = _captured_query({"medicinalproduct": "colistin"})
    assert (
        "(patient.drug.medicinalproduct:colistin+OR+"
        "patient.drug.openfda.generic_name:colistin)"
    ) in query
    # No stray AND when only one parameter is supplied.
    assert "+AND+" not in query
