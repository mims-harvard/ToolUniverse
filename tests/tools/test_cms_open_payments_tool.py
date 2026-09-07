"""Tests for the CMS Open Payments tool.

ToolUniverse had no health-economics / conflict-of-interest layer; Open
Payments is the "Sunshine Act" database of manufacturer payments to
physicians. Most tests use the npi and manufacturer_id filters (indexed,
1-3s); one test confirms the exact-match name path also works, which is
unindexed and measured at roughly 25s during development.
"""

import pytest
from tooluniverse import ToolUniverse


TRANSIENT = ("timed out", "Failed to connect", "HTTP 5")

KNOWN_NPI = "1528271848"
KNOWN_MANUFACTURER_ID = "100000010419"


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
        assert "CMSOpenPayments_search_payments" in names


class TestSearchByNpi:
    def test_finds_known_physician_payments(self, tu):
        rows = data_of(
            tu.tools.CMSOpenPayments_search_payments(npi=KNOWN_NPI, limit=10)
        )
        assert rows
        assert all(r["recipient_npi"] == KNOWN_NPI for r in rows)

    def test_defaults_to_2024(self, tu):
        result = tu.tools.CMSOpenPayments_search_payments(npi=KNOWN_NPI, limit=1)
        assert result["metadata"]["program_year"] == 2024

    def test_program_year_is_honored(self, tu):
        result = tu.tools.CMSOpenPayments_search_payments(
            npi=KNOWN_NPI, program_year=2019, limit=1
        )
        data_of(result)
        assert result["metadata"]["program_year"] == 2019

    def test_limit_is_respected(self, tu):
        rows = data_of(
            tu.tools.CMSOpenPayments_search_payments(npi=KNOWN_NPI, limit=3)
        )
        assert len(rows) <= 3

    def test_unknown_npi(self, tu):
        result = tu.tools.CMSOpenPayments_search_payments(npi="9999999999")
        assert result["status"] == "error"


class TestSearchByManufacturer:
    def test_finds_manufacturer_payments(self, tu):
        rows = data_of(
            tu.tools.CMSOpenPayments_search_payments(
                manufacturer_id=KNOWN_MANUFACTURER_ID, limit=10
            )
        )
        assert rows
        assert all(r["manufacturer_id"] == KNOWN_MANUFACTURER_ID for r in rows)

    @pytest.mark.timeout(90)
    def test_exact_name_match_also_works(self, tu):
        # Unindexed text-column match; measured at ~25s during development.
        rows = data_of(
            tu.tools.CMSOpenPayments_search_payments(
                manufacturer_name="Phadia US Inc.", limit=3
            )
        )
        assert rows


class TestErrorHandling:
    def test_no_filter_provided(self, tu):
        result = tu.tools.CMSOpenPayments_search_payments(npi="")
        assert result["status"] == "error"

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"npi": "9999999999"},
        ],
    )
    def test_returns_error_dict_not_exception(self, tu, kwargs):
        result = tu.tools.CMSOpenPayments_search_payments(**kwargs)
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert isinstance(result.get("error"), str) and result["error"]
