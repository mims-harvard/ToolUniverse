"""Unit and registration tests for the complete official Boltz API SDK tools."""

from __future__ import annotations

import json
import inspect
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator, ValidationError

from tooluniverse import ToolUniverse
from tooluniverse._lazy_registry_static import STATIC_LAZY_REGISTRY
from tooluniverse.boltz_api_tool import BoltzAPITool
from tooluniverse.default_config import default_tool_files


CONFIG_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "tooluniverse"
    / "data"
    / "boltz_api_tools.json"
)


def _configs() -> list[dict]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _config(name: str) -> dict:
    return next(config for config in _configs() if config["name"] == name)


@pytest.mark.unit
def test_checked_in_config_matches_official_sdk_generator(tmp_path):
    """The static registry must be reproducible from the pinned official SDK."""

    generated_path = tmp_path / "boltz_api_tools.json"
    subprocess.run(
        [
            sys.executable,
            str(CONFIG_PATH.parents[3] / "scripts" / "generate_boltz_api_tools.py"),
            "--output",
            str(generated_path),
        ],
        check=True,
    )
    assert generated_path.read_text(encoding="utf-8") == CONFIG_PATH.read_text(
        encoding="utf-8"
    )


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def to_dict(self, *, mode: str):
        assert mode == "json"
        return self.payload


class FakeResource:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []
        self.failure = None

    def __getattr__(self, operation):
        def invoke(*args, **kwargs):
            self.calls.append((operation, args, kwargs))
            if self.failure is not None:
                raise self.failure
            return FakeResponse(self.payload)

        return invoke


def _set_nested_resource(root, resource_path: str, resource) -> None:
    target = root
    components = resource_path.split(".")
    for component in components[:-1]:
        child = getattr(target, component, None)
        if child is None:
            child = SimpleNamespace()
            setattr(target, component, child)
        target = child
    setattr(target, components[-1], resource)


def _tool_with_fake_client(config: dict, payload):
    resource = FakeResource(payload)
    client = SimpleNamespace()
    _set_nested_resource(client, config["fields"]["resource"], resource)
    tool = BoltzAPITool(config)
    tool._client = client
    return tool, resource


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


def _minimal_arguments(config: dict) -> dict:
    fields = config["fields"]
    arguments = {}
    for name in fields.get("positional_parameters", []):
        arguments[name] = f"{name}_account_scoped_value"
    if fields.get("require_idempotency"):
        arguments["idempotency_key"] = "stable-test-key-001"
    if fields.get("confirmation_message"):
        arguments["confirm"] = True
    if fields["resource"] == "predictions.structure_and_binding" and fields[
        "operation"
    ] in {"estimate_cost", "start"}:
        arguments["input"] = _prediction_input()
    return arguments


def _success_payload(config: dict):
    name = config["name"]
    operation = config["fields"]["operation"]
    if operation == "estimate_cost":
        return {
            "estimated_cost_usd": "0.0250",
            "breakdown": {"application": "test", "num_units": 1},
            "disclaimer": "Estimate only",
        }
    if operation == "run":
        return "/tmp/boltz-experiments/tooluniverse-test"
    if operation in {"list", "list_results"}:
        return {
            "data": [],
            "has_more": False,
            "first_id": None,
            "last_id": None,
        }
    if operation == "delete_data":
        return {
            "id": "job_account_scoped_id",
            "data_deleted_at": "2026-08-11T00:00:00Z",
        }
    if name == "Boltz_create_api_key":
        return {
            "key": "sk_bc_ws_returned-once",
            "key_details": {"id": "key_123"},
        }
    if name == "Boltz_get_auth_context":
        return {"principal_type": "api_key", "key_type": "workspace"}
    if name == "Boltz_get_cli_version":
        return {
            "latest": "0.46.0",
            "minimum_supported": "0.40.0",
            "update_available": False,
            "update_required": False,
        }
    if "spending_limit" in name:
        return None
    if "workspace" in name:
        return {"id": "ws_123", "name": "Research"}
    if name == "Boltz_revoke_api_key":
        return {"id": "key_123", "revoked": True}
    return {
        "id": "job_account_scoped_id",
        "status": "pending",
        "output": None,
        "error": None,
    }


