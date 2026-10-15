"""Unit tests for gather_target_profile.

These cover the parts that must not depend on a live upstream: which databases
apply to a non-human target, the per-datasource expression ranking, and the
loss-of-function constraint cross-check.
"""

from tooluniverse.compound_target_profile_tool import (
    SECTIONS,
    CompoundTargetProfileTool,
    _is_human_ensembl,
)


def _tool():
    return CompoundTargetProfileTool(
        {
            "name": "gather_target_profile",
            "type": "CompoundTargetProfileTool",
            "parameter": {"type": "object", "properties": {}},
        }
    )


def test_human_ensembl_detection_gates_the_human_only_sources():
    """OpenTargets accepts a mouse id and answers 'no target', once per endpoint.

    A mouse gene produced six failures and no explanation of why; the id itself
    says which curation applies.
    """
    assert _is_human_ensembl("ENSG00000141510") is True
    assert _is_human_ensembl("ensg00000141510") is True
    assert _is_human_ensembl("ENSMUSG00000059552") is False
    assert _is_human_ensembl("ENSRNOG00000010756") is False
    assert _is_human_ensembl(None) is False
    assert _is_human_ensembl("") is False
    # A transcript is not a gene id and must not pass as one.
    assert _is_human_ensembl("ENST00000269305") is False


def test_expression_ranks_within_a_datasource_never_across():
    """GTEx reports bulk TPM and Tabula Sapiens pseudobulk CPM.

    One ranking over both would order different quantities against each other,
    so each source is ranked and labelled with its own unit.
    """
    tool = _tool()
    rows = [
        {
            "datasourceId": "gtex",
            "unit": "TPM",
            "median": 37.4,
            "tissueBiosample": {"biosampleName": "skin"},
        },
        {
            "datasourceId": "gtex",
            "unit": "TPM",
            "median": 8.4,
            "tissueBiosample": {"biosampleName": "ovary"},
        },
        {
            "datasourceId": "tabula_sapiens",
            "unit": "CPM",
            "median": 219.0,
            "tissueBiosample": {"biosampleName": "cardiac atrium"},
            "celltypeBiosample": {"biosampleName": "natural killer cell"},
        },
        # Same tissue, a second cell type: Tabula Sapiens gives TP53 1173 rows
        # over 65 tissues, so ranking rows listed one tissue many times and read
        # as a ranking of tissues.
        {
            "datasourceId": "tabula_sapiens",
            "unit": "CPM",
            "median": 12.0,
            "tissueBiosample": {"biosampleName": "cardiac atrium"},
            "celltypeBiosample": {"biosampleName": "fibroblast"},
        },
        # Rows without a biosample name carry no tissue to rank.
        {"datasourceId": "gtex", "unit": "TPM", "median": 999.0},
    ]
    out = tool._expression(
        lambda *a: {
            "status": "success",
            "data": {
                "target": {
                    "baselineExpression": {
                        "count": 4,
                        "rows": rows,
                        "truncated": False,
                    }
                }
            },
        },
        "ENSG00000141510",
    )
    gtex = out["by_datasource"]["gtex"]
    assert gtex["unit"] == "TPM"
    # The unnamed row is excluded, so the highest TPM is 37.4 and not 999.
    assert gtex["rows_measured"] == 2
    assert gtex["distinct_tissues"] == 2
    assert [t["tissue"] for t in gtex["highest_expression"]] == ["skin", "ovary"]
    # Bulk rows carry no cell type.
    assert all(t["cell_type"] is None for t in gtex["highest_expression"])

    ts = out["by_datasource"]["tabula_sapiens"]
    assert ts["unit"] == "CPM"
    # Two rows, one tissue: listed once, at its highest-expressing cell type.
    assert ts["rows_measured"] == 2
    assert ts["distinct_tissues"] == 1
    assert ts["highest_expression"] == [
        {
            "tissue": "cardiac atrium",
            "median": 219.0,
            "cell_type": "natural killer cell",
        }
    ]
    assert out["complete"] is True
    # The dropped row is counted, so the per-source totals plus the untissued
    # rows account for every row read.
    assert out["rows_without_tissue"] == 1
    binned = sum(b["rows_measured"] for b in out["by_datasource"].values())
    assert binned + out["rows_without_tissue"] == out["rows_read"]

    notes = " ".join(
        tool._notes({"expression": out, "sources_failed": []}, ["expression"])
    )
    assert "not comparable" in notes


def test_tractability_reports_only_supported_assessments():
    tool = _tool()
    rows = [
        {"label": "Approved Drug", "modality": "SM", "value": False},
        {"label": "Advanced Clinical", "modality": "SM", "value": True},
        {"label": "UniProt Ubiquitination", "modality": "PR", "value": True},
    ]
    out = tool._tractability(
        lambda *a: {"status": "success", "data": {"target": {"tractability": rows}}},
        "ENSG00000141510",
    )
    assert out["assessments"] == 3
    assert out["supported_by_modality"] == {
        "SM": ["Advanced Clinical"],
        "PR": ["UniProt Ubiquitination"],
    }
    assert out["modalities_with_evidence"] == ["PR", "SM"]

    # No supported modality is the absence of a positive assessment, not a
    # verdict that the target cannot be drugged.
    empty = tool._tractability(
        lambda *a: {"status": "success", "data": {"target": {"tractability": []}}},
        "ENSG00000141510",
    )
    notes = " ".join(
        tool._notes({"tractability": empty, "sources_failed": []}, ["tractability"])
    )
    assert "not an assessment that the target is" in notes


