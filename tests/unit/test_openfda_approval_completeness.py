from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.openfda_approval_tool import OpenFDAApprovalTool


pytestmark = pytest.mark.unit


def _response(payload=None, status=200, text=""):
    response = MagicMock()
    response.status_code = status
    response.text = text
    response.json.return_value = payload
    return response


def _application(number, brands=None, strengths=None, documents=0):
    return {
        "application_number": number,
        "sponsor_name": "Example sponsor",
        "openfda": {
            "brand_name": brands or [f"Brand {number}"],
            "generic_name": ["GENERIC A", "GENERIC B"],
        },
        "products": [
            {
                "product_number": "001",
                "brand_name": (brands or [f"Brand {number}"])[0],
                "active_ingredients": [
                    {"name": "INGREDIENT", "strength": strength}
                    for strength in (strengths or ["1MG"])
                ],
                "dosage_form": "TABLET",
                "route": "ORAL",
            }
        ],
        "submissions": [
            {
                "submission_type": "ORIG",
                "submission_status": "AP",
                "submission_number": "1",
                "submission_status_date": "20200101",
                "application_docs": [
                    {
                        "id": str(index),
                        "type": "Review",
                        "title": f"Doc {index}",
                        "url": "x",
                    }
                    for index in range(documents)
                ],
            }
        ],
    }


def _payload(results, total, skip=0, limit=5):
    return {
        "meta": {"results": {"skip": skip, "limit": limit, "total": total}},
        "results": results,
    }


def test_search_has_exact_offset_pagination_and_complete_summary_arrays():
    brands = [f"Brand {index}" for index in range(6)]
    strengths = [f"{index}MG" for index in range(7)]
    app = _application("ANDA1", brands=brands, strengths=strengths)
    tool = OpenFDAApprovalTool({"fields": {"operation": "search_approvals"}})
    with patch(
        "tooluniverse.openfda_approval_tool.requests.get",
        return_value=_response(_payload([app], total=3, skip=2, limit=1)),
    ) as get:
        result = tool.run({"drug_name": "aspirin", "limit": 1, "offset": 2})
    assert get.call_args.kwargs["params"]["skip"] == 2
    assert result["metadata"]["total_matches"] == 3
    assert result["metadata"]["has_more"] is False
    summary = result["data"]["approvals"][0]
    assert summary["brand_names"] == brands
    assert summary["strengths"] == sorted(strengths)


def test_http_error_is_not_rewritten_as_zero_results():
    tool = OpenFDAApprovalTool({"fields": {"operation": "search_approvals"}})
    with patch(
        "tooluniverse.openfda_approval_tool.requests.get",
        return_value=_response(status=503, text="maintenance"),
    ):
        result = tool.run({"drug_name": "aspirin"})
    assert result["status"] == "error"
    assert result["status_code"] == 503
    assert "maintenance" in result["detail"]


def test_ambiguous_drug_name_returns_candidates_instead_of_first_record():
    apps = [_application("ANDA1"), _application("NDA2")]
    tool = OpenFDAApprovalTool({"fields": {"operation": "get_approval_history"}})
    with patch(
        "tooluniverse.openfda_approval_tool.requests.get",
        return_value=_response(_payload(apps, total=2, limit=100)),
    ):
        result = tool.run({"drug_name": "aspirin"})
    assert result["status"] == "error"
    assert result["error_type"] == "ambiguous_query"
    assert result["candidate_application_numbers"] == ["ANDA1", "NDA2"]


def test_exact_history_keeps_every_application_document():
    app = _application("NDA1", documents=7)
    tool = OpenFDAApprovalTool({"fields": {"operation": "get_approval_history"}})
    with patch(
        "tooluniverse.openfda_approval_tool.requests.get",
        return_value=_response(_payload([app], total=1, limit=100)),
    ):
        result = tool.run({"application_number": "NDA1"})
    docs = result["data"]["submission_history"][0]["application_docs"]
    assert len(docs) == 7
    assert result["metadata"]["all_submission_documents_included"] is True


@pytest.mark.parametrize(
    "arguments",
    [
        {"drug_name": "aspirin", "limit": 0},
        {"drug_name": "aspirin", "limit": "5"},
        {"drug_name": "aspirin", "offset": -1},
    ],
)
def test_invalid_paging_is_rejected_before_network(arguments):
    tool = OpenFDAApprovalTool({"fields": {"operation": "search_approvals"}})
    with patch("tooluniverse.openfda_approval_tool.requests.get") as get:
        result = tool.run(arguments)
    assert result["status"] == "error"
    get.assert_not_called()


def test_detail_rejects_conflicting_identifiers_before_network():
    tool = OpenFDAApprovalTool({"fields": {"operation": "get_approved_products"}})
    with patch("tooluniverse.openfda_approval_tool.requests.get") as get:
        result = tool.run({"drug_name": "aspirin", "application_number": "NDA1"})
    assert result["status"] == "error"
    assert "not both" in result["error"]
    get.assert_not_called()