@pytest.mark.unit
def test_original_three_tools_remain_compatible():
    estimate_config = _config("Boltz_estimate_structure_binding_cost")
    estimate, estimate_resource = _tool_with_fake_client(
        estimate_config, _success_payload(estimate_config)
    )

    result = estimate.run({"input": _prediction_input()})

    assert result["status"] == "success"
    assert result["data"]["estimated_cost_usd"] == "0.0250"
    assert estimate_resource.calls == [
        (
            "estimate_cost",
            (),
            {"input": _prediction_input(), "model": "boltz-2.1"},
        )
    ]

    start_config = _config("Boltz_start_structure_binding")
    start, start_resource = _tool_with_fake_client(
        start_config, _success_payload(start_config)
    )
    missing = start.run({"input": _prediction_input()})
    assert missing == {
        "status": "error",
        "error": "idempotency_key is required for submission to prevent duplicate billing",
    }
    assert start_resource.calls == []

    retrieve_config = _config("Boltz_get_structure_binding")
    retrieve, retrieve_resource = _tool_with_fake_client(
        retrieve_config, _success_payload(retrieve_config)
    )
    result = retrieve.run({"id": "sab_pred_123", "workspace_id": "ws_123"})
    assert result["status"] == "success"
    assert retrieve_resource.calls == [
        ("retrieve", ("sab_pred_123",), {"workspace_id": "ws_123"})
    ]


@pytest.mark.unit
def test_legacy_self_hosted_boltz_tools_are_preserved():
    assert "mcp_auto_loader_boltz" in default_tool_files
    assert "boltz_api" in default_tool_files
    assert STATIC_LAZY_REGISTRY["Boltz2DockingTool"] == "boltz_tool"
    assert STATIC_LAZY_REGISTRY["BoltzAPITool"] == "boltz_api_tool"

    legacy_config = json.loads(
        Path(default_tool_files["mcp_auto_loader_boltz"]).read_text(encoding="utf-8")
    )[0]
    assert legacy_config["name"] == "mcp_auto_loader_boltz"
    assert legacy_config["type"] == "MCPAutoLoaderTool"
    assert legacy_config["server_url"].endswith(":8080/mcp")


@pytest.mark.unit
def test_all_69_official_sdk_operations_are_configured():
    configs = _configs()
    expected = {
        (resource, operation)
        for resource, operations in BoltzAPITool.SUPPORTED_RESOURCES.items()
        for operation in operations
    }
    actual = {
        (config["fields"]["resource"], config["fields"]["operation"])
        for config in configs
    }

    assert len(configs) == 69
    assert len(expected) == 69
    assert actual == expected
    assert len({config["name"] for config in configs}) == 69
    assert {
        "Boltz_estimate_structure_binding_cost",
        "Boltz_start_structure_binding",
        "Boltz_get_structure_binding",
    }.issubset({config["name"] for config in configs})
    assert {
        "Boltz_run_structure_binding",
        "Boltz_run_adme",
        "Boltz_run_protein_design",
        "Boltz_run_protein_library_screen",
        "Boltz_run_small_molecule_design",
        "Boltz_run_small_molecule_library_screen",
    }.issubset({config["name"] for config in configs})


@pytest.mark.unit
def test_all_configs_are_valid_and_sdk_derived():
    configs = _configs()
    assert (
        sum(config.get("mcp_schema_mode") == "passthrough" for config in configs) == 23
    )
    assert sum("api_key_info" in config for config in configs) == 1

    for config in configs:
        assert len(config["name"]) <= 55
        assert config["type"] == "BoltzAPITool"
        assert config["required_api_keys"] == ["BOLTZ_API_KEY"]
        assert config["required_packages"] == ["boltz_api"]
        assert config["fields"]["sdk_version"] == "0.46.0"
        assert config["parameter"].get("additionalProperties") is False
        if "$defs" in config["parameter"]:
            assert config["mcp_schema_mode"] == "passthrough"
        else:
            assert "mcp_schema_mode" not in config
        assert "oneOf" in config["return_schema"]
        Draft202012Validator.check_schema(config["parameter"])
        Draft202012Validator.check_schema(config["return_schema"])


@pytest.mark.unit
def test_configs_map_to_real_official_sdk_methods():
    boltz_api = pytest.importorskip("boltz_api")
    client = boltz_api.Boltz(api_key="test-signature-inspection-only")

    for resource_path, expected_operations in BoltzAPITool.SUPPORTED_RESOURCES.items():
        resource = client
        for component in resource_path.split("."):
            resource = getattr(resource, component)
        public_operations = {
            name
            for name in dir(resource)
            if not name.startswith("_")
            and name not in {"with_raw_response", "with_streaming_response"}
            and callable(getattr(resource, name))
        }
        assert public_operations == expected_operations, resource_path

    for config in _configs():
        resource = client
        for component in config["fields"]["resource"].split("."):
            resource = getattr(resource, component)
        method = getattr(resource, config["fields"]["operation"])
        signature = inspect.signature(method)
        exposed = set(config["parameter"].get("properties", {})) - {"confirm"}
        sdk_parameters = set(signature.parameters) - {
            "extra_headers",
            "extra_query",
            "extra_body",
            "timeout",
        }

        assert exposed == sdk_parameters, config["name"]
        for name in config["fields"].get("positional_parameters", []):
            assert signature.parameters[name].kind in {
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            }


