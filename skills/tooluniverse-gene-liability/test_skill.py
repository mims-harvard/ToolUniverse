"""Contract tests for the gene-liability skill's documented tools."""

import inspect
from pathlib import Path

import pytest

from tooluniverse.tools.ClinVar_search_variants import ClinVar_search_variants
from tooluniverse.tools.DepMap_get_gene_dependencies import (
    DepMap_get_gene_dependencies,
)
from tooluniverse.tools.GTEx_get_median_gene_expression import (
    GTEx_get_median_gene_expression,
)
from tooluniverse.tools.HPA_get_comprehensive_gene_details_by_ensembl_id import (
    HPA_get_comprehensive_gene_details_by_ensembl_id,
)
from tooluniverse.tools.MyGene_query_genes import MyGene_query_genes
from tooluniverse.tools.OpenTargets_get_associated_drugs_by_target_ensemblID import (
    OpenTargets_get_associated_drugs_by_target_ensemblID,
)
from tooluniverse.tools.OpenTargets_get_biological_mouse_models_by_ensemblID import (
    OpenTargets_get_biological_mouse_models_by_ensemblID,
)
from tooluniverse.tools.OpenTargets_get_target_safety_profile_by_ensemblID import (
    OpenTargets_get_target_safety_profile_by_ensemblID,
)
from tooluniverse.tools.gnomad_get_gene_constraints import gnomad_get_gene_constraints


pytestmark = pytest.mark.unit

_SKILL_TEXT = (Path(__file__).parent / "SKILL.md").read_text()


def test_skill_has_no_host_specific_metadata():
    skill_dir = Path(__file__).parent

    assert not (skill_dir / "agents" / "openai.yaml").exists()


@pytest.mark.parametrize(
    ("tool", "parameter"),
    [
        (MyGene_query_genes, "query"),
        (gnomad_get_gene_constraints, "gene_symbol"),
        (OpenTargets_get_biological_mouse_models_by_ensemblID, "ensemblId"),
        (GTEx_get_median_gene_expression, "gencode_id"),
        (HPA_get_comprehensive_gene_details_by_ensembl_id, "ensembl_id"),
        (OpenTargets_get_target_safety_profile_by_ensemblID, "ensemblId"),
        (OpenTargets_get_associated_drugs_by_target_ensemblID, "ensemblId"),
        (ClinVar_search_variants, "gene"),
        (DepMap_get_gene_dependencies, "gene_symbol"),
    ],
)
def test_documented_tool_parameter_contracts(tool, parameter):
    assert parameter in inspect.signature(tool).parameters


def test_gtex_uses_the_supported_operation_name():
    assert 'operation="get_median_gene_expression"' in _SKILL_TEXT
    assert 'operation="median"' not in _SKILL_TEXT


def test_score_weights_cover_the_full_liability_model():
    for dimension, weight in [
        ("Human genetic constraint", 25),
        ("Mammalian knockout phenotype", 25),
        ("Critical-organ expression", 20),
        ("Observed on-target effects", 20),
        ("Cellular essentiality and redundancy", 10),
    ]:
        assert dimension in _SKILL_TEXT
        assert f"| {weight} |" in _SKILL_TEXT

    assert sum([25, 25, 20, 20, 10]) == 100


def test_skill_does_not_treat_missing_evidence_as_safe():
    normalized_text = " ".join(_SKILL_TEXT.split())

    assert "Do not assign zero points to a missing dimension" in normalized_text
    assert "DepMap as cancer-cell essentiality" in _SKILL_TEXT