def _safety_call(ot_obs, gnomad_obs):
    def call(_source, tool_name, _args):
        if "safety_profile" in tool_name:
            return {"status": "success", "data": {"target": {"safetyLiabilities": []}}}
        if "constraint_info" in tool_name:
            return {
                "status": "success",
                "data": {
                    "target": {
                        "geneticConstraint": [
                            {"constraintType": "syn", "obs": 1},
                            {"constraintType": "lof", "obs": ot_obs, "exp": 49.8},
                        ]
                    }
                },
            }
        return {
            "status": "success",
            "data": {
                "gene": {"gnomad_constraint": {"obs_lof": gnomad_obs, "pLI": 0.99}}
            },
        }

    return call


def test_constraint_sources_are_compared_not_merged():
    """The two curators can disagree, and the comparison is how that surfaces.

    When this was written OpenTargets reported 59 observed loss-of-function
    variants for PCSK9 against gnomAD's 57, and 12 against 13 for SEPT9;
    OpenTargets has since moved to the same gnomAD release and they now agree.
    The mocked figures below stand in for that state, because the point of the
    comparison is to catch the next divergence, not that one is current.
    """
    tool = _tool()
    agree = tool._safety(_safety_call(12, 12), lambda *a: None, "ENSG1", "TP53")
    assert agree["sources_agree_on_observed_lof"] is True

    conflict = tool._safety(_safety_call(59, 57), lambda *a: None, "ENSG1", "PCSK9")
    assert conflict["sources_agree_on_observed_lof"] is False
    assert conflict["lof_constraint_opentargets"]["observed"] == 59
    assert conflict["lof_constraint_gnomad"]["observed"] == 57
    notes = " ".join(
        tool._notes({"safety": conflict, "sources_failed": []}, ["safety"])
    )
    assert "different gnomAD releases" in notes


def test_a_non_human_target_skips_the_human_only_sources_audibly():
    tool = _tool()
    skipped = []

    def call(*_args):  # pragma: no cover - must not be reached
        raise AssertionError("human-only source queried for a non-human target")

    out = tool._safety(
        call, lambda s, r: skipped.append(s), "ENSMUSG00000059552", "Trp53", human=False
    )
    assert out["lof_constraint_opentargets"] is None
    assert out["lof_constraint_gnomad"] is None
    # None, not False: the lookup was not attempted rather than attempted and
    # failed, and the note must not claim it "did not answer".
    assert out["liabilities_checked"] is None
    assert skipped == ["gnomad"]

    notes = " ".join(tool._notes({"safety": out, "sources_failed": []}, ["safety"]))
    assert "cover human targets only" in notes
    assert "did not answer" not in notes

    # Nor may tractability claim an absence of evidence it never looked for.
    absent = tool._absent_tractability()
    assert absent["assessments"] is None
    tract_notes = " ".join(
        tool._notes({"tractability": absent, "sources_failed": []}, ["tractability"])
    )
    assert tract_notes == ""


def test_absent_liabilities_are_not_evidence_of_safety():
    tool = _tool()
    checked = tool._safety(_safety_call(12, 12), lambda *a: None, "ENSG1", "TP53")
    assert checked["safety_liabilities"] == []
    notes = " ".join(tool._notes({"safety": checked, "sources_failed": []}, ["safety"]))
    assert "not evidence that inhibiting it is safe" in notes

    # A lookup that never answered says nothing at all, which is different.
    unanswered = tool._safety(lambda *a: None, lambda *a: None, "ENSG1", "TP53")
    assert unanswered["liabilities_checked"] is False
    unanswered_notes = " ".join(
        tool._notes({"safety": unanswered, "sources_failed": []}, ["safety"])
    )
    assert "says nothing about this target" in unanswered_notes


def test_uniprot_function_arrives_as_a_bare_list():
    """UniProt's function endpoint does not use the {status, data} envelope."""
    tool = _tool()
    out = tool._function(
        lambda *a: ["Multifunctional transcription factor", "Second description"],
        lambda *a: None,
        "P04637",
    )
    assert out["descriptions"][0].startswith("Multifunctional")
    assert out["truncated"] is False
    assert out["pubmed_citations_removed"] is False

    # UniProt carries its evidence inline; for TP53 that is roughly half the text.
    cited = tool._function(
        lambda *a: ["Induces apoptosis (PubMed:11025664, PubMed:12524540). Acts."],
        lambda *a: None,
        "P04637",
    )
    assert cited["descriptions"] == ["Induces apoptosis. Acts."]
    assert cited["pubmed_citations_removed"] is True

    skipped = []
    none = tool._function(lambda *a: None, lambda s, r: skipped.append(s), None)
    assert none["descriptions"] == [] and skipped == ["uniprot"]


def test_run_rejects_bad_input_without_raising():
    tool = _tool()
    assert tool.run({})["status"] == "error"
    assert tool.run({"target": "   "})["status"] == "error"
    empty = tool.run({"target": "TP53", "sections": []})
    assert empty["status"] == "error" and "empty" in empty["error"]
    bad = tool.run({"target": "TP53", "sections": ["nope"]})
    assert bad["status"] == "error" and "nope" in bad["error"]
    assert set(SECTIONS) == {
        "identity",
        "function",
        "expression",
        "tractability",
        "safety",
    }
