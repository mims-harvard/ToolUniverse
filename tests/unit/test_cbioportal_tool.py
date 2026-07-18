"""Regression guard for Fix-R4A-001: CBioPortalRESTTool schema-default fill.

_build_url only substitutes {placeholder} for keys present in the call
arguments, so an omitted optional parameter (e.g. `limit`, which the JSON
schema declares default=20) left its literal "{limit}" placeholder unfilled
in the endpoint template -- sending a broken query string to the live API
instead of falling back to the declared default.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.cbioportal_tool import CBioPortalRESTTool

pytestmark = pytest.mark.unit


def _tool():
    return CBioPortalRESTTool(
        {
            "name": "cBioPortal_get_cancer_studies",
            "parameter": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 20},
                },
            },
            "fields": {"endpoint": "https://www.cbioportal.org/api/studies?pageSize={limit}"},
        }
    )


def test_omitted_param_uses_schema_default():
    tool = _tool()
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = [{"studyId": "x"}]

    with patch.object(tool.session, "get", return_value=resp) as mock_get:
        result = tool.run({})

    assert result["status"] == "success"
    called_url = mock_get.call_args.args[0]
    assert "{limit}" not in called_url
    assert "pageSize=20" in called_url


def test_explicit_param_overrides_default():
    tool = _tool()
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = [{"studyId": "x"}]

    with patch.object(tool.session, "get", return_value=resp) as mock_get:
        tool.run({"limit": 5})

    called_url = mock_get.call_args.args[0]
    assert "pageSize=5" in called_url