@pytest.mark.unit
def test_all_operations_dispatch_and_match_declared_return_schema():
    for config in _configs():
        payload = _success_payload(config)
        tool, resource = _tool_with_fake_client(config, payload)
        arguments = _minimal_arguments(config)

        result = tool.run(arguments)

        assert result["status"] == "success", config["name"]
        Draft202012Validator(config["return_schema"]).validate(result)
        assert len(resource.calls) == 1
        operation, positional, kwargs = resource.calls[0]
        assert operation == config["fields"]["operation"]
        assert "confirm" not in kwargs
        assert len(positional) == len(config["fields"].get("positional_parameters", []))


@pytest.mark.unit
def test_every_paid_start_requires_idempotency_key():
    start_configs = [
        config for config in _configs() if config["fields"]["operation"] == "start"
    ]
    assert len(start_configs) == 7

    for config in start_configs:
        assert config["fields"]["require_idempotency"] is True
        assert "idempotency_key" in config["parameter"]["required"]
        tool, resource = _tool_with_fake_client(config, _success_payload(config))
        arguments = _minimal_arguments(config)
        arguments.pop("idempotency_key")
        result = tool.run(arguments)
        assert result["status"] == "error"
        assert "idempotency_key" in result["error"]
        assert resource.calls == []


@pytest.mark.unit
def test_mutating_operations_require_and_strip_confirmation():
    protected = [
        config for config in _configs() if config["fields"].get("confirmation_message")
    ]
    assert len(protected) == 23

    for config in protected:
        assert "confirm" in config["parameter"]["required"]
        tool, resource = _tool_with_fake_client(config, _success_payload(config))
        arguments = _minimal_arguments(config)
        arguments.pop("confirm")
        result = tool.run(arguments)
        assert result["status"] == "error"
        assert "confirm=true" in result["error"]
        assert resource.calls == []

        arguments["confirm"] = True
        assert tool.run(arguments)["status"] == "success"
        assert "confirm" not in resource.calls[0][2]


@pytest.mark.unit
def test_official_schema_preserves_complex_supported_inputs():
    structure = _config("Boltz_start_structure_binding")["parameter"]
    entity_refs = structure["properties"]["input"]["$ref"]
    assert entity_refs == "#/$defs/Input"
    assert "InputTemplate" in structure["$defs"]
    assert "InputConstraintContactConstraint" in structure["$defs"]

    protein_design = _config("Boltz_start_protein_design")["parameter"]
    assert "BinderSpecificationBoltzCuratedBinderSpec" in protein_design["$defs"]
    assert "BinderSpecificationStructureTemplateBinderSpec" in protein_design["$defs"]

    small_molecule = _config("Boltz_start_small_molecule_design")["parameter"]
    assert "MoleculeFiltersCustomFilterRdkitDescriptorFilter" in small_molecule["$defs"]

    sequence_redesign = _config("Boltz_start_protein_sequence_redesign")["parameter"]
    assert set(sequence_redesign["properties"]) == {
        "entities",
        "num_proteins",
        "structure",
        "type",
        "global_design_filters",
        "idempotency_key",
        "workspace_id",
    }
    assert set(sequence_redesign["required"]) == {
        "entities",
        "num_proteins",
        "structure",
        "type",
        "idempotency_key",
    }
    Draft202012Validator(sequence_redesign).validate(
        {
            "entities": [
                {"chain_id": "A", "role": "target", "type": "from_template"},
                {"chain_id": "B", "role": "binder", "type": "from_template"},
            ],
            "num_proteins": 1,
            "structure": {"type": "url", "url": "https://example.org/input.cif"},
            "type": "binder",
            "idempotency_key": "stable-sequence-redesign-test-key",
        }
    )
    Draft202012Validator(sequence_redesign).validate(
        {
            "entities": [{"chain_id": "A", "type": "from_template"}],
            "num_proteins": 1,
            "structure": {"type": "url", "url": "https://example.org/input.cif"},
            "type": "generic",
            "idempotency_key": "stable-generic-redesign-test-key",
        }
    )
    with pytest.raises(ValidationError):
        Draft202012Validator(sequence_redesign).validate(
            {
                "entities": [{"chain_id": "A", "type": "from_template"}],
                "num_proteins": 1,
                "structure": {
                    "type": "url",
                    "url": "https://example.org/input.cif",
                },
                "type": "unsupported",
                "idempotency_key": "stable-invalid-redesign-test-key",
            }
        )


