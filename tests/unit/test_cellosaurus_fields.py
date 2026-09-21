"""`fields` must trim the record instead of emptying it."""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.cellosaurus_tool import CELLOSAURUS_FIELDS

pytestmark = pytest.mark.unit

# What the API actually returns for fields=id,ox,ca -- JSON response keys, not
# the query abbreviations that were sent.
TRIMMED = {
    "Cellosaurus": {
        "cell-line-list": [
            {
                "category": "Cancer cell line",
                "name-list": [{"type": "identifier", "value": "HeLa"}],
                "species-list": [{"accession": "9606"}],
            }
        ]
    }
}


def _response(payload):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    return response


def _info_tool():
    from tooluniverse.cellosaurus_tool import CellosaurusGetCellLineInfoTool

    return CellosaurusGetCellLineInfoTool(
        {"name": "cellosaurus_get_cell_line_info", "type": "x"}
    )


def test_documented_example_returns_data():
    """{"accession":"CVCL_0030","fields":["id","ox","char"]} used to give {}."""
    with patch(
        "tooluniverse.cellosaurus_tool.requests.get", return_value=_response(TRIMMED)
    ):
        result = _info_tool().run(
            {"accession": "CVCL_0030", "fields": ["id", "ox", "char"]}
        )

    assert result["success"] is True
    assert result["data"], "field filtering emptied the record"
    assert "name-list" in result["data"]


def test_fields_are_sent_to_the_api():
    with patch(
        "tooluniverse.cellosaurus_tool.requests.get", return_value=_response(TRIMMED)
    ) as get:
        _info_tool().run({"accession": "CVCL_0030", "fields": ["id", "ac"]})

    assert get.call_args.kwargs["params"]["fields"] == "id,ac"


def test_unknown_field_is_still_rejected():
    with patch("tooluniverse.cellosaurus_tool.requests.get") as get:
        result = _info_tool().run({"accession": "CVCL_0030", "fields": ["nope"]})
    assert result["status"] == "error"
    get.assert_not_called()


def test_field_abbreviations_are_shared_not_duplicated():
    for tag in ("id", "ac", "ox", "ca", "char"):
        assert tag in CELLOSAURUS_FIELDS
