"""MediaDive_get_ingredient: the usage counts must be described correctly.

used_in_media_count counts the returned sample (at most 20 medium ids) and
total_used_in_media_sample is how many media use the ingredient. The note
still called used_in_media_count "the true total" (Peptone: 20 vs 310), and
the return_schema did not list the total field.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.mediadive_tool import MediaDiveTool

pytestmark = pytest.mark.unit


def _config():
    with open("src/tooluniverse/data/mediadive_tools.json") as fh:
        return next(t for t in json.load(fh) if t["name"] == "MediaDive_get_ingredient")


def _run():
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "data": {"id": 1, "name": "Peptone", "media": list(range(310))}
    }
    with patch("tooluniverse.mediadive_tool.requests.get", return_value=response):
        return MediaDiveTool(_config()).run({"ingredient_id": 1})


def test_counts_and_note_agree():
    result = _run()
    data = result["data"]
    assert data["used_in_media_count"] == 20 == len(data["used_in_media_sample"])
    assert data["total_used_in_media_sample"] == 310
    note = result["metadata"]["note"]
    assert "used_in_media_count is the true total" not in note
    assert "total_used_in_media_sample" in note


def test_return_schema_lists_the_total_field():
    properties = _config()["return_schema"]["oneOf"][0]["properties"]
    assert properties["total_used_in_media_sample"] == {"type": "integer"}
    assert set(_run()["data"]) <= set(properties)
