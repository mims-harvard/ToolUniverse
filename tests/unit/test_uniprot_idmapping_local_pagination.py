from tooluniverse.uniprot_idmapping_tool import UniProtIDMappingTool


def test_mappings_after_old_five_hundred_cutoff_are_recoverable():
    parsed = [{"from": "P00533", "to": str(i)} for i in range(587)]

    page = UniProtIDMappingTool._paginate_parsed_results(
        parsed, {"limit": 3, "offset": 500}
    )

    assert [item["to"] for item in page["results"]] == ["500", "501", "502"]
    assert page["returned"] == 3
    assert page["has_more"] is True
    assert page["next_offset"] == 503
