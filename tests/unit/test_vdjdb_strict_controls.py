from unittest.mock import patch

import pytest

from tooluniverse.vdjdb_tool import VDJDBTool


@pytest.mark.parametrize(
    "arguments",
    [
        {"operation": "search_cdr3", "cdr3": "CASSIRSSYEQYF", "match_type": "typo"},
        {"operation": "search_cdr3", "cdr3": "CASSIRSSYEQYF", "page": True},
        {"operation": "search_cdr3", "cdr3": "CASSIRSSYEQYF", "page_size": 101},
        {"operation": "search_cdr3", "cdr3": "CASSIRSSYEQYF", "species": "rat"},
        {"operation": "search_cdr3", "cdr3": "CASSIRSSYEQYF", "gene": "IGH"},
        {
            "operation": "get_antigen_specificity",
            "epitope": "GILGFVFTL",
            "mhc_class": "I",
        },
        {
            "operation": "get_antigen_specificity",
            "epitope": "GILGFVFTL",
            "min_score": True,
        },
    ],
)
def test_invalid_controls_do_not_reach_api(arguments):
    tool = VDJDBTool({"name": "vdjdb"})
    with patch.object(tool.session, "post") as post:
        result = tool.run(arguments)
    assert result["status"] == "error"
    post.assert_not_called()
