"""Tests for the codon usage table tool.

DNA_codon_optimize ships hardcoded tables for four species; this tool
supplies the reference data for any sequenced organism. Assertions check
known codon bias (CTG dominates human leucine, E. coli prefers GC-ending
codons at several positions) rather than response shape alone.
"""

import pytest
from tooluniverse import ToolUniverse


TRANSIENT = ("timed out", "Failed to connect", "HTTP 5")

HUMAN = 9606
ECOLI_K12 = 83333
YEAST = 4932


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
        assert "CodonUsage_get_table" in names
        assert "CodonUsage_get_optimal_codons" in names


class TestTable:
    def test_full_table_has_64_codons(self, tu):
        result = tu.tools.CodonUsage_get_table(taxid=HUMAN)
        rows = data_of(result)
        assert len(rows) == 64
        assert result["metadata"]["species"] == "Homo sapiens"

    def test_fractions_sum_to_one_per_amino_acid(self, tu):
        rows = data_of(tu.tools.CodonUsage_get_table(taxid=HUMAN))
        totals = {}
        for row in rows:
            totals.setdefault(row["amino_acid"], 0.0)
            totals[row["amino_acid"]] += row["fraction"]
        for amino_acid, total in totals.items():
            assert total == pytest.approx(1.0, abs=0.01), amino_acid

    def test_ctg_dominates_human_leucine(self, tu):
        rows = data_of(
            tu.tools.CodonUsage_get_table(taxid=HUMAN, amino_acid="Leu")
        )
        assert len(rows) == 6
        # Rows come back ordered by usage within the amino acid.
        assert rows[0]["codon"] == "CTG"
        assert rows[0]["fraction"] > 0.3

    def test_codons_use_dna_alphabet(self, tu):
        rows = data_of(tu.tools.CodonUsage_get_table(taxid=HUMAN))
        assert all(set(r["codon"]) <= set("ACGT") for r in rows)

    def test_species_level_taxid_without_a_table_explains_itself(self, tu):
        # E. coli tables are held at strain level: 83333, not 562.
        result = tu.tools.CodonUsage_get_table(taxid=562)
        assert result["status"] == "error"
        assert "83333" in result["error"]

    def test_unknown_amino_acid(self, tu):
        result = tu.tools.CodonUsage_get_table(taxid=HUMAN, amino_acid="Zzz")
        assert result["status"] == "error"


class TestOptimalCodons:
    def test_returns_twenty_amino_acids_by_default(self, tu):
        rows = data_of(tu.tools.CodonUsage_get_optimal_codons(taxid=HUMAN))
        assert len(rows) == 20
        assert all(r["amino_acid"] != "End" for r in rows)

    def test_stop_codons_included_on_request(self, tu):
        rows = data_of(
            tu.tools.CodonUsage_get_optimal_codons(
                taxid=HUMAN, include_stop_codons=True
            )
        )
        assert any(r["amino_acid"] == "End" for r in rows)

    def test_human_preferences_match_known_bias(self, tu):
        rows = data_of(tu.tools.CodonUsage_get_optimal_codons(taxid=HUMAN))
        preferred = {r["amino_acid"]: r["preferred_codon"] for r in rows}
        assert preferred["Leu"] == "CTG"
        assert preferred["Gly"] == "GGC"

    def test_ecoli_differs_from_human(self, tu):
        human = {
            r["amino_acid"]: r["preferred_codon"]
            for r in data_of(tu.tools.CodonUsage_get_optimal_codons(taxid=HUMAN))
        }
        ecoli = {
            r["amino_acid"]: r["preferred_codon"]
            for r in data_of(
                tu.tools.CodonUsage_get_optimal_codons(taxid=ECOLI_K12)
            )
        }
        differing = [aa for aa in human if human[aa] != ecoli.get(aa)]
        # Host preference differs substantially; this is why optimization exists.
        assert len(differing) >= 5, differing
        assert ecoli["Ala"] == "GCG"

    def test_yeast_table_available(self, tu):
        result = tu.tools.CodonUsage_get_optimal_codons(taxid=YEAST)
        assert result["metadata"]["species"] == "Saccharomyces cerevisiae"


class TestErrorHandling:
    @pytest.mark.parametrize(
        "tool_name,kwargs",
        [
            ("CodonUsage_get_table", {"taxid": ""}),
            ("CodonUsage_get_optimal_codons", {"taxid": ""}),
            ("CodonUsage_get_table", {"taxid": 999999999}),
        ],
    )
    def test_returns_error_dict_not_exception(self, tu, tool_name, kwargs):
        result = getattr(tu.tools, tool_name)(**kwargs)
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert isinstance(result.get("error"), str) and result["error"]
