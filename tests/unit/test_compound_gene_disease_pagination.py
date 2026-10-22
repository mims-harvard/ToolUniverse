from tooluniverse.compound_gene_disease_tool import CompoundGeneDiseaseAssociationTool


def test_extractor_does_not_cap_opentargets_rows_at_thirty():
    tool = CompoundGeneDiseaseAssociationTool({"name": "test"})
    rows = [
        {"disease": {"name": f"Disease {i}"}, "score": i / 100}
        for i in range(75)
    ]

    extracted = tool._extract_genes_or_diseases(
        {"status": "success", "data": {"target": {"associatedDiseases": {"rows": rows}}}},
        "OpenTargets",
        query_by_disease=False,
    )

    assert len(extracted) == 75
    assert extracted[-1]["name"] == "Disease 74"
