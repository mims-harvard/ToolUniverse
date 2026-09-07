"""NCBIVariation_rsid_lookup reports 1-based GRCh38 positions.

dbSNP SPDI offsets are 0-based interbase. Passing them through under the name
`position` put every variant one base 5' of its real location while the tool
advertised "GRCh38 genomic coordinates": rs121965019 (IDUA c.1205G>A) came back
as chr4:1002746 where ClinVar, Ensembl VEP and MyVariant all say 1002747.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.ncbi_variation_tool import (
    _dedupe_genes,
    _grch38_placement_from_spdi,
)

pytestmark = pytest.mark.unit


def test_substitution_position_is_one_based():
    placement = _grch38_placement_from_spdi(
        {
            "seq_id": "NC_000004.12",
            "position": 1002746,
            "deleted_sequence": "G",
            "inserted_sequence": "A",
        }
    )

    assert placement["position"] == 1002747
    assert placement["coordinate_system"] == "1-based"
    assert placement["spdi_position"] == 1002746


def test_insertion_anchors_on_the_preceding_base():
    placement = _grch38_placement_from_spdi(
        {
            "seq_id": "NC_000019.10",
            "position": 44908683,
            "deleted_sequence": "",
            "inserted_sequence": "T",
        }
    )

    assert placement["position"] == 44908683
    assert placement["spdi_position"] == 44908683


def test_missing_position_is_passed_through_unchanged():
    placement = _grch38_placement_from_spdi(
        {"seq_id": "NC_000019.10", "position": None, "deleted_sequence": "T"}
    )

    assert placement["position"] is None


def test_genes_repeated_per_allele_are_collapsed():
    genes = [
        {"gene": "IDUA", "name": "alpha-L-iduronidase", "gene_id": 3425},
        {"gene": "IDUA", "name": "alpha-L-iduronidase", "gene_id": 3425},
        {"gene": "APOE", "name": "apolipoprotein E", "gene_id": 348},
    ]

    assert [g["gene"] for g in _dedupe_genes(genes)] == ["IDUA", "APOE"]
