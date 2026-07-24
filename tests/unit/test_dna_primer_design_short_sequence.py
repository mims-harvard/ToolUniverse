"""Regression guard for Fix-R22C-1: DNA_primer_design's error message when a
short input sequence can't yield a large enough product didn't reference the
tool's own documented "at least 200 bp" guidance, leaving a user unable to
connect the generic "Designed product size (N bp) is outside the range"
failure to the actual root cause. Confirmed live with a real 111bp GFP
fragment (below the documented minimum) that the message previously gave no
hint about sequence length at all. Fixed by appending a length-aware hint
when the failure is caused by too-small a product on a sub-200bp template.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.dna_tools import DNATool

pytestmark = pytest.mark.unit

_SHORT_SEQUENCE = (
    "ATGCGTAAAGGAGAAGAACTTTTCACTGGAGTTGTCCCAATTCTTGTTGAATTAGATGGT"
    "GATGTTAATGGGCACAAATTTTCTGTCAGTGGAGAGGGTGAAGGTGATGCA"
)

_LONG_SEQUENCE = (
    "ATGAGTAAAGGAGAAGAACTTTTCACTGGAGTTGTCCCAATTCTTGTTGAATTAGATGGT"
    "GATGTTAATGGGCACAAATTTTCTGTCAGTGGAGAGGGTGAAGGTGATGCAACATACGGA"
    "AAACTTACCCTTAAATTTATTTGCACTACTGGAAAACTACCTGTTCCATGGCCAACACT"
    "TGTCACTACTTTCTCTTATGGTGTTCAATGCTTTTCAAGATACCCAGATCATATGAAAC"
    "AGCATGACTTTTTCAAGAGTGCCATGCCCGAAGGTTATGTACAGGAAAGAACTATATTT"
    "TTCAAAGATGACGGGAACTACAAGACACGTGCTGAAGTCAAGTTTGAAGGTGATACCCT"
    "TGTTAATAGAATCGAGTTAAAAGGTATTGATTTTAAAGAAGATGGAAACATTCTTGGAC"
    "ACAAATTGGAATACAACTATAACTCACACAATGTATACATCATGGCAGACAAACAAAA"
    "GAATGGAATCAAAGTTAACTTCAAAATTAGACACAACATTGAAGATGGAAGCGTTCAAC"
    "TAGCAGACCATTATCAACAAAATACTCCAATTGGCGATGGCCCTGTCCTTTTACCAGAC"
    "AACCATTACCTGTCCACACAATCTGCCCTTTCGAAAGATCCCAACGAAAAGAGAGACCA"
    "CATGGTCCTTCTTGAGTTTGTAACAGCTGCTGGGATTACACATGGCATGGATGAACTAT"
    "ACAAATAA"
)


def _tool():
    return DNATool({"name": "dna_test", "parameter": {}})


class TestPrimerDesignShortSequenceHint:
    def test_short_sequence_error_mentions_length_and_200bp_guidance(self):
        tool = _tool()
        result = tool.run(
            {"operation": "primer_design", "sequence": _SHORT_SEQUENCE}
        )

        assert result["status"] == "error"
        assert f"{len(_SHORT_SEQUENCE)} bp" in result["error"]
        assert "200 bp" in result["error"]

    def test_long_sequence_still_succeeds(self):
        tool = _tool()
        result = tool.run(
            {"operation": "primer_design", "sequence": _LONG_SEQUENCE}
        )

        assert result["status"] == "success"
        assert result["data"]["product_size"] >= 100

    def test_hint_absent_when_sequence_already_long(self):
        """The 200bp hint should only fire for genuinely short templates --
        a >=200bp sequence that fails for an unrelated reason (e.g.
        product_size_max set too low) shouldn't get a misleading hint."""
        tool = _tool()
        result = tool.run(
            {
                "operation": "primer_design",
                "sequence": _LONG_SEQUENCE,
                "product_size_min": 5000,
                "product_size_max": 6000,
            }
        )

        assert result["status"] == "error"
        assert "200 bp" not in result["error"]
