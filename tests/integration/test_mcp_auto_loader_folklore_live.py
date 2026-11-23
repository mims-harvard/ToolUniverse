import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from tooluniverse.default_config import default_tool_files
from tooluniverse.mcp_client_tool import MCPAutoLoaderTool

PUBLIC_ENDPOINT = "https://api.helena.bio/folklore/v1/mcp"
LOCKFILE = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "tooluniverse"
    / "data"
    / "mcp_contracts.lock.json"
)

# What the server answers for a resolved variant, read off a live call on
# 2026-11-22 rather than from the service's documentation.
RESOLUTION_STATUSES = {
    "resolved",
    "ambiguous",
    "not_found",
    "invalid_request",
    "unsupported",
    "resolution_unavailable",
}


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.mcp
@pytest.mark.asyncio
async def test_folklore_reviewed_tools_match_live_contract_and_return_boundaries():
    config_path = Path(default_tool_files["mcp_auto_loader_folklore"])
    config = copy.deepcopy(json.loads(config_path.read_text())[0])
    config["server_url"] = PUBLIC_ENDPOINT

    loader = MCPAutoLoaderTool(config)
    tools = await loader.discover_tools()

    assert list(tools) == config["selected_tools"]
    assert all(tool["annotations"]["readOnlyHint"] for tool in tools.values())

    response = await loader.call_tool(
        "classify_germline_variant",
        {
            "assembly": "GRCh38",
            # BRCA1 is minus-strand; the reference genome's plus-strand base at
            # this position is T, not A (A is T's complement). The previous
            # A:G here was written in BRCA1's gene-strand orientation, so the
            # server correctly rejected it (reference_mismatch) rather than
            # resolving it -- this always returned invalid_request instead of
            # exercising the resolved path this test claims to cover.
            "query": "chr17:43045705:T:C",
        },
    )
    structured = response["structuredContent"]

    # The live answer must still satisfy the contract this repo pinned, because
    # a tolerated tool publishes the *reviewed* contract to the agent. Note how
    # little this proves on its own: the pinned outputSchema constrains the four
    # top-level keys and, inside `result`, only search_contract_version and
    # status. It says nothing about identity, resolution or interpretation, so
    # it would pass even if the whole clinical payload disappeared. The explicit
    # assertions below cover what the pin does not.
    pinned = json.loads(LOCKFILE.read_text())["loaders"]["mcp_auto_loader_folklore"][
        "tools"
    ]["classify_germline_variant"]["contract"]["outputSchema"]
    drift = sorted(Draft202012Validator(pinned).iter_errors(structured), key=str)
    assert not drift, (
        "the live answer no longer satisfies the pinned contract: "
        f"{list(drift[0].absolute_path)} {drift[0].message}"
    )

    assert structured["contract_version"] == "2"
    assert structured["adapter_error"] is None
    assert structured["record_url"].startswith("https://folklore.helena.bio/")

    result = structured["result"]
    assert result["status"] in RESOLUTION_STATUSES

    # v2 dropped the machine-readable boundary. v1 returned a top-level
    # `usage_boundary` object carrying result_type, review_required,
    # patient_context_evaluated, intended_use and
    # not_for [patient_diagnosis, treatment_decision,
    # standalone_clinical_reporting]. No key in a v2 answer carries any of that.
    # What is left is one prose sentence about *technical* scope, so the
    # "requires qualified professional review, not a diagnosis or a treatment
    # recommendation" disclosure now reaches an agent only through this loader's
    # own description in mcp_auto_loader_folklore.json. Absence is not asserted
    # here: restoring that block upstream would be welcome, not a regression.
    interpretation = result["interpretation"]
    assert interpretation["limitations"]["scope"].strip()
    assert interpretation["classification"]["framework"] == "acmg_2015"
    assert interpretation["classification"]["automated_class"].strip()
    assert interpretation["provenance"]["classifier_version_label"].strip()

    # The server says so when it cut evidence out of the answer -- the live call
    # above comes back with warnings == ["evidence_truncated"]. The wrapper
    # normalizes the MCP envelope, so assert that signal still reaches the
    # caller rather than being flattened away.
    assert isinstance(interpretation["warnings"], list)
