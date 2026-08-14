"""Regression guard for Fix-R58-2: gnomad_get_gene_constraints reported
mitochondrially-encoded genes as having no constraint data at all.

gnomAD scores mtDNA genes under `mitochondrial_constraint`, never under
`gnomad_constraint`/`exac_constraint`. The tool's GraphQL query asked only
for the latter two, so MT-ND4 returned `status: success` with both null and
no note -- readable as "unconstrained" for a gene gnomAD actually scores at
oe_lof_upper 0.022, i.e. among the most loss-of-function-intolerant there
are. That is the wrong answer on exactly the gene family a Leber hereditary
optic neuropathy workup turns on.

Confirmed live against the host the tool calls
(POST https://gnomad.broadinstitute.org/api):

    MT-ND4  -> mitochondrial_constraint {__typename ProteinMitochondrialGene
               Constraint, exp_lof 52.597, obs_lof 0, oe_lof 0,
               oe_lof_upper 0.022}
    MT-TL1  -> mitochondrial_constraint {__typename RNAMitochondrialGene
               Constraint, observed 13.634, expected 92.721, oe 0.147,
               oe_upper 0.213}
    OPA1    -> mitochondrial_constraint null, gnomad_constraint pLI 0.962

Both union branches are requested because mt-tRNA/mt-rRNA genes use the RNA
shape. The query lives in the shipped config, not in the Python default --
the class only falls back to its own literal when the config omits one, so
editing the Python alone changed nothing.
"""

import json
from pathlib import Path

import pytest

from tooluniverse.gnomad_tool import (
    _note_absent_constraints,
    gnomADGetGeneConstraints,
)

pytestmark = pytest.mark.unit

_CONFIG = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "tooluniverse"
    / "data"
    / "gnomad_tools.json"
)


def _config(name="gnomad_get_gene_constraints"):
    return next(c for c in json.loads(_CONFIG.read_text()) if c["name"] == name)


def _query_actually_sent():
    """The query the tool will send: config wins over the class default."""
    cfg = _config()
    return cfg["fields"]["query_schema"] or gnomADGetGeneConstraints(cfg).query_schema


def test_shipped_query_requests_mitochondrial_constraint():
    query = _query_actually_sent()
    assert "mitochondrial_constraint" in query, (
        "without this field mtDNA genes report null constraint and read as "
        "unconstrained"
    )


def test_both_mitochondrial_union_branches_are_requested():
    """Protein-coding mtDNA genes and mt-tRNA genes return different shapes."""
    query = _query_actually_sent()
    assert "ProteinMitochondrialGeneConstraint" in query
    assert "RNAMitochondrialGeneConstraint" in query
    assert "oe_lof_upper" in query, "the protein-branch constraint figure"
    assert "oe_upper" in query, "the RNA-branch constraint figure"


def test_nuclear_constraint_fields_are_untouched():
    """The fix is additive -- OPA1's pLI must still be asked for."""
    query = _query_actually_sent()
    assert "gnomad_constraint" in query
    assert "exac_constraint" in query
    assert "pLI" in query


def test_schema_admits_a_null_nuclear_constraint():
    """MT-* genes return gnomad_constraint null; the schema used to forbid it."""
    props = _config()["return_schema"]["oneOf"][0]["properties"]["gene"]["properties"]
    assert "null" in props["gnomad_constraint"]["type"]
    assert "mitochondrial_constraint" in props


@pytest.mark.parametrize(
    "gene_payload",
    [
        {"symbol": "MT-ND4", "gnomad_constraint": None, "exac_constraint": None},
        {"symbol": "SOMEGENE"},
    ],
)
def test_note_fires_when_no_constraint_of_any_kind_is_present(gene_payload):
    result = {
        "status": "success",
        "gene_symbol": gene_payload["symbol"],
        "data": {"gene": gene_payload},
    }
    _note_absent_constraints(result)

    assert "note" in result
    assert "not that the gene is unconstrained" in result["note"]


def test_note_is_absent_when_mitochondrial_constraint_was_returned():
    """A scored mtDNA gene is not a no-data case and must not be labelled one."""
    result = {
        "status": "success",
        "gene_symbol": "MT-ND4",
        "data": {
            "gene": {
                "symbol": "MT-ND4",
                "gnomad_constraint": None,
                "exac_constraint": None,
                "mitochondrial_constraint": {"oe_lof_upper": 0.022},
            }
        },
    }
    _note_absent_constraints(result)

    assert "note" not in result


def test_note_is_absent_for_a_scored_nuclear_gene():
    result = {
        "status": "success",
        "gene_symbol": "OPA1",
        "data": {"gene": {"symbol": "OPA1", "gnomad_constraint": {"pLI": 0.962}}},
    }
    _note_absent_constraints(result)

    assert "note" not in result
