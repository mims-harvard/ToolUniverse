"""EOL_get_collection returned collection 1 regardless of collection_id.

EOL's collections endpoint takes the ID in the URL path (/collections/{id}.json);
the tool sent it as a query parameter (/collections/1.0.json?id=176) instead, so
every collection_id returned collection 1, "Fingertip Fauna" (confirmed live:
id=176, id=55869 and no id at all all gave that response, while
/collections/2.0.json?id=176 returned collection 2 -- the path segment decides
the result, not the query string).
"""

from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


def _tool():
    from tooluniverse.eol_tool import EOLTool

    return EOLTool(
        {"name": "EOL_get_collection", "fields": {"endpoint": "collections"}}
    )


def _fake_get(collections):
    def get(url, timeout=30):
        for cid, payload in collections.items():
            if f"/collections/{cid}.json" in url:
                return payload
        raise AssertionError(f"unexpected URL: {url}")

    return get


def test_collection_id_selects_the_url_path_not_a_query_parameter():
    collections = {
        4: {"name": "Backyard Animals in CT"},
        100: {"name": "Gulf of Mexico Sea Turtles"},
    }
    with patch(
        "tooluniverse.eol_tool._eol_http_get", side_effect=_fake_get(collections)
    ):
        result = _tool().run({"collection_id": 100})
    assert result["status"] == "success"
    assert result["data"]["name"] == "Gulf of Mexico Sea Turtles"


def test_id_is_never_sent_as_a_query_parameter():
    seen = {}

    def get(url, timeout=30):
        seen["url"] = url
        return {"name": "x"}

    with patch("tooluniverse.eol_tool._eol_http_get", side_effect=get):
        _tool().run({"collection_id": 176, "page": 2, "per_page": 5})
    assert "/collections/176.json?" in seen["url"]
    assert "id=" not in seen["url"]
    assert "page=2" in seen["url"] and "per_page=5" in seen["url"]
