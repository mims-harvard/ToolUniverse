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
        assert len(boltz_tools) == 72

        estimate_tool = boltz_tools["Boltz_estimate_structure_binding_cost"]
        start_tool = boltz_tools["Boltz_start_structure_binding"]
        delete_tool = boltz_tools["Boltz_delete_structure_binding_data"]
        assert estimate_tool.annotations.readOnlyHint is True
        assert estimate_tool.annotations.destructiveHint is False
        assert start_tool.annotations.readOnlyHint is False
        assert start_tool.annotations.destructiveHint is False
        assert delete_tool.annotations.readOnlyHint is False
        assert delete_tool.annotations.destructiveHint is True

        download_tool = boltz_tools["Boltz_download_experiment_results"]
        assert download_tool.parameters["anyOf"] == [
            {"required": ["id"]},
            {"required": ["run_dir"]},
            {"required": ["name"]},
        ]

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

        sequence_redesign = boltz_tools["Boltz_start_protein_sequence_redesign"]
        assert {
            "entities",
            "num_proteins",
            "structure",
            "type",
            "global_design_filters",
            "idempotency_key",
            "workspace_id",
        } == set(sequence_redesign.parameters["properties"])

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

        redesign_arguments = {
            "entities": [
                {"chain_id": "A", "role": "target", "type": "from_template"},
                {"chain_id": "B", "role": "binder", "type": "from_template"},
            ],
            "num_proteins": 1,
            "structure": {"type": "url", "url": "https://example.org/input.cif"},
            "type": "binder",
            "idempotency_key": "stable-redesign-mcp-test-key-001",
        }
        redesign_result = await sequence_redesign.run(redesign_arguments)
        redesign_payload = json.loads(redesign_result.content[0].text)
        assert (
            redesign_payload["echo"]["name"] == "Boltz_start_protein_sequence_redesign"
        )
        assert redesign_payload["echo"]["arguments"] == redesign_arguments
    finally:
        await server.close()
