"""The coding wrapper must expose ChEMBL's implemented field projection."""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.tools.ChEMBL_get_target_assays import ChEMBL_get_target_assays

pytestmark = pytest.mark.unit


def test_target_assays_wrapper_forwards_fields_with_page_arguments():
    client = MagicMock()
    client.run_one_function.return_value = {"status": "success"}

    with patch(
        "tooluniverse.tools.ChEMBL_get_target_assays.get_shared_client",
        return_value=client,
    ):
        ChEMBL_get_target_assays(
            "CHEMBL2074",
            limit=2,
            offset=2,
            fields=["assay_chembl_id", "confidence_score"],
        )

    request = client.run_one_function.call_args.args[0]
    assert request == {
        "name": "ChEMBL_get_target_assays",
        "arguments": {
            "target_chembl_id__exact": "CHEMBL2074",
            "limit": 2,
            "offset": 2,
            "fields": ["assay_chembl_id", "confidence_score"],
        },
    }
