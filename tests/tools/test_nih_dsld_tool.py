"""Tests for the NIH DSLD (Dietary Supplement Label Database) tool.

Supplements are a regulatory category distinct from FDA drug labels
(ToolUniverse's ~150 existing label tools), with no prior coverage. Tests
assert a real, known label survives the round trip rather than checking
response shape alone.
"""

import pytest
from tooluniverse import ToolUniverse


TRANSIENT = ("timed out", "Failed to connect", "HTTP 5")

VITAMIN_D_GUMMY = 20581


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
        assert "NIHDSLD_search_products" in names
        assert "NIHDSLD_get_label" in names


class TestSearchProducts:
    def test_finds_vitamin_d_products(self, tu):
        rows = data_of(tu.tools.NIHDSLD_search_products(query="vitamin d", limit=10))
        assert rows
        assert all(r["product_id"] for r in rows)

    def test_limit_is_respected(self, tu):
        rows = data_of(
            tu.tools.NIHDSLD_search_products(query="turmeric", limit=3)
        )
        assert len(rows) <= 3

    def test_unmatched_query(self, tu):
        result = tu.tools.NIHDSLD_search_products(query="zzzznotarealsupplement12345")
        assert result["status"] == "error"

    def test_missing_query(self, tu):
        assert tu.tools.NIHDSLD_search_products(query="")["status"] == "error"


class TestGetLabel:
    def test_vitamin_d_gummy_has_known_dose(self, tu):
        data = data_of(tu.tools.NIHDSLD_get_label(product_id=VITAMIN_D_GUMMY))
        assert data["name"] == "Vitamin D Gummy Vitamins"
        vitamin_d = next(
            i for i in data["ingredients"] if i["name"] == "Vitamin D"
        )
        assert vitamin_d["amount"] == 2000
        assert vitamin_d["unit"] == "IU"
        assert vitamin_d["percent_daily_value"] == 500

    def test_string_product_id_is_accepted(self, tu):
        result = tu.tools.NIHDSLD_get_label(product_id="20581")
        assert result["status"] == "success"

    def test_serving_size_is_included(self, tu):
        data = data_of(tu.tools.NIHDSLD_get_label(product_id=VITAMIN_D_GUMMY))
        assert data["serving_size"]["minQuantity"] == 2

    def test_unknown_product(self, tu):
        result = tu.tools.NIHDSLD_get_label(product_id=999999999)
        assert result["status"] == "error"

    def test_missing_product_id(self, tu):
        assert tu.tools.NIHDSLD_get_label(product_id="")["status"] == "error"


class TestErrorHandling:
    @pytest.mark.parametrize(
        "tool_name,kwargs",
        [
            ("NIHDSLD_search_products", {"query": ""}),
            ("NIHDSLD_get_label", {"product_id": ""}),
            ("NIHDSLD_get_label", {"product_id": 999999999}),
        ],
    )
    def test_returns_error_dict_not_exception(self, tu, tool_name, kwargs):
        result = getattr(tu.tools, tool_name)(**kwargs)
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert isinstance(result.get("error"), str) and result["error"]
