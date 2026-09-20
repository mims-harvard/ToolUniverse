"""ODPHP tool schemas must not require parameters the tools treat as optional.

odphp_myhealthfinder required the boolean strip_html, odphp_topicsearch required
topicId, categoryId, keyword *and* strip_html (though its description says to search
by any one of them), and odphp_outlink_fetch required max_chars and return_html
(optional / defaulted in the code). A call with only the real inputs was rejected
with "'strip_html' is a required property".
"""

import json
from pathlib import Path

import jsonschema
import pytest

pytestmark = pytest.mark.unit

_DATA = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"
_TOOLS = {t["name"]: t for t in json.loads((_DATA / "odphp_tools.json").read_text())}


def _valid(tool, arguments):
    jsonschema.validate(arguments, _TOOLS[tool]["parameter"])


def test_myhealthfinder_accepts_demographics_without_strip_html():
    _valid(
        "odphp_myhealthfinder",
        {"lang": "en", "age": 35, "sex": "female", "pregnant": "yes"},
    )


@pytest.mark.parametrize(
    "extra",
    [{"keyword": "diabetes"}, {"topicId": "30544"}, {"categoryId": "15"}],
)
def test_topicsearch_accepts_any_single_search_key(extra):
    _valid("odphp_topicsearch", {"lang": "en", **extra})


def test_outlink_fetch_needs_only_urls():
    _valid("odphp_outlink_fetch", {"urls": ["https://health.gov/x"]})


def test_optional_flags_are_still_accepted_when_given():
    _valid(
        "odphp_myhealthfinder",
        {"lang": "en", "age": 1, "sex": "female", "pregnant": "no", "strip_html": True},
    )
    _valid(
        "odphp_outlink_fetch",
        {"urls": ["https://health.gov/x"], "max_chars": 2000, "return_html": False},
    )


def test_required_inputs_are_still_enforced():
    with pytest.raises(jsonschema.ValidationError):
        _valid("odphp_myhealthfinder", {"lang": "en", "age": 35})
    with pytest.raises(jsonschema.ValidationError):
        _valid("odphp_outlink_fetch", {})
