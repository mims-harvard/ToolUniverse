"""Regression guard for Fix-R26E-1: ProtParam_calculate's molecular_weight_da
was systematically 18.02 Da too high for every sequence -- exactly one
water molecule's mass, regardless of sequence length. Root cause: _calc_mw
added _WATER_MW once before the per-residue loop (correct, to convert the
loop's per-residue "free amino acid mass minus water" terms into a proper
peptide-bond-aware sum) but then added it again after the loop, a second,
unwanted water. Confirmed live against known references: ACDEFGHIK should
be 1019.14 Da (was 1037.15) and human lysozyme C (148 aa) should be
~16537 Da (was 16554.97).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.protparam_tool import ProtParamTool

pytestmark = pytest.mark.unit

_LYSOZYME = (
    "MKALIVLGLVLLSVTVQGKVFERCELARTLKRLGMDGYRGISLANWMCLAKWESGYNTRATNYNAGDRST"
    "DYGIFQINSRYWCNDGKTPGAVNACHLSCSALLQDNIADAVACAKRVVRDPQGIRAWVAWRNRCQNRDVR"
    "QYVQGCGV"
)


def _tool():
    return ProtParamTool()


class TestMolecularWeight:
    def test_short_peptide_matches_known_reference(self):
        tool = _tool()
        result = tool.run({"sequence": "ACDEFGHIK"})

        assert result["status"] == "success"
        assert result["data"]["molecular_weight_da"] == pytest.approx(1019.14, abs=0.05)

    def test_lysozyme_matches_uniprot_reference_mass(self):
        tool = _tool()
        result = tool.run({"sequence": _LYSOZYME})

        assert result["status"] == "success"
        # UniProt P61626 records 16537 Da for this sequence.
        assert result["data"]["molecular_weight_da"] == pytest.approx(16537, abs=0.5)

    def test_dipeptide_equals_two_free_masses_minus_one_water(self):
        tool = _tool()
        result = tool.run({"sequence": "AA"})

        # One peptide bond forms between the two alanines, losing exactly
        # one water relative to the sum of the two free amino acid masses
        # (89.0935 * 2 - 18.01524 = 160.17176). The double-water bug would
        # instead have subtracted zero waters (or added one back), landing
        # on 178.19 or 196.20 instead.
        assert result["data"]["molecular_weight_da"] == pytest.approx(160.17, abs=0.01)
