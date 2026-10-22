from unittest.mock import Mock

from tooluniverse.elm_tool import ELMTool


def _response(text):
    response = Mock(status_code=200, text=text)
    return response


def test_list_classes_offset_pagination():
    tool = ELMTool({"parameter": {"properties": {"operation": {"enum": ["list_classes"]}}}})
    tool.session.get = Mock(
        return_value=_response(
            "ELMIdentifier\tAccession\tDescription\tFunctionalSiteName\tRegex\tProbability\t#Instances\t#Instances_in_PDB\n"
            + "\n".join(f"LIG_TEST_{i}\tE{i}\tdesc\tname\tA\t0.1\t1\t0" for i in range(5))
        )
    )
    result = tool.run({"operation": "list_classes", "max_results": 2, "offset": 2})

    assert [row["elm_identifier"] for row in result["data"]] == ["LIG_TEST_2", "LIG_TEST_3"]
    assert result["metadata"]["total_classes"] == 5
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_offset"] == 4


def test_interaction_domain_tail_page():
    tool = ELMTool({"parameter": {"properties": {"operation": {"enum": ["get_interaction_domains"]}}}})
    tool.session.get = Mock(
        return_value=_response(
            "ELM identifier\tInteraction Domain Id\tInteraction Domain Description\tInteraction Domain Name\n"
            + "\n".join(f"LIG_TEST_{i}\tPF{i}\tdesc\tname" for i in range(5))
        )
    )
    result = tool.run(
        {"operation": "get_interaction_domains", "max_results": 2, "offset": 4}
    )

    assert len(result["data"]) == 1
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_offset"] is None
