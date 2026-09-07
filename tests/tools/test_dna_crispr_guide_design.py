"""Tests for DNA_crispr_guide_design.

Nothing in ToolUniverse designed a CRISPR guide RNA before this. It is a
transparent rule-based heuristic (GC content, PAM-proximal G, terminator/
homopolymer avoidance), not a trained on-target efficiency model, and does
no off-target search against any genome -- both facts are asserted here so
a caller cannot mistake it for a validated predictor. Tests verify PAM
correctness and strand-mapping directly rather than trusting the scores.
"""

import pytest
from tooluniverse import ToolUniverse


GAPDH_FRAGMENT = (
    "GGAAGGTGAAGGTCGGAGTCAACGGATTTGGTCGTATTGGGCGCCTGGTCACCAGGGCTG"
    "CTTTTAACTCTGGTAAAGTGGATATTGTTGCCATCAATGACCCCTTCATTGACCTCAACT"
    "ACATGGTTTACATGTTCCAATATGATTCCACCCATGGCAAATTCCATGGCACCGTCAAGG"
    "CTGAGAACGGGAAGCTTGTCATCAATGGAAATCCCATCACCATCTTCCAGGAGCGAGATC"
    "CC"
)


@pytest.fixture(scope="module")
def tu():
    instance = ToolUniverse()
    instance.load_tools()
    return instance


class TestRegistration:
    def test_tool_loads(self, tu):
        names = {t.get("name") for t in tu.all_tools if isinstance(t, dict)}
        assert "DNA_crispr_guide_design" in names


class TestCandidateGeneration:
    def test_every_candidate_has_a_real_ngg_pam(self, tu):
        result = tu.tools.DNA_crispr_guide_design(
            sequence=GAPDH_FRAGMENT, limit=50
        )
        assert result["status"] == "success"
        rows = result["data"]
        assert rows
        for row in rows:
            assert row["pam"][1:] == "GG"
            assert len(row["protospacer"]) == 20

    def test_minus_strand_coordinates_map_back_correctly(self, tu):
        result = tu.tools.DNA_crispr_guide_design(
            sequence=GAPDH_FRAGMENT, limit=100
        )
        minus_hits = [r for r in result["data"] if r["strand"] == "-"]
        assert minus_hits
        for row in minus_hits:
            region = GAPDH_FRAGMENT[row["start"] : row["end"]]
            full_site = row["protospacer"] + row["pam"]
            # The minus-strand site, reverse-complemented, must equal the
            # plus-strand region at the reported coordinates exactly.
            complement = str.maketrans("ACGT", "TGCA")
            revcomp = full_site.translate(complement)[::-1]
            assert revcomp == region

    def test_results_sorted_by_score_descending(self, tu):
        result = tu.tools.DNA_crispr_guide_design(
            sequence=GAPDH_FRAGMENT, limit=20
        )
        scores = [r["heuristic_score"] for r in result["data"]]
        assert scores == sorted(scores, reverse=True)

    def test_gc_filter_is_honored_when_matches_exist(self, tu):
        result = tu.tools.DNA_crispr_guide_design(
            sequence=GAPDH_FRAGMENT, gc_min=45, gc_max=55, limit=50
        )
        assert result["status"] == "success"
        assert all(
            45 <= r["gc_content_percent"] <= 55 for r in result["data"]
        )

    def test_limit_is_respected(self, tu):
        result = tu.tools.DNA_crispr_guide_design(sequence=GAPDH_FRAGMENT, limit=3)
        assert len(result["data"]) <= 3

    def test_metadata_discloses_heuristic_nature(self, tu):
        result = tu.tools.DNA_crispr_guide_design(sequence=GAPDH_FRAGMENT, limit=1)
        note = result["metadata"]["note"].lower()
        assert "not a trained" in note
        assert "off-target" in note


class TestErrorHandling:
    @pytest.mark.parametrize(
        "kwargs",
        [
            {"sequence": ""},
            {"sequence": "ATCG"},
            {"sequence": "ATCGATCGATCGATCGATCGATCGN"},
            {"sequence": "ATATATATATATATATATATATATATAT"},
            {"sequence": "A" * 30, "gc_min": 80, "gc_max": 20},
        ],
    )
    def test_returns_error_dict_not_exception(self, tu, kwargs):
        result = tu.tools.DNA_crispr_guide_design(**kwargs)
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert isinstance(result.get("error"), str) and result["error"]
