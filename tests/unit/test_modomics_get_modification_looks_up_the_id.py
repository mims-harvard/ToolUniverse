"""MODOMICS_get_modification returned the same record for every ID.

MODOMICS's /modifications/{mod_id} endpoint ignores the path segment and always
answers with the full ~433-entry catalog (confirmed live: ids 78, 2 and 58 all
returned the identical 433-key dict), so taking `list(data.values())[0]`
silently returned modification 2 regardless of which ID was requested.
"""

from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit

CATALOG = {
    "2": {"id": 2, "name": "5,2'-O-dimethylcytidine", "short_name": "Cm"},
    "78": {
        "id": 78,
        "name": "5-methylaminomethyl-2-selenouridine",
        "short_name": "mnm5se2U",
    },
}


def _tool():
    from tooluniverse.modomics_tool import MODOMICSTool

    return MODOMICSTool(
        {
            "name": "MODOMICS_get_modification",
            "fields": {"endpoint_type": "get_modification"},
        }
    )


def _response(payload):
    class R:
        status_code = 200

        def json(self):
            return payload

    return R()


def test_requested_id_is_looked_up_not_defaulted_to_the_first_entry():
    with patch(
        "tooluniverse.modomics_tool.requests.get", return_value=_response(CATALOG)
    ):
        result = _tool().run({"modification_id": 78})
    assert result["status"] == "success"
    assert result["data"]["name"] == "5-methylaminomethyl-2-selenouridine"


def test_different_ids_return_different_records():
    with patch(
        "tooluniverse.modomics_tool.requests.get", return_value=_response(CATALOG)
    ):
        first = _tool().run({"modification_id": 2})
        second = _tool().run({"modification_id": 78})
    assert first["data"]["name"] != second["data"]["name"]


def test_id_missing_from_the_catalog_is_an_error_not_the_first_entry():
    with patch(
        "tooluniverse.modomics_tool.requests.get", return_value=_response(CATALOG)
    ):
        result = _tool().run({"modification_id": 999999})
    assert result["status"] == "error"
    assert "999999" in result["error"]
