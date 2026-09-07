"""Tests for the MolGlueDB tool.

MolGlueDB has no documented public API; its own frontend calls a
same-origin JSON backend that sits behind a WAF returning the SPA shell
(HTTP 200, not an error) to requests without a browser-like User-Agent
and Referer. These tests exercise the real backend, so they also guard
against that WAF behavior regressing silently -- if headers stopped
being enough, search results would come back empty/malformed rather
than erroring loudly.
"""

import pytest
from tooluniverse import ToolUniverse


TRANSIENT = ("timed out", "Failed to connect", "HTTP 5", "non-JSON")

IKZF2_COMPOUND_ID = 1


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
        assert "MolGlueDB_search_compounds" in names
        assert "MolGlueDB_get_compound" in names


class TestSearchCompounds:
    def test_target_keyword_returns_real_hits(self, tu):
        result = tu.tools.MolGlueDB_search_compounds(keyword="IKZF2", limit=10)
        rows = data_of(result)
        assert rows
        assert result["metadata"]["total_matching"] > 0
        assert any(r["PrimaryTarget"] == "IKZF2" for r in rows)

    def test_compound_name_keyword(self, tu):
        rows = data_of(tu.tools.MolGlueDB_search_compounds(keyword="Lenalidomide", limit=10))
        assert rows
        assert any("lenalidomide" in (r["Name"] or "").lower() for r in rows)

    def test_nonsense_keyword_returns_empty_not_full_dataset(self, tu):
        result = tu.tools.MolGlueDB_search_compounds(keyword="zzznonexistentxyz123")
        rows = data_of(result)
        assert rows == []
        assert result["metadata"]["total_matching"] == 0

    def test_limit_is_respected(self, tu):
        rows = data_of(tu.tools.MolGlueDB_search_compounds(keyword="CRBN", limit=3))
        assert len(rows) <= 3

    def test_missing_keyword(self, tu):
        result = tu.tools.MolGlueDB_search_compounds(keyword="")
        assert result["status"] == "error"


class TestGetCompound:
    def test_known_compound_id(self, tu):
        data = data_of(tu.tools.MolGlueDB_get_compound(compound_id=IKZF2_COMPOUND_ID))
        assert data["id"] == IKZF2_COMPOUND_ID
        assert data["PrimaryTarget"] == "IKZF2"
        assert data["SMILES"]

    def test_unknown_compound_id(self, tu):
        result = tu.tools.MolGlueDB_get_compound(compound_id=999999999)
        assert result["status"] == "error"

    def test_non_integer_compound_id(self, tu):
        result = tu.tools.MolGlueDB_get_compound(compound_id="not-a-number")
        assert result["status"] == "error"


class TestErrorHandling:
    @pytest.mark.parametrize(
        "tool_name,kwargs",
        [
            ("MolGlueDB_search_compounds", {"keyword": ""}),
            ("MolGlueDB_get_compound", {"compound_id": "bad"}),
        ],
    )
    def test_returns_error_dict_not_exception(self, tu, tool_name, kwargs):
        result = getattr(tu.tools, tool_name)(**kwargs)
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert isinstance(result.get("error"), str) and result["error"]
