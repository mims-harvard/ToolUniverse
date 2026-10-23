from tooluniverse.compound_gene_disease_tool import CompoundGeneDiseaseAssociationTool


def test_extractor_does_not_cap_opentargets_rows_at_thirty():
    tool = CompoundGeneDiseaseAssociationTool({"name": "test"})
    rows = [{"disease": {"name": f"Disease {i}"}, "score": i / 100} for i in range(75)]

    extracted = tool._extract_genes_or_diseases(
        {
            "status": "success",
            "data": {"target": {"associatedDiseases": {"rows": rows}}},
        },
        "OpenTargets",
        query_by_disease=False,
    )

    assert len(extracted) == 75
    assert extracted[-1]["name"] == "Disease 74"


def test_disclosure_notes_follow_the_requested_page():
    """Truncation notes restate the caller's page size and the next offset."""
    tool = CompoundGeneDiseaseAssociationTool({"name": "test"})
    result = {
        "num_associations": 120,
        "association_offset": 0,
        "association_limit": 100,
        "next_association_offset": 100,
        "truncated": True,
        "per_source_result_counts": {"OpenTargets": 75, "GenCC": 5},
        "per_source_pagination": {
            "OpenTargets": {"limit": 25, "returned": 25},
            "GenCC": {"limit": 25, "returned": 5},
        },
    }
    rows = {"OpenTargets": [{"name": "x"}], "GenCC": [{"name": "y"}]}

    notes = tool._disclosure_notes(result, rows)

    association_note = next(n for n in notes if "'associations' is truncated" in n)
    assert "100 per page" in association_note
    assert "offset=100" in association_note
    source_note = next(n for n in notes if "per_source_results" in n)
    assert "OpenTargets 25 of 75" in source_note
    assert "GenCC" not in source_note
