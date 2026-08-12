"""MCP registration tests for the official Boltz API tool family."""

from __future__ import annotations

import json

import pytest
from jsonschema import Draft202012Validator

from tooluniverse.smcp import SMCP


def _prediction_input() -> dict:
    return {
        "entities": [
            {
                "type": "protein",
                "value": "MKTIIALSYIFCLVFA",
                "chain_ids": ["A"],
            },
            {
                "type": "ligand_smiles",
                "value": "CC(=O)OC1=CC=CC=C1C(=O)O",
                "chain_ids": ["B"],
            },
        ],
        "binding": {
            "type": "ligand_protein_binding",
            "binder_chain_id": "B",
        },
        "num_samples": 1,
    }


@pytest.mark.mcp
@pytest.mark.asyncio
async def test_all_boltz_tools_are_exposed_with_exact_schema(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BOLTZ_API_KEY", "sk_bc_ws_test_mcp-schema-only")
    server = SMCP(
        name="Boltz MCP schema test",
        tool_categories=["boltz_api"],
        search_enabled=False,
        max_workers=1,
    )

    try:
        tools = await server.get_tools()
        boltz_tools = {
            name: tool for name, tool in tools.items() if name.startswith("Boltz_")
        }
        assert len(boltz_tools) == 69

        start_tool = boltz_tools["Boltz_start_structure_binding"]
        mcp_schema = start_tool.parameters
        Draft202012Validator.check_schema(mcp_schema)
        assert set(mcp_schema["required"]) == {"input", "idempotency_key"}
        assert not list(
            Draft202012Validator(mcp_schema).iter_errors(
                {
                    "input": _prediction_input(),
                    "idempotency_key": "stable-mcp-test-key-001",
                }
            )
        )

        # FastMCP normalizes local $defs/$ref nodes into an equivalent
        # dereferenced schema. Verify representative discriminators survived.
        serialized_schema = json.dumps(mcp_schema)
        for entity_type in {"protein", "rna", "dna", "ligand_smiles"}:
            assert f'"const": "{entity_type}"' in serialized_schema

        invalid_result = await start_tool.run(
            {
                "input": {
                    "entities": [
                        {
                            "type": "unsupported_entity",
                            "value": "MKTIIALSYIFCLVFA",
                            "chain_ids": ["A"],
                        }
                    ],
                    "num_samples": 1,
                },
                "idempotency_key": "invalid-nested-mcp-input-001",
            }
        )
        invalid_payload = json.loads(invalid_result.content[0].text)
        assert invalid_payload["status"] == "error"
        assert "Parameter validation failed" in invalid_payload["error"]

        server.tooluniverse.run_one_function = lambda call, stream_callback=None: {
            "status": "success",
            "echo": call,
        }
        result = await start_tool.run(
            {
                "input": _prediction_input(),
                "idempotency_key": "stable-mcp-test-key-001",
            }
        )
        payload = json.loads(result.content[0].text)
        assert payload["echo"]["name"] == "Boltz_start_structure_binding"
        assert payload["echo"]["arguments"]["input"] == _prediction_input()
    finally:
        await server.close()
