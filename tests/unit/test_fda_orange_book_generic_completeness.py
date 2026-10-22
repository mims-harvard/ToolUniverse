"""Regression tests for complete, criteria-backed generic classification."""

from unittest.mock import patch

from tooluniverse.fda_orange_book_tool import FDAOrangeBookTool


def _tool():
    return FDAOrangeBookTool(
        {
            "name": "FDA_OrangeBook_check_generic_availability",
            "parameter": {
                "properties": {
                    "operation": {
                        "const": "check_generic_availability",
                        "default": "check_generic_availability",
                    }
                }
            },
        }
    )


def _drug(app, reference="No"):
    return {
        "application_number": app,
        "sponsor_name": "Sponsor",
        "products": [
            {
                "brand_name": app,
                "reference_drug": reference,
                "marketing_status": "Prescription",
                "te_code": "AB",
                "active_ingredients": [{"name": "IBUPROFEN"}],
            }
        ],
    }


def test_generic_check_reads_all_pages_and_uses_anda_criterion():
    pages = [
        {
            "status": "success",
            "drugs": [_drug("NDA001", "Yes"), _drug("NDA002", "No")],
            "total": 4,
            "has_more": True,
            "next_offset": 2,
        },
        {
            "status": "success",
            "drugs": [_drug("ANDA003", "No"), _drug("ANDA004", "Yes")],
            "total": 4,
            "has_more": False,
            "next_offset": None,
        },
    ]
    tool = _tool()
    with patch.object(tool, "_search_drug", side_effect=pages) as search:
        data = tool.run({"generic_name": "IBUPROFEN"})["data"]

    assert search.call_count == 2
    assert search.call_args_list[0].args[0]["offset"] == 0
    assert search.call_args_list[1].args[0]["offset"] == 2
    assert data["applications_scanned"] == 4
    assert data["reference_count"] == 2
    assert data["generic_count"] == 2
    assert data["generics_available"] is True
    assert data["counts_complete"] is True
    assert "ANDA" in data["classification_criteria"]["generic"]
    # NDA002 is non-reference but is not a generic application.
    assert {d["application_number"] for d in data["generic_drugs"]} == {
        "ANDA003",
        "ANDA004",
    }
