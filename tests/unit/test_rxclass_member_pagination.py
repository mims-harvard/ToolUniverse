from unittest.mock import MagicMock, patch

from tooluniverse.rxclass_tool import RxClassTool


def _tool():
    return RxClassTool(
        {"name": "RxClass_get_class_members", "fields": {"operation": "get_class_members"}}
    )


def _response(count=5):
    response = MagicMock()
    response.json.return_value = {
        "drugMemberGroup": {
            "drugMember": [
                {
                    "minConcept": {
                        "rxcui": str(index),
                        "name": f"drug-{index}",
                        "tty": "IN",
                    }
                }
                for index in range(count)
            ]
        }
    }
    response.raise_for_status.return_value = None
    return response


def _classes_response(count=5):
    response = MagicMock()
    response.json.return_value = {
        "rxclassDrugInfoList": {
            "rxclassDrugInfo": [
                {
                    "rxclassMinConceptItem": {
                        "classId": f"C{index}",
                        "className": f"class-{index}",
                        "classType": "ATC1-4",
                    },
                    "minConcept": {"rxcui": "1191", "name": "aspirin", "tty": "IN"},
                    "rela": "has_ingredient",
                    "relaSource": "ATC",
                }
                for index in range(count)
            ]
        }
    }
    response.raise_for_status.return_value = None
    return response


def _find_classes_response(count=5):
    response = MagicMock()
    response.json.return_value = {
        "rxclassMinConceptList": {
            "rxclassMinConcept": [
                {
                    "classId": f"C{index}",
                    "className": f"inhibitor class {index}",
                    "classType": "MOA",
                }
                for index in range(count)
            ]
        }
    }
    response.raise_for_status.return_value = None
    return response


@patch("tooluniverse.rxclass_tool.requests.get", return_value=_response())
def test_rxclass_members_report_total_and_adjacent_page(_get):
    result = _tool().run({"class_id": "J01", "limit": 2, "offset": 2})

    assert [row["rxcui"] for row in result["data"]] == ["2", "3"]
    assert result["metadata"]["total_count"] == 5
    assert result["metadata"]["count"] == 2
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_offset"] == 4


@patch("tooluniverse.rxclass_tool.requests.get", return_value=_response())
def test_rxclass_members_tail_page_terminates(_get):
    result = _tool().run({"class_id": "J01", "limit": 2, "offset": 4})

    assert [row["rxcui"] for row in result["data"]] == ["4"]
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_offset"] is None


@patch("tooluniverse.rxclass_tool.requests.get", return_value=_classes_response())
def test_rxclass_drug_classes_report_total_and_later_page(_get):
    tool = RxClassTool(
        {"name": "RxClass_get_drug_classes", "fields": {"operation": "get_drug_classes"}}
    )
    result = tool.run(
        {"drug_name": "aspirin", "rela_source": "ALL", "limit": 2, "offset": 2}
    )

    assert [row["classId"] for row in result["data"]] == ["C2", "C3"]
    assert result["metadata"]["total_count"] == 5
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_offset"] == 4


@patch(
    "tooluniverse.rxclass_tool.requests.get", return_value=_find_classes_response()
)
def test_rxclass_find_classes_report_total_and_later_page(_get):
    tool = RxClassTool(
        {"name": "RxClass_find_classes", "fields": {"operation": "find_classes"}}
    )
    result = tool.run({"query": "inhibitor", "limit": 2, "offset": 2})

    assert [row["classId"] for row in result["data"]] == ["C2", "C3"]
    assert result["metadata"]["total_count"] == 5
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_offset"] == 4


@patch(
    "tooluniverse.rxclass_tool.requests.get", return_value=_find_classes_response()
)
def test_rxclass_find_classes_tail_page_terminates(_get):
    tool = RxClassTool(
        {"name": "RxClass_find_classes", "fields": {"operation": "find_classes"}}
    )
    result = tool.run({"query": "inhibitor", "limit": 2, "offset": 4})

    assert [row["classId"] for row in result["data"]] == ["C4"]
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_offset"] is None
