from unittest.mock import Mock

from tooluniverse.rcsb_data_tool import RCSBDataTool


def test_assembly_operations_and_evidence_have_independent_pages(monkeypatch) -> None:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "rcsb_id": "1CWP-1",
        "rcsb_assembly_info": {},
        "pdbx_struct_assembly": {},
        "pdbx_struct_oper_list": [
            {"id": str(index), "type": "point symmetry operation"}
            for index in range(12)
        ],
        "pdbx_struct_assembly_auth_evidence": [
            {"experimental_support": f"evidence {index}"} for index in range(7)
        ],
    }
    monkeypatch.setattr(
        "tooluniverse.rcsb_data_tool.requests.get", Mock(return_value=response)
    )
    tool = RCSBDataTool({"fields": {"endpoint": "assembly"}})

    result = tool.run(
        {
            "pdb_id": "1CWP",
            "operation_limit": 2,
            "operation_offset": 10,
            "evidence_limit": 1,
            "evidence_offset": 5,
        }
    )

    data = result["data"]
    assert data["operation_count"] == 12
    assert [operation["id"] for operation in data["operations"]] == ["10", "11"]
    assert data["operations_pagination"] == {
        "offset": 10,
        "limit": 2,
        "returned": 2,
        "has_more": False,
        "next_offset": None,
    }
    assert data["evidence_count"] == 7
    assert data["evidence"][0]["experimental_support"] == "evidence 5"
    assert data["evidence_pagination"] == {
        "offset": 5,
        "limit": 1,
        "returned": 1,
        "has_more": True,
        "next_offset": 6,
    }
