"""Tests for the PDBTM tool.

PDBTM is the third independent view alongside the already-shipped OPM
(geometry/energetics) and TopDB (curated per-region evidence): per-chain
classification computed directly from structure coordinates. Tests assert
known biology: porin (2POR) is a 16-stranded beta-barrel, and the
photosynthetic reaction centre (1PRC) has a non-membrane H subunit
alongside the membrane-embedded L and M subunits.
"""

import pytest
from tooluniverse import ToolUniverse


TRANSIENT = ("timed out", "Failed to connect", "HTTP 5")

PORIN = "2por"
REACTION_CENTRE = "1prc"


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
        assert "PDBTM_get_topology" in names


class TestGetTopology:
    def test_porin_is_a_beta_barrel(self, tu):
        data = data_of(tu.tools.PDBTM_get_topology(pdb_id=PORIN))
        assert data["chains"]
        assert all(c["tm_type"] == "beta" for c in data["chains"])
        assert all(c["num_tm_segments"] == 16 for c in data["chains"])

    def test_reaction_centre_has_one_non_membrane_subunit(self, tu):
        data = data_of(tu.tools.PDBTM_get_topology(pdb_id=REACTION_CENTRE))
        by_chain = {c["chain_label"]: c for c in data["chains"]}
        assert by_chain["A"]["tm_type"] == "non_tm"
        assert by_chain["A"]["is_membrane_embedded"] is False
        assert by_chain["B"]["num_tm_segments"] == 5
        assert by_chain["B"]["is_membrane_embedded"] is True

    def test_case_insensitive_pdb_id(self, tu):
        result = tu.tools.PDBTM_get_topology(pdb_id="2POR")
        assert result["status"] == "success"

    def test_unknown_pdb_id(self, tu):
        result = tu.tools.PDBTM_get_topology(pdb_id="notarealid")
        assert result["status"] == "error"

    def test_missing_pdb_id(self, tu):
        assert tu.tools.PDBTM_get_topology(pdb_id="")["status"] == "error"


class TestErrorHandling:
    @pytest.mark.parametrize(
        "tool_name,kwargs",
        [
            ("PDBTM_get_topology", {"pdb_id": ""}),
            ("PDBTM_get_topology", {"pdb_id": "notarealid"}),
        ],
    )
    def test_returns_error_dict_not_exception(self, tu, tool_name, kwargs):
        result = getattr(tu.tools, tool_name)(**kwargs)
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert isinstance(result.get("error"), str) and result["error"]
