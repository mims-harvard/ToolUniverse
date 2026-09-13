"""Completed ID-mapping jobs can contain only failedIds, without results."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import requests

from tooluniverse.uniprot_idmapping_tool import UniProtIDMappingTool
from tooluniverse.uniprot_tool import UniProtRESTTool

pytestmark = pytest.mark.unit


def response(body):
    result = requests.Response()
    result.status_code = 200
    result._content = json.dumps(body).encode()
    return result


@pytest.mark.parametrize("wrapper", ["mapping", "rest"])
def test_failed_only_completed_job_returns_failed_ids_without_polling_again(wrapper):
    """Unmappable inputs are a completed result, not a still-running job."""
    failed_ids = ["NOTAREALACC99"]
    if wrapper == "mapping":
        tool = UniProtIDMappingTool(
            {"name": "test", "fields": {"endpoint_type": "convert"}}
        )
        arguments = {
            "ids": "NOTAREALACC99",
            "from_db": "UniProtKB_AC-ID",
            "to_db": "PDB",
        }
    else:
        configs = json.loads(
            (
                Path(__file__).resolve().parents[2]
                / "src/tooluniverse/data/uniprot_tools.json"
            ).read_text()
        )
        tool = UniProtRESTTool(
            next(config for config in configs if config["name"] == "UniProt_id_mapping")
        )
        arguments = {"ids": failed_ids, "from_db": "UniProtKB_AC-ID", "to_db": "PDB"}

    with (
        patch("requests.post", return_value=response({"jobId": "test-job"})),
        patch(
            "requests.get",
            side_effect=lambda *args, **kwargs: response({"failedIds": failed_ids}),
        ) as get,
        patch(
            "time.sleep", side_effect=AssertionError("completed jobs must not sleep")
        ) as sleep,
    ):
        result = tool.run(arguments)

    assert result["status"] == "success", result
    assert result["data"]["results"] == []
    assert result["data"]["failed_ids"] == failed_ids
    sleep.assert_not_called()
    assert sum("/status/" in call.args[0] for call in get.call_args_list) == 1
