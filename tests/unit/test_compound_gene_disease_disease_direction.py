"""Direction fix for gather_gene_disease_associations: the disease->gene
direction used to echo the queried disease back instead of returning the
associated genes.

The gene->disease direction was carefully built (Fix-R30D-6 resolves gene->
Ensembl id->associated diseases; Fix-R80A-1 stops ClinVar gene-as-disease
fabrication), but the parallel disease->gene direction was never given the
same treatment: `_extract_genes_or_diseases` always preferred disease-name
fields (GenCC's disease_title over gene_symbol; OpenTargets' bare disease-name
search over an associated-targets lookup), so a disease query returned the
disease name itself (e.g. "cystic fibrosis") and dropped the gene (CFTR).

These tests exercise the now direction-aware extractor with each source's real
response shape, in both directions.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.compound_gene_disease_tool import CompoundGeneDiseaseAssociationTool

pytestmark = pytest.mark.unit


def _tool():
    return CompoundGeneDiseaseAssociationTool({"name": "gather_test"})


_GENCC = {
    "status": "success",
    "data": {
        "submissions": [
            {"disease_title": "cystic fibrosis", "gene_symbol": "CFTR", "classification": "Definitive"},
            {"disease_title": "cystic fibrosis", "gene_symbol": "CFTR", "classification": "Definitive"},
        ]
    },
}

_OT_ASSOCIATED_TARGETS = {
    "status": "success",
    "data": {
        "disease": {
            "id": "MONDO_0009061",
            "name": "cystic fibrosis",
            "associatedTargets": {
                "count": 4608,
                "rows": [
                    {"target": {"id": "ENSG00000001626", "approvedSymbol": "CFTR"}, "score": 0.918},
                    {"target": {"id": "ENSG00000010704", "approvedSymbol": "HFE"}, "score": 0.41},
                ],
            },
        }
    },
}

_CLINVAR_CONDITION = {
    "status": "success",
    "data": {
        "variants": [
            {"title": "NM_000492.4(CFTR):c.82T>C", "genes": ["CFTR"], "clinical_significance": "Pathogenic"},
            {"title": "NM_000492.4(CFTR):c.353C>A", "genes": ["CFTR"], "clinical_significance": "Pathogenic"},
        ]
    },
}

_OT_ASSOCIATED_DISEASES = {  # gene->disease shape (must still yield diseases)
    "status": "success",
    "data": {
        "target": {
            "id": "ENSG00000012048",
            "associatedDiseases": {
                "rows": [
                    {"disease": {"name": "hereditary breast ovarian cancer syndrome"}, "score": 0.8},
                ]
            },
        }
    },
}


def _names(items):
    return [i["name"] for i in items]


def test_gencc_disease_query_yields_gene_not_disease():
    t = _tool()
    got = t._extract_genes_or_diseases(_GENCC, "GenCC", query_by_disease=True)
    assert _names(got) == ["CFTR", "CFTR"]


def test_gencc_gene_query_still_yields_disease():
    t = _tool()
    got = t._extract_genes_or_diseases(_GENCC, "GenCC", query_by_disease=False)
    assert _names(got) == ["cystic fibrosis", "cystic fibrosis"]


def test_opentargets_associated_targets_yields_genes():
    t = _tool()
    got = t._extract_genes_or_diseases(_OT_ASSOCIATED_TARGETS, "OpenTargets", query_by_disease=True)
    assert _names(got) == ["CFTR", "HFE"]
    assert got[0]["score"] == 0.918


def test_opentargets_associated_diseases_still_yields_diseases():
    t = _tool()
    got = t._extract_genes_or_diseases(_OT_ASSOCIATED_DISEASES, "OpenTargets", query_by_disease=False)
    assert _names(got) == ["hereditary breast ovarian cancer syndrome"]


def test_clinvar_disease_query_extracts_genes():
    t = _tool()
    got = t._extract_genes_or_diseases(_CLINVAR_CONDITION, "ClinVar", query_by_disease=True)
    assert _names(got) == ["CFTR", "CFTR"]


def test_clinvar_gene_query_contributes_nothing():
    # Fix-R80A-1 must still hold: no gene-as-disease fabrication for gene queries.
    t = _tool()
    got = t._extract_genes_or_diseases(_CLINVAR_CONDITION, "ClinVar", query_by_disease=False)
    assert got == []


def test_concordance_ranks_by_score_within_tier():
    # Same concordance tier: the higher-scored entity must lead, not the
    # alphabetically-earlier one (regression guard for the score-blind sort that
    # buried HBB below BCL11A for sickle cell).
    t = _tool()
    results = {
        "OpenTargets": [
            {"name": "BCL11A", "score": 0.30, "source": "OpenTargets"},
            {"name": "HBB", "score": 0.81, "source": "OpenTargets"},
        ]
    }
    out = t._build_concordance(results)
    assert [a["name"] for a in out] == ["HBB", "BCL11A"]
    # output shape stays clean (no internal sort key leaks)
    assert "_best_score" not in out[0]


def test_concordance_scored_entities_lead_unscored_in_tier():
    t = _tool()
    results = {
        "GenCC": [{"name": "ZZZ1", "score": None, "source": "GenCC"}],
        "OpenTargets": [{"name": "AAA1", "score": 0.5, "source": "OpenTargets"}],
    }
    out = t._build_concordance(results)
    # both concordance 1; scored AAA1 leads the unscored ZZZ1 despite alphabetical order
    assert [a["name"] for a in out] == ["AAA1", "ZZZ1"]
