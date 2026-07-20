"""Regression guard for Fix-R22B-2 (exact-match ranking) and Fix-R22B-3
(markup stripping) in SwissLipidsTool.

Fix-R22B-2: SwissLipids_search's upstream ordering buries an exact-name
match under derivative entries -- confirmed live that searching "cholesterol"
returns 87 cholesteryl-ester derivatives before the "cholesterol" entry
itself (SLM:000000287), so it never survived truncation to the tool's
default limit=10. Fixed by stable-sorting exact case-insensitive name
matches to the front before truncating.

Fix-R22B-3: SwissLipids embeds pseudo-XML stereodescriptor markup in entity
names, e.g. "<greek>alpha</greek>-<stereo>D</stereo>-glucosaminyl" -- passed
through unsanitized. Fixed by stripping the tag markers while keeping their
text content.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.swisslipids_tool import SwissLipidsTool

pytestmark = pytest.mark.unit

_CHOLESTEROL_SEARCH_HITS = [
    {
        "entity_id": "SLM:000500294",
        "entity_name": "docosanoyl-cholesterol",
        "entity_type": "Lipid",
        "classification_level": "Species",
    },
    {
        "entity_id": "SLM:000500267",
        "entity_name": "(15-methylhexadecanoyl)-cholesterol",
        "entity_type": "Lipid",
        "classification_level": "Species",
    },
    {
        "entity_id": "SLM:000000287",
        "entity_name": "cholesterol",
        "entity_type": "Lipid",
        "classification_level": "Species",
    },
]

_MARKUP_CHILDREN = [
    {
        "SLM:000010000": {
            "entity_id": "SLM:000010000",
            "entity_name": "a 6-(<greek>alpha</greek>-<stereo>D</stereo>-glucosaminyl)-1-phosphatidyl-1<stereo>D</stereo>-<stereo>myo</stereo>-inositol",
            "entity_type": "Lipid",
        }
    }
]


def _tool():
    return SwissLipidsTool({"name": "swisslipids_test", "fields": {}})


def _resp(json_body):
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = json_body
    return r


class TestExactMatchRanking:
    def test_exact_match_boosted_to_front_within_limit(self):
        tool = _tool()
        resp = _resp(_CHOLESTEROL_SEARCH_HITS)

        with patch("tooluniverse.swisslipids_tool.requests.get", return_value=resp):
            result = tool.run({"operation": "search", "query": "cholesterol", "limit": 2})

        assert result["status"] == "success"
        names = [r["entity_name"] for r in result["data"]]
        assert names[0] == "cholesterol"
        assert len(names) == 2

    def test_case_insensitive_match_still_boosted(self):
        tool = _tool()
        resp = _resp(_CHOLESTEROL_SEARCH_HITS)

        with patch("tooluniverse.swisslipids_tool.requests.get", return_value=resp):
            result = tool.run({"operation": "search", "query": "CHOLESTEROL", "limit": 1})

        assert result["data"][0]["entity_name"] == "cholesterol"

    def test_no_exact_match_preserves_original_order(self):
        tool = _tool()
        hits = _CHOLESTEROL_SEARCH_HITS[:2]  # no exact "cholesterol" entry
        resp = _resp(hits)

        with patch("tooluniverse.swisslipids_tool.requests.get", return_value=resp):
            result = tool.run({"operation": "search", "query": "cholesterol", "limit": 2})

        names = [r["entity_name"] for r in result["data"]]
        assert names == ["docosanoyl-cholesterol", "(15-methylhexadecanoyl)-cholesterol"]


class TestEntityNameMarkupStripped:
    def test_get_children_strips_greek_and_stereo_tags(self):
        tool = _tool()
        resp = _resp(_MARKUP_CHILDREN)

        with patch("tooluniverse.swisslipids_tool.requests.get", return_value=resp):
            result = tool.run({"operation": "get_children", "entity_id": "SLM:000001193"})

        assert result["status"] == "success"
        name = result["data"][0]["entity_name"]
        assert "<greek>" not in name
        assert "<stereo>" not in name
        assert name == "a 6-(alpha-D-glucosaminyl)-1-phosphatidyl-1D-myo-inositol"

    def test_search_result_names_also_cleaned(self):
        tool = _tool()
        hits = [
            {
                "entity_id": "SLM:000020000",
                "entity_name": "<stereo>D</stereo>-glucose",
                "entity_type": "Lipid",
                "classification_level": "Species",
            }
        ]
        resp = _resp(hits)

        with patch("tooluniverse.swisslipids_tool.requests.get", return_value=resp):
            result = tool.run({"operation": "search", "query": "glucose"})

        assert result["data"][0]["entity_name"] == "D-glucose"

    def test_none_name_passes_through_unchanged(self):
        tool = _tool()
        hits = [
            {
                "entity_id": "SLM:000030000",
                "entity_name": None,
                "entity_type": "Lipid",
                "classification_level": "Species",
            }
        ]
        resp = _resp(hits)

        with patch("tooluniverse.swisslipids_tool.requests.get", return_value=resp):
            result = tool.run({"operation": "search", "query": "x"})

        assert result["data"][0]["entity_name"] is None
