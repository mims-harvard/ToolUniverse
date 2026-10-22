from tooluniverse.compound_disease_tool import CompoundDiseaseProfileTool


def test_opentargets_cross_references_are_not_capped_at_ten():
    tool = CompoundDiseaseProfileTool({"name": "test"})
    xrefs = [f"DB:{i}" for i in range(19)]
    result = {
        "status": "success",
        "data": {
            "search": {
                "hits": [
                    {
                        "id": "MONDO_0009061",
                        "name": "cystic fibrosis",
                        "object": {
                            "id": "MONDO_0009061",
                            "name": "cystic fibrosis",
                            "dbXRefs": xrefs,
                        },
                    }
                ]
            }
        },
    }

    parsed = tool._parse_opentargets(result)

    assert parsed["dbXRef_count"] == 19
    assert parsed["dbXRefs"] == xrefs
