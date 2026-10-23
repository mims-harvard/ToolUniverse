from unittest.mock import Mock

import pytest

from tooluniverse.pathwaycommons_tool import PathwayCommonsTool


def test_neighborhood_has_recoverable_pages():
    header = "PARTICIPANT_A\tINTERACTION_TYPE\tPARTICIPANT_B"
    rows = [f"A{i}\tin-complex-with\tB{i}" for i in range(7)]
    response = Mock(status_code=200, text="\n".join([header, *rows]))
    tool = PathwayCommonsTool(
        {"name": "test", "fields": {"operation": "get_neighborhood"}}
    )
    tool.session.get = Mock(return_value=response)

    first = tool.run({"gene": "CDK2", "max_results": 3, "offset": 0})
    second = tool.run({"gene": "CDK2", "max_results": 3, "offset": 3})
    tail = tool.run({"gene": "CDK2", "max_results": 3, "offset": 6})

    assert [e["participant_a"] for e in first["data"]["interactions"]] == [
        "A0",
        "A1",
        "A2",
    ]
    assert [e["participant_a"] for e in second["data"]["interactions"]] == [
        "A3",
        "A4",
        "A5",
    ]
    assert [e["participant_a"] for e in tail["data"]["interactions"]] == ["A6"]
    assert first["metadata"]["next_offset"] == 3
    assert first["metadata"]["has_more"] is True
    assert tail["metadata"]["next_offset"] is None
    assert tail["metadata"]["has_more"] is False


def test_neighborhood_stops_before_extended_sif_participant_table():
    text = "\n".join(
        [
            "PARTICIPANT_A\tINTERACTION_TYPE\tPARTICIPANT_B\tINTERACTION_DATA_SOURCE",
            "CDK2\tin-complex-with\tCCNA2\tReactome",
            "",
            "PARTICIPANT\tPARTICIPANT_TYPE\tPARTICIPANT_NAME\tUNIFICATION_XREF",
            "CDK2\tProteinReference\tCDK2_HUMAN\tuniprot:P24941",
            "CCNA2\tProteinReference\tCCNA2_HUMAN\tuniprot:P20248",
        ]
    )
    tool = PathwayCommonsTool(
        {"name": "test", "fields": {"operation": "get_neighborhood"}}
    )
    tool.session.get = Mock(return_value=Mock(status_code=200, text=text))

    result = tool.run({"gene": "CDK2"})

    assert result["status"] == "success"
    assert result["metadata"]["total_interactions"] == 1
    assert result["data"]["interactions"] == [
        {
            "participant_a": "CDK2",
            "interaction_type": "in-complex-with",
            "participant_b": "CCNA2",
            "data_source": "Reactome",
        }
    ]


def test_neighborhood_forwards_official_graph_qualifiers_and_reports_resolution():
    header = "PARTICIPANT_A\tINTERACTION_TYPE\tPARTICIPANT_B"
    tool = PathwayCommonsTool(
        {"name": "test", "fields": {"operation": "get_neighborhood"}}
    )
    tool.session.get = Mock(return_value=Mock(status_code=200, text=header))

    result = tool.run(
        {
            "gene": "https://www.pathwaycommons.org/pc14/entity",
            "datasource": "reactome",
            "organism": "9606",
            "direction": "UP_STREAM",
            "pattern": ["IN_COMPLEX_WITH"],
            "subpw": False,
        }
    )

    params = tool.session.get.call_args.kwargs["params"]
    assert params["datasource"] == "reactome"
    assert params["organism"] == "9606"
    assert params["direction"] == "upstream"
    assert params["pattern"] == ["in-complex-with"]
    assert params["subpw"] is False
    assert result["metadata"]["source_resolution"] == "exact_uri"


@pytest.mark.parametrize(
    ("arguments", "field"),
    [
        ({"gene": "CDK2", "offset": "0"}, "offset"),
        ({"gene": "CDK2", "offset": -1}, "offset"),
        ({"gene": "CDK2", "max_results": 0}, "max_results"),
        ({"gene": "CDK2", "max_results": 501}, "max_results"),
        ({"gene": "CDK2", "limit": True}, "limit"),
        ({"gene": "CDK2", "limit": 101}, "limit"),
        ({"gene": "CDK2", "direction": "sideways"}, "direction"),
        ({"gene": "CDK2", "pattern": ["imaginary-relation"]}, "pattern"),
        ({"gene": "CDK2", "subpw": "false"}, "subpw"),
    ],
)
def test_neighborhood_rejects_invalid_pagination_and_depth(arguments, field):
    tool = PathwayCommonsTool(
        {"name": "test", "fields": {"operation": "get_neighborhood"}}
    )
    tool.session.get = Mock()

    result = tool.run(arguments)

    assert result["status"] == "error"
    assert field in result["error"]
    tool.session.get.assert_not_called()
