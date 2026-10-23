from unittest.mock import MagicMock, patch

from tooluniverse.tools.OpenTargets_get_diseases_phenotypes_by_target_ensembl import (
    OpenTargets_get_diseases_phenotypes_by_target_ensembl,
)


def test_generated_wrapper_forwards_page_object():
    client = MagicMock()
    client.run_one_function.return_value = {"data": {}}
    with patch(
        "tooluniverse.tools.OpenTargets_get_diseases_phenotypes_by_target_ensembl.get_shared_client",
        return_value=client,
    ):
        OpenTargets_get_diseases_phenotypes_by_target_ensembl(
            "ENSG00000141510", page={"index": 2, "size": 3}
        )

    arguments = client.run_one_function.call_args.args[0]["arguments"]
    assert arguments == {
        "ensemblId": "ENSG00000141510",
        "page": {"index": 2, "size": 3},
    }
