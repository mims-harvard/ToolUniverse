"""Tests for the SciCrunch RRID resolver tool.

ToolUniverse already has a richer, antibody-specific Antibody Registry
tool for the AB_ prefix (the majority of RRIDs). This tool resolves any
other prefix through SciCrunch's own registry. Tests assert a known
software RRID (SCR_002526, Stereo Investigator) resolves correctly, with
and without the RRID: prefix.
"""

import pytest
from tooluniverse import ToolUniverse


TRANSIENT = ("timed out", "Failed to connect", "HTTP 5")

STEREO_INVESTIGATOR = "SCR_002526"


@pytest.fixture(scope="module")
def tu():
    instance = ToolUniverse()
    instance.load_tools()
    return instance


def data_of(result):
    if result.get("status") == "error":
        error = str(result.get("error", ""))
        if any(t in error for t in TRANSIENT):
            pytest.skip(f"upstream temporarily unavailable: {error[:80]}")
        pytest.fail(f"unexpected error response: {error[:200]}")
    return result["data"]


class TestRegistration:
    def test_tools_load(self, tu):
        names = {t.get("name") for t in tu.all_tools if isinstance(t, dict)}
        assert "SciCrunch_resolve_rrid" in names


class TestResolveRrid:
    def test_known_software_rrid(self, tu):
        data = data_of(tu.tools.SciCrunch_resolve_rrid(rrid=STEREO_INVESTIGATOR))
        assert "Stereo Investigator" in data["name"]
        assert data["rrid"] == f"RRID:{STEREO_INVESTIGATOR}"
        assert "SCR_002526" in data["proper_citation"]

    def test_prefix_is_optional(self, tu):
        without_prefix = data_of(
            tu.tools.SciCrunch_resolve_rrid(rrid=STEREO_INVESTIGATOR)
        )
        with_prefix = data_of(
            tu.tools.SciCrunch_resolve_rrid(rrid=f"RRID:{STEREO_INVESTIGATOR}")
        )
        assert without_prefix["name"] == with_prefix["name"]

    def test_categories_are_included(self, tu):
        data = data_of(tu.tools.SciCrunch_resolve_rrid(rrid=STEREO_INVESTIGATOR))
        assert data["categories"]

    def test_unknown_rrid(self, tu):
        result = tu.tools.SciCrunch_resolve_rrid(rrid="NOTAREALRRID999")
        assert result["status"] == "error"

    def test_missing_rrid(self, tu):
        assert tu.tools.SciCrunch_resolve_rrid(rrid="")["status"] == "error"


class TestErrorHandling:
    @pytest.mark.parametrize(
        "tool_name,kwargs",
        [
            ("SciCrunch_resolve_rrid", {"rrid": ""}),
            ("SciCrunch_resolve_rrid", {"rrid": "NOTAREALRRID999"}),
        ],
    )
    def test_returns_error_dict_not_exception(self, tu, tool_name, kwargs):
        result = getattr(tu.tools, tool_name)(**kwargs)
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert isinstance(result.get("error"), str) and result["error"]
