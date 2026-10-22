import inspect
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.hpo_tool import HPOTool
from tooluniverse.tools.HPO_get_diseases_by_phenotype import (
    HPO_get_diseases_by_phenotype,
)
from tooluniverse.tools.HPO_get_genes_by_phenotype import HPO_get_genes_by_phenotype


@pytest.mark.parametrize(
    "endpoint,kind",
    [
        ("get_associated_genes", "genes"),
        ("get_associated_diseases", "diseases"),
    ],
)
@patch("tooluniverse.hpo_tool.requests.get")
def test_association_pages_expose_machine_readable_continuation(
    mock_get, endpoint, kind
):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        kind: [{"id": f"ID:{i}", "name": f"Item {i}"} for i in range(7)]
    }
    mock_get.return_value = response

    result = HPOTool({"fields": {"endpoint": endpoint}}).run(
        {"term_id": "HP:0001250", "limit": 3, "offset": 3}
    )

    assert [row["id"] for row in result["data"][kind]] == ["ID:3", "ID:4", "ID:5"]
    metadata = result["metadata"]
    assert metadata["total"] == 7
    assert metadata["returned"] == 3
    assert metadata["offset"] == 3
    assert metadata["limit"] == 3
    assert metadata["has_more"] is True
    assert metadata["next_offset"] == 6
    assert metadata["result_set_complete"] is False


def test_generated_hpo_association_wrappers_expose_offset():
    for function in (
        HPO_get_genes_by_phenotype,
        HPO_get_diseases_by_phenotype,
    ):
        parameters = inspect.signature(function).parameters
        assert parameters["limit"].default == 50
        assert parameters["offset"].default == 0
