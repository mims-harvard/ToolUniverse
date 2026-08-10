"""Golden Gate reactions were only supported in the design direction. The reverse
question -- "I combined these plasmids with Esp3I; what does the product contain?"
-- had no tool, so it was answered by hand-writing a digestion/ligation simulator.

`golden_gate_assemble` digests each input, drops fragments that keep a recognition
site (they are re-cut in the reaction and cannot persist), and chains the rest by
matching each fragment's right-hand overhang to the next fragment's left-hand
overhang until the product closes.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.dna_tools import DNATool

pytestmark = pytest.mark.unit

ASSEMBLE = {
    "name": "DNA_golden_gate_assemble",
    "type": "DNATool",
    "fields": {"operation": "golden_gate_assemble"},
}


_COMPLEMENT = str.maketrans("ACGT", "TGCA")


def _rc(seq):
    return seq.translate(_COMPLEMENT)[::-1]


def _donor(ov_left, ov_right, body, backbone):
    """A circular donor with inward-facing BsaI sites flanking `body`.

    Cutting releases `body` (site-free, so it survives the reaction) and leaves
    the recognition sites on the backbone piece.

    `ov_left`/`ov_right` are the overhang identities in the standard
    Golden-Gate/MoClo notation used by `DNA_golden_gate_design` -- the same
    4-letter code is shared by both mating ends of a junction. The right-hand
    site is inward-facing (reverse-oriented, GAGACC on this strand), so BsaI
    reads it on the bottom strand; the literal top-strand text immediately
    before that site is therefore the *reverse complement* of `ov_right`, not
    `ov_right` itself (mirrors `DNA_golden_gate_design`'s own construction).
    """
    return "GGTCTC" "A" + ov_left + body + _rc(ov_right) + "A" "GAGACC" + backbone


DONOR_A = _donor("AGGT", "CATC", "GGGGCCCCGGGGCCCCAAAA", "ACGTACGTACGTACGTACGTACGTAC")
DONOR_B = _donor("CATC", "AGGT", "CCCCGGGGCCCCGGGGTTTT", "TGCATGCATGCATGCATGCATGCATG")


def test_two_donors_assemble_into_a_circle():
    result = DNATool(ASSEMBLE).run(
        {"fragments": [DONOR_A, DONOR_B], "enzyme": "BsaI", "circular": True}
    )
    assert result["status"] == "success", result.get("error")
    data = result["data"]
    assert data["num_fragments_assembled"] == 2
    assert data["product_length"] == 48  # both inserts, backbones discarded
    assert data["is_circular"] is True


def test_product_carries_no_recognition_site():
    """A correct Golden Gate product cannot be re-cut by the assembly enzyme."""
    data = DNATool(ASSEMBLE).run(
        {"fragments": [DONOR_A, DONOR_B], "enzyme": "BsaI"}
    )["data"]
    product = data["product_sequence"]
    assert "GGTCTC" not in product and "GAGACC" not in product


def test_junction_overhangs_chain_and_close():
    data = DNATool(ASSEMBLE).run(
        {"fragments": [DONOR_A, DONOR_B], "enzyme": "BsaI"}
    )["data"]
    order = data["assembly_order"]
    for i, part in enumerate(order):
        nxt = order[(i + 1) % len(order)]
        assert part["right_overhang"] == nxt["left_overhang"], (
            f"junction {i} does not chain: {part['right_overhang']} != {nxt['left_overhang']}"
        )


def test_labels_are_echoed_in_assembly_order():
    data = DNATool(ASSEMBLE).run(
        {
            "fragments": [DONOR_A, DONOR_B],
            "enzyme": "BsaI",
            "labels": ["pDonor-A", "pDonor-B"],
        }
    )["data"]
    assert {p["source"] for p in data["assembly_order"]} == {"pDonor-A", "pDonor-B"}


def test_type_iis_enzyme_aliases_resolve():
    """Esp3I and BsmBI are the same enzyme; both must be accepted."""
    for enzyme in ("Esp3I", "BsmBI"):
        result = DNATool(ASSEMBLE).run(
            {"fragments": [DONOR_A, DONOR_B], "enzyme": enzyme}
        )
        # These donors carry BsaI sites, so Esp3I releases nothing -- but the
        # enzyme itself must resolve rather than be reported unknown.
        assert "Unknown enzyme" not in str(result.get("error", ""))


def test_non_type_iis_enzyme_is_rejected():
    """A blunt cutter cannot drive Golden Gate; say so instead of guessing."""
    result = DNATool(ASSEMBLE).run(
        {"fragments": [DONOR_A, DONOR_B], "enzyme": "SmaI"}
    )
    assert result["status"] == "error"
    assert "5'" in result["error"] or "overhang" in result["error"]


def test_unknown_enzyme_is_reported():
    result = DNATool(ASSEMBLE).run(
        {"fragments": [DONOR_A, DONOR_B], "enzyme": "NotAnEnzyme9"}
    )
    assert result["status"] == "error"
    assert "NotAnEnzyme9" in result["error"]


def test_fragments_that_cannot_chain_report_an_error():
    """Mismatched overhangs must fail loudly, not return a plausible product."""
    mismatched = _donor("GGGG", "TTTT", "AAAACCCCAAAACCCCAAAA", "ACGTACGTACGTACGTACGT")
    result = DNATool(ASSEMBLE).run(
        {"fragments": [DONOR_A, mismatched], "enzyme": "BsaI"}
    )
    assert result["status"] == "error"
    assert "circular" in result["error"].lower()


def test_requires_a_list_of_fragments():
    assert DNATool(ASSEMBLE).run({"enzyme": "BsaI"})["status"] == "error"
