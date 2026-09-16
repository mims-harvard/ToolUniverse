"""Cellosaurus search must use Solr rows/start, not size/offset."""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.cellosaurus_tool import CellosaurusSearchTool

pytestmark = pytest.mark.unit


def test_search_sends_rows_and_start_instead_of_size_and_offset():
    tool = CellosaurusSearchTool({"name": "cellosaurus_search_cell_lines"})
    payload = {
        "Cellosaurus": {
            "cell-line-list": [
                {"accession-list": [{"value": "CVCL_0030"}]},
                {"accession-list": [{"value": "CVCL_1276"}]},
            ]
        }
    }
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None

    with patch(
        "tooluniverse.cellosaurus_tool.requests.get", return_value=response
    ) as get:
        result = tool.run({"q": "HeLa", "size": 2, "offset": 2})

    get.assert_called_once()
    params = get.call_args.kwargs["params"]
    assert params == {"q": "HeLa", "start": 2, "rows": 2}
    assert "size" not in params
    assert "offset" not in params
    assert result["success"] is True
    assert result["results"]["size"] == 2
    assert result["results"]["offset"] == 2
    assert len(result["results"]["cell_lines"]) == 2
