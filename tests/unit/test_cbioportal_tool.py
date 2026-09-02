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


class TestMolecularProfileIdResolution:
    """Regression guard for Fix-Round3-003: a confirmed-nonexistent
    study_id must be reported immediately, not deferred to a confusing
    404 several steps later at the actual mutations/CNA fetch call.
    Covers both _get_mutation_profile_id and _get_cna_profile_id, which
    share this behavior via _resolve_molecular_profile_id."""

    def test_mutation_profile_id_returns_none_for_unknown_study(self):
        tool = _tool()
        resp = MagicMock()
        resp.status_code = 404
        with patch.object(tool.session, "get", return_value=resp):
            assert tool._get_mutation_profile_id("not-a-real-study") is None

    def test_cna_profile_id_returns_none_for_unknown_study(self):
        tool = _tool()
        resp = MagicMock()
        resp.status_code = 404
        with patch.object(tool.session, "get", return_value=resp):
            assert tool._get_cna_profile_id("not-a-real-study") is None

    def test_mutation_profile_id_found_when_study_exists(self):
        tool = _tool()
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = [
            {"molecularAlterationType": "MUTATION_EXTENDED", "molecularProfileId": "x_mutations"},
        ]
        with patch.object(tool.session, "get", return_value=resp):
            assert tool._get_mutation_profile_id("real_study") == "x_mutations"

    def test_mutation_profile_id_falls_back_to_guess_when_study_has_no_profile(self):
        """Study exists (200) but has no MUTATION_EXTENDED profile listed --
        keep the previous best-effort naming-convention guess rather than
        failing, since this is a different (rarer) situation than a
        nonexistent study."""
        tool = _tool()
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = [{"molecularAlterationType": "COPY_NUMBER_ALTERATION"}]
        with patch.object(tool.session, "get", return_value=resp):
            assert tool._get_mutation_profile_id("real_study") == "real_study_mutations"
