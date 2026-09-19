"""Europe PMC annotation searches must forward pageSize, including zero."""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.europepmc_annotations_tool import EuroPMCAnnotationsTool

pytestmark = pytest.mark.unit


def test_batch_query_sends_zero_page_size():
    tool = EuroPMCAnnotationsTool(
        {
            "name": "europepmc_annotations_batch",
            "fields": {"endpoint_type": "batch_by_type"},
        }
    )
    response = MagicMock()
    response.json.return_value = []
    response.raise_for_status.return_value = None

    with patch(
        "tooluniverse.europepmc_annotations_tool.requests.get", return_value=response
    ) as get:
        result = tool.run(
            {
                "article_ids": "PMC:PMC4353746",
                "annotation_type": "Chemicals",
                "page_size": 0,
            }
        )

    assert get.call_args.kwargs["params"]["pageSize"] == 0
    assert result["status"] == "success"
    assert result["data"]["total_annotations"] == 0
