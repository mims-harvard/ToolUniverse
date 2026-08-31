import copy
import json
from pathlib import Path

import pytest

from tooluniverse.default_config import default_tool_files
from tooluniverse.mcp_client_tool import MCPAutoLoaderTool

PUBLIC_ENDPOINT = "https://api.helena.bio/folklore/v1/mcp"


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
        "search_variant_evidence",
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

    assert structured["contract_version"] == "1"
    assert structured["adapter_error"] is None
    assert structured["result"]["status"] in {
        "resolved",
        "ambiguous",
        "not_found",
        "invalid_request",
        "unsupported",
        "resolution_unavailable",
    }
    assert structured["usage_boundary"] == {
        "result_type": "automated_variant_level_classification",
        "review_required": True,
        "patient_context_evaluated": False,
        "intended_use": "professional_variant_review",
        "not_for": [
            "patient_diagnosis",
            "treatment_decision",
            "standalone_clinical_reporting",
        ],
    }
