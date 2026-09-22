"""WikiPathways_get_pathway's format='gpml' silently ran the JSON/SPARQL path.

The tool advertised a "format": "json"/"gpml" enum but the run() method never
read it, so a caller asking for the raw GPML XML got the same gene-list JSON
back with no error and no indication anything was wrong.
"""

from unittest.mock import patch
from urllib.error import HTTPError

import pytest

pytestmark = pytest.mark.unit


def _tool():
    from tooluniverse.wikipathways_tool import WikiPathwaysGetTool

    return WikiPathwaysGetTool({"settings": {"timeout": 30}})


def test_gpml_format_fetches_gpml_instead_of_running_sparql():
    with (
        patch(
            "tooluniverse.wikipathways_tool._fetch_gpml", return_value="<Pathway/>"
        ) as fetch,
        patch("tooluniverse.wikipathways_tool._sparql") as sparql,
    ):
        result = _tool().run({"wpid": "WP254", "format": "gpml"})
    assert result == {
        "status": "success",
        "data": {"wpid": "WP254", "format": "gpml", "gpml": "<Pathway/>"},
    }
    fetch.assert_called_once_with("WP254", timeout=30)
    sparql.assert_not_called()


def test_json_format_still_runs_sparql_not_gpml():
    with (
        patch("tooluniverse.wikipathways_tool._fetch_gpml") as fetch,
        patch(
            "tooluniverse.wikipathways_tool._sparql",
            return_value={"results": {"bindings": []}},
        ),
    ):
        result = _tool().run({"wpid": "WP254", "format": "json"})
    fetch.assert_not_called()
    assert (
        result["status"] == "error"
    )  # no bindings -> pathway not found, still SPARQL path


def test_missing_gpml_is_a_clear_error_not_a_stack_trace():
    error = HTTPError("url", 404, "Not Found", {}, None)
    with patch("tooluniverse.wikipathways_tool._fetch_gpml", side_effect=error):
        result = _tool().run({"wpid": "NOTREAL999", "format": "gpml"})
    assert result["status"] == "error"
    assert "404" in result["error"]
