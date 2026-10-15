"""Tools that always parse the response as JSON must not advertise ``format=xml``.

EBI Search called ``response.json()`` on whatever it got back, so ``format="xml"``
failed with ``EBI Search API error: Expecting value: line 1 column 1 (char 0)``.
IntAct ignored the value and returned JSON. Both now declare the one value they
can produce (the same convention as ``intact_get_interactions``).
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

DATA = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"


def _format_params(filename):
    for tool in json.loads((DATA / filename).read_text(encoding="utf-8")):
        fmt = tool["parameter"]["properties"].get("format")
        if fmt is not None:
            yield tool["name"], fmt


@pytest.mark.parametrize("filename", ["ebi_search_tools.json", "intact_tools.json"])
def test_format_param_only_offers_json(filename):
    seen = list(_format_params(filename))
    assert seen, f"{filename} no longer declares a format parameter; update this test"
    for name, fmt in seen:
        assert fmt["enum"] == ["json"], name
        assert fmt["default"] == "json", name
        assert "json" in fmt["description"], name