@pytest.mark.unit
def test_mcp_annotations_match_remote_side_effects():
    read_only = {
        "estimate_cost",
        "retrieve",
        "list",
        "list_results",
        "retrieve_spending_limit",
        "me",
        "version",
    }
    destructive = {"delete_data", "stop", "archive", "revoke"}

    for config in _configs():
        operation = config["fields"]["operation"]
        assert config["mcp_annotations"] == {
            "readOnlyHint": operation in read_only,
            "destructiveHint": operation in destructive,
        }, config["name"]


@pytest.mark.unit
def test_sdk_error_body_is_normalized():
    config = _config("Boltz_start_structure_binding")
    tool, resource = _tool_with_fake_client(config, _success_payload(config))

    class FakeSDKError(Exception):
        status_code = 422
        message = "Request validation failed"
        body = {
            "error": {
                "code": "bad_request",
                "message": "Invalid binder chain",
                "details": {"input.binding.binder_chain_id": "Chain Z was not found"},
            }
        }

    resource.failure = FakeSDKError()
    result = tool.run(
        {
            "input": _prediction_input(),
            "idempotency_key": "invalid-binding-001",
        }
    )

    assert result == {
        "status": "error",
        "error": "Invalid binder chain",
        "status_code": 422,
        "code": "bad_request",
        "details": {"input.binding.binder_chain_id": "Chain Z was not found"},
    }


@pytest.mark.unit
def test_sdk_run_path_is_serialized_for_json_clients():
    path = Path("/tmp/boltz-experiments/tooluniverse-test")
    assert BoltzAPITool._serialize_response(path) == str(path)


@pytest.mark.unit
def test_client_is_lazy_and_reads_environment(monkeypatch):
    captured = {}

    class FakeBoltz:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setenv("BOLTZ_API_KEY", "sk_bc_ws_test_not-a-real-secret")
    monkeypatch.setitem(sys.modules, "boltz_api", SimpleNamespace(Boltz=FakeBoltz))

    tool = BoltzAPITool(_config("Boltz_get_auth_context"))
    client = tool._get_client()

    assert isinstance(client, FakeBoltz)
    assert captured == {
        "api_key": "sk_bc_ws_test_not-a-real-secret",
        "timeout": 60,
        "max_retries": 2,
    }
    assert tool._get_client() is client


@pytest.mark.unit
def test_missing_api_key_returns_actionable_error(monkeypatch):
    monkeypatch.delenv("BOLTZ_API_KEY", raising=False)
    tool = BoltzAPITool(_config("Boltz_get_auth_context"))

    result = tool.run({})

    assert result["status"] == "error"
    assert result["error"].startswith("BOLTZ_API_KEY is required")


@pytest.mark.unit
def test_invalid_dispatch_and_original_inputs_fail_before_sdk_calls():
    bad_config = dict(_config("Boltz_get_auth_context"))
    bad_config["fields"] = {
        "resource": "auth",
        "operation": "delete_everything",
    }
    tool, resource = _tool_with_fake_client(bad_config, {})
    assert tool.run({})["status"] == "error"
    assert resource.calls == []

    config = _config("Boltz_estimate_structure_binding_cost")
    estimate, estimate_resource = _tool_with_fake_client(
        config, _success_payload(config)
    )
    assert estimate.run({"input": {}}) == {
        "status": "error",
        "error": "input.entities must be a non-empty array",
    }
    assert estimate.run({"input": _prediction_input(), "model": "boltz-3"}) == {
        "status": "error",
        "error": "model must be 'boltz-2.1'",
    }
    assert estimate_resource.calls == []


@pytest.mark.unit
def test_boltz_api_tools_register_without_network(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BOLTZ_API_KEY", "sk_bc_ws_test_registration-only")
    tu = ToolUniverse()
    tu.load_tools(tool_type=["boltz_api"])

    expected_names = {config["name"] for config in _configs()}
    registered_names = {
        name
        for name, config in tu.all_tool_dict.items()
        if config.get("type") == "BoltzAPITool"
    }
    assert registered_names == expected_names
    for name in expected_names:
        assert hasattr(tu.tools, name)
