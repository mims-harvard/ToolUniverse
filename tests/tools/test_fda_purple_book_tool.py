"""Tests for the FDA Purple Book tool.

There is no JSON API for the Purple Book, only monthly CSV snapshots at
a discoverable (but not reliably-cased) URL. Per FDA's own download-page
documentation, each monthly file's second section is a complete current
snapshot of the whole database, not just that month's changes -- these
tests confirm that section is parsed (not the top "changes" section) by
checking that products unrelated to any given month's changes are still
findable, and that known reference/biosimilar/interchangeable
relationships resolve correctly.
"""

import pytest
from tooluniverse import ToolUniverse


TRANSIENT = ("timed out", "Failed to connect", "HTTP 5", "Failed to reach", "Failed to download")


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
    def test_tool_loads(self, tu):
        names = {t.get("name") for t in tu.all_tools if isinstance(t, dict)}
        assert "FDAPurpleBook_search_products" in names


class TestSearchProducts:
    def test_reference_product_found_by_generic_name(self, tu):
        rows = data_of(tu.tools.FDAPurpleBook_search_products(proper_name="adalimumab", limit=100))
        assert rows
        names = {r["proprietary_name"] for r in rows}
        assert "Humira" in names

    def test_biosimilar_resolves_to_reference_product(self, tu):
        rows = data_of(
            tu.tools.FDAPurpleBook_search_products(
                reference_product_proprietary_name="Humira", limit=100
            )
        )
        assert rows
        # Every hit must actually reference Humira, and license_type must
        # mark it as a biosimilar/interchangeable, not the 351(a) itself.
        assert all("humira" in (r["reference_product_proprietary_name"] or "").lower() for r in rows)
        assert any("351(k)" in (r["license_type"] or "") for r in rows)

    def test_interchangeable_filter_excludes_plain_biosimilars(self, tu):
        rows = data_of(
            tu.tools.FDAPurpleBook_search_products(
                reference_product_proprietary_name="Humira",
                license_type="interchangeable",
                limit=100,
            )
        )
        assert rows
        assert all("interchangeable" in (r["license_type"] or "").lower() for r in rows)

    def test_applicant_and_license_type_combine(self, tu):
        rows = data_of(
            tu.tools.FDAPurpleBook_search_products(
                applicant="AbbVie", license_type="351(a)", limit=200
            )
        )
        assert rows
        assert all("abbvie" in (r["applicant"] or "").lower() for r in rows)
        assert all(r["license_type"] == "351(a)" for r in rows)

    def test_limit_is_respected(self, tu):
        rows = data_of(tu.tools.FDAPurpleBook_search_products(applicant="AbbVie", limit=3))
        assert len(rows) <= 3

    def test_unknown_bla_number_returns_empty(self, tu):
        rows = data_of(tu.tools.FDAPurpleBook_search_products(bla_number="999999999"))
        assert rows == []

    def test_no_filter_provided(self, tu):
        result = tu.tools.FDAPurpleBook_search_products()
        assert result["status"] == "error"


class TestErrorHandling:
    def test_returns_error_dict_not_exception(self, tu):
        result = tu.tools.FDAPurpleBook_search_products()
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert isinstance(result.get("error"), str) and result["error"]
