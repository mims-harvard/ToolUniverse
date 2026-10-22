from unittest.mock import Mock, patch

import pytest

from tooluniverse.swiss_target_tool import SwissTargetTool


@pytest.mark.parametrize("value", [0, -1, True, 1.5])
def test_invalid_top_n_does_not_submit(value):
    tool = SwissTargetTool({"name": "swiss"})
    with patch.object(tool.session, "post") as post:
        result = tool.run({"operation": "predict", "smiles": "CCO", "top_n": value})
    assert result["status"] == "error"
    post.assert_not_called()


def test_top_n_preserves_total_available_count():
    tool = SwissTargetTool({"name": "swiss"})
    submit = Mock(
        status_code=200,
        text='location.replace("https://www.swisstargetprediction.ch/result.php?job=123&organism=Homo_sapiens")',
    )
    result_page = Mock(status_code=200, text="table")
    targets = [{"target_name": str(i)} for i in range(100)]
    with (
        patch.object(tool.session, "post", return_value=submit),
        patch.object(tool.session, "get", return_value=result_page),
        patch.object(tool, "_parse_result_table", return_value=targets),
    ):
        result = tool.run({"operation": "predict", "smiles": "CCO", "top_n": 10})
    data = result["data"]
    assert data["total_targets"] == 100
    assert data["returned_targets"] == 10
    assert data["result_set_complete"] is False
    assert data["top_n_applied"] == 10
