"""Regression guard for Fix-R22B-1: OpenCRAVAT_list_annotators' `category`
filter only matched against each module's `type` field. Confirmed live that
every one of the 182+ modules on the current OpenCRAVAT server shares the
single type value "annotator" -- so `category` could only ever match
everything or nothing, making it useless for the natural use case (finding
a specific annotator like "clinvar" or "sift" by name). Fixed by also
matching against `name`/`title`.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.opencravat_tool import OpenCRAVATTool

pytestmark = pytest.mark.unit

_ANNOTATORS = {
    "clinvar": {"title": "ClinVar", "description": "ClinVar annotations", "type": "annotator"},
    "clinvar_acmg": {"title": "ClinVar ACMG", "description": "ACMG prediction", "type": "annotator"},
    "sift": {"title": "SIFT", "description": "SIFT deleteriousness score", "type": "annotator"},
    "gnomad3": {"title": "gnomAD3", "description": "Population frequencies", "type": "annotator"},
}


def _tool():
    return OpenCRAVATTool(
        {"name": "opencravat_test", "fields": {"operation": "list_annotators"}}
    )


def _resp(json_body):
    r = MagicMock()
    r.json.return_value = json_body
    r.raise_for_status = MagicMock()
    return r


class TestCategoryFilterMatchesNameAndTitle:
    def test_name_substring_finds_matching_annotators(self):
        tool = _tool()
        resp = _resp(_ANNOTATORS)

        with patch("tooluniverse.opencravat_tool.requests.get", return_value=resp):
            result = tool.run({"category": "clinvar"})

        assert result["status"] == "success"
        names = {a["name"] for a in result["data"]}
        assert names == {"clinvar", "clinvar_acmg"}

    def test_title_substring_finds_matching_annotator(self):
        tool = _tool()
        resp = _resp(_ANNOTATORS)

        with patch("tooluniverse.opencravat_tool.requests.get", return_value=resp):
            result = tool.run({"category": "SIFT"})

        assert result["status"] == "success"
        assert [a["name"] for a in result["data"]] == ["sift"]

    def test_type_substring_still_matches_everything(self):
        tool = _tool()
        resp = _resp(_ANNOTATORS)

        with patch("tooluniverse.opencravat_tool.requests.get", return_value=resp):
            result = tool.run({"category": "annotator"})

        assert result["status"] == "success"
        assert len(result["data"]) == 4

    def test_no_category_returns_all_sorted_by_name(self):
        tool = _tool()
        resp = _resp(_ANNOTATORS)

        with patch("tooluniverse.opencravat_tool.requests.get", return_value=resp):
            result = tool.run({})

        assert result["status"] == "success"
        names = [a["name"] for a in result["data"]]
        assert names == sorted(names)
        assert len(names) == 4

    def test_no_match_returns_empty_list(self):
        tool = _tool()
        resp = _resp(_ANNOTATORS)

        with patch("tooluniverse.opencravat_tool.requests.get", return_value=resp):
            result = tool.run({"category": "nonexistent_xyz"})

        assert result["status"] == "success"
        assert result["data"] == []
