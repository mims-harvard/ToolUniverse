#!/usr/bin/env python3
"""Generate ToolUniverse configs from the official boltz-api TypedDict models."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

if __package__:
    from .sdk_schema_utils import typed_dict_params_schema
else:
    from sdk_schema_utils import typed_dict_params_schema


OUTPUT = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "tooluniverse"
    / "data"
    / "boltz_api_tools.json"
)

PRODUCTS = [
    {
        "resource": "predictions.structure_and_binding",
        "slug": "structure_binding",
        "label": "structure-and-binding prediction",
        "namespace": "predictions",
        "base": "structure_and_binding",
        "operations": ["estimate_cost", "start", "retrieve", "list", "delete_data"],
        "run": True,
    },
    {
        "resource": "predictions.adme",
        "slug": "adme",
        "label": "ADME prediction",
        "namespace": "predictions",
        "base": "adme",
        "operations": ["estimate_cost", "start", "retrieve", "list", "delete_data"],
        "run": True,
    },
    {
        "resource": "protein.design",
        "slug": "protein_design",
        "label": "protein-design pipeline",
        "namespace": "protein",
        "base": "design",
        "operations": [
            "estimate_cost",
            "start",
            "retrieve",
            "list",
            "list_results",
            "resume",
            "stop",
            "delete_data",
        ],
        "run": True,
    },
    {
        "resource": "protein.sequence_redesign",
        "slug": "protein_sequence_redesign",
        "label": "protein sequence-redesign pipeline",
        "namespace": "protein",
        "base": "sequence_redesign",
        "operations": [
            "estimate_cost",
            "start",
            "retrieve",
            "list",
            "list_results",
            "resume",
            "stop",
            "delete_data",
        ],
    },
    {
        "resource": "protein.library_screen",
        "slug": "protein_library_screen",
        "label": "protein-library screen",
        "namespace": "protein",
        "base": "library_screen",
        "operations": [
            "estimate_cost",
            "start",
            "retrieve",
            "list",
            "list_results",
            "resume",
            "stop",
            "delete_data",
        ],
        "run": True,
    },
    {
        "resource": "small_molecule.design",
        "slug": "small_molecule_design",
        "label": "small-molecule design pipeline",
        "namespace": "small_molecule",
        "base": "design",
        "operations": [
            "estimate_cost",
            "start",
            "retrieve",
            "list",
            "list_results",
            "resume",
            "stop",
            "delete_data",
        ],
        "run": True,
    },
    {
        "resource": "small_molecule.library_screen",
        "slug": "small_molecule_library_screen",
        "label": "small-molecule library screen",
        "namespace": "small_molecule",
        "base": "library_screen",
        "operations": [
            "estimate_cost",
            "start",
            "retrieve",
            "list",
            "list_results",
            "resume",
            "stop",
            "delete_data",
        ],
        "run": True,
    },
]

PARAMETER_DESCRIPTIONS = {
    "id": "Account-scoped job or prediction ID returned by the matching start or list tool.",
    "workspace_id": "Workspace ID. Required as a path identifier for workspace operations; otherwise only needed with an admin key.",
    "api_key_id": "API key ID returned by the key creation or listing tool; this is not the secret key value.",
    "idempotency_key": "Stable caller-generated key used to prevent duplicate submissions and duplicate billing.",
    "after_id": "Return the page after this cursor ID; mutually exclusive with before_id.",
    "before_id": "Return the page before this cursor ID; mutually exclusive with after_id.",
    "limit": "Maximum number of records in this page, subject to the official API limit.",
    "ids": "Optional comma-separated result IDs to select.",
    "input": "Official application-specific request object; follow the nested schema and discriminator fields exactly.",
    "model": "Official model identifier accepted by this endpoint.",
    "binder_specification": "Protein binder specification: no-template, structure-template, or Boltz-curated mode, following the nested discriminator schema.",
    "num_proteins": "Number of protein candidates to generate or price, within the endpoint's official limits.",
    "target": "Application-specific target definition, including sequences, structures, chains, bonds, or constraints as described by the nested schema.",
    "entities": "Protein sequence-redesign entities and their designable motifs, following the selected binder or generic request type.",
    "structure": "URL or base64 structure input used for protein sequence redesign.",
    "type": "Official request discriminator; its allowed literal values determine the matching nested input shape.",
    "global_design_filters": "Optional global amino-acid, motif, or hydrophobicity filters applied to generated proteins.",
    "proteins": "Protein candidates to screen, expressed in the official sequence or structure input format.",
    "num_molecules": "Number of small molecules to generate or price, within the endpoint's official limits.",
    "chemical_space": "Chemical-space constraint: Enamine REAL or none, when supported by the endpoint.",
    "molecule_filters": "Optional built-in or custom molecular filters, including Lipinski, RDKit descriptor, SMARTS, or SMILES-regex rules.",
    "molecules": "Small molecules to screen, represented using the official SMILES-based input objects.",
    "data_retention": "Workspace result-retention duration using the official hours/days object.",
    "name": "Human-readable workspace or API-key name, depending on the operation.",
    "spending_limit": "Optional workspace spending-limit object applied at creation.",
    "allowed_ips": "Optional list of source IP addresses allowed to use the new API key; an empty list allows all IPs.",
    "expires_in_days": "Optional API-key lifetime in days.",
    "mode": "Create a live or test workspace API key.",
    "starting_at": "Inclusive usage-window start as an ISO 8601 timestamp.",
    "ending_at": "Exclusive usage-window end as an ISO 8601 timestamp.",
    "window_size": "Usage aggregation window: HOUR or DAY.",
    "applications": "Optional application name or list of application names to include in usage totals.",
    "group_by": "Optional grouping dimension or dimensions: workspace_id and/or application.",
    "page": "Opaque usage-pagination cursor returned by the previous page.",
    "workspace_ids": "Optional workspace ID or list of workspace IDs to include in usage totals.",
    "current": "Currently installed Boltz CLI version string.",
    "platform": "Current operating-system/platform identifier used for installation guidance.",
    "root_dir": "Local directory where the official SDK creates the experiment folder and persists downloaded results.",
    "quiet": "Suppress official SDK progress output while waiting for the run to finish.",
    "poll_interval_seconds": "Seconds between official SDK status polls while waiting for completion; must be greater than zero.",
    "download_mode": "Result download mode for design and screening runs: everything or metadata_only.",
    "run_dir": "Existing local experiment directory created by an official Boltz run or start helper.",
}

ERROR_SCHEMA = {
    "type": "object",
    "required": ["status", "error"],
    "additionalProperties": True,
    "properties": {
        "status": {"const": "error"},
        "error": {"type": "string"},
        "status_code": {"type": "integer"},
        "code": {"type": "string"},
        "details": {},
    },
}

BOLTZ_API_KEY_INFO = {
    "BOLTZ_API_KEY": {
        "domain": "Models & Infrastructure",
        "type": "api_key",
        "register_url": "https://api.boltz.bio/",
        "purpose": "Authenticate to the official hosted Boltz prediction and administration API.",
        "without": "Official hosted Boltz API tools are unavailable; the existing self-hosted Boltz MCP integration is unaffected.",
    }
}


def _camel(value: str) -> str:
    return "".join(part.capitalize() for part in value.split("_"))


def _params_schema(module_name: str | None, positional: list[str]) -> dict[str, Any]:
    return typed_dict_params_schema(
        module_name,
        positional=positional,
        descriptions=PARAMETER_DESCRIPTIONS,
    )


def _add_confirmation(schema: dict[str, Any], message: str) -> None:
    schema.setdefault("properties", {})["confirm"] = {
        "type": "boolean",
        "const": True,
        "description": message,
    }
    required = schema.setdefault("required", [])
    if "confirm" not in required:
        required.append("confirm")


def _run_params_schema(product: dict[str, Any]) -> dict[str, Any]:
    """Build the schema for the SDK's high-level submit/wait/download helper."""
    module_name = (
        f"boltz_api.types.{product['namespace']}.{product['base']}_start_params"
    )
    schema = _params_schema(module_name, [])
    properties = schema.setdefault("properties", {})
    required = schema.setdefault("required", [])

    # The high-level SDK helper owns idempotency internally and exposes local
    # experiment controls instead of the raw start method's header argument.
    properties.pop("idempotency_key", None)
    required[:] = [name for name in required if name != "idempotency_key"]
    properties.update(
        {
            "root_dir": {
                "type": "string",
                "default": "boltz-experiments",
                "description": PARAMETER_DESCRIPTIONS["root_dir"],
            },
            "name": {
                "type": "string",
                "minLength": 1,
                "description": "Stable experiment directory name. Reuse the same name when retrying this request so the SDK reuses its persisted idempotency key instead of submitting duplicate paid work.",
            },
            "quiet": {
                "type": "boolean",
                "default": False,
                "description": PARAMETER_DESCRIPTIONS["quiet"],
            },
            "poll_interval_seconds": {
                "type": "number",
                "exclusiveMinimum": 0,
                "default": 5.0,
                "description": PARAMETER_DESCRIPTIONS["poll_interval_seconds"],
            },
        }
    )
    if product["resource"] not in {
        "predictions.structure_and_binding",
        "predictions.adme",
    }:
        properties["download_mode"] = {
            "type": ["string", "null"],
            "enum": ["everything", "metadata_only", None],
            "description": PARAMETER_DESCRIPTIONS["download_mode"],
        }
    if "name" not in required:
        required.append("name")
    if not required:
        schema.pop("required", None)
    return schema


def _require_idempotency(schema: dict[str, Any]) -> None:
    required = schema.setdefault("required", [])
    if "idempotency_key" not in required:
        required.append("idempotency_key")


def _data_schema(kind: str) -> dict[str, Any]:
    if kind == "run":
        return {
            "type": "string",
            "description": "Local experiment directory created by the official Boltz SDK.",
        }
    if kind == "estimate_cost":
        return {
            "type": "object",
            "required": ["estimated_cost_usd", "breakdown"],
            "additionalProperties": True,
            "properties": {
                "estimated_cost_usd": {"type": "string"},
                "breakdown": {"type": "object", "additionalProperties": True},
                "disclaimer": {"type": ["string", "null"]},
            },
        }
    if kind in {"list", "list_results", "usage_list"}:
        properties = {
            "data": {
                "type": "array",
                "items": {"type": "object", "additionalProperties": True},
            },
            "has_more": {"type": ["boolean", "null"]},
            "first_id": {"type": ["string", "null"]},
            "last_id": {"type": ["string", "null"]},
            "next_page": {"type": ["string", "null"]},
        }
        return {
            "type": "object",
            "required": ["data"],
            "additionalProperties": True,
            "properties": properties,
        }
    if kind == "delete_data":
        return {
            "type": "object",
            "required": ["id", "data_deleted_at"],
            "additionalProperties": True,
            "properties": {
                "id": {"type": "string"},
                "data_deleted_at": {"type": "string"},
            },
        }
    if kind == "api_key_create":
        return {
            "type": "object",
            "required": ["key", "key_details"],
            "additionalProperties": True,
            "properties": {
                "key": {"type": "string"},
                "key_details": {"type": "object", "additionalProperties": True},
            },
        }
    if kind == "cli_version":
        return {
            "type": "object",
            "required": ["latest", "minimum_supported", "update_available"],
            "additionalProperties": True,
            "properties": {
                "latest": {"type": "string"},
                "minimum_supported": {"type": "string"},
                "update_available": {"type": "boolean"},
                "update_required": {"type": "boolean"},
            },
        }
    if kind in {"spending_limit_get", "spending_limit_set"}:
        return {
            "oneOf": [
                {"type": "object", "additionalProperties": True},
                {"type": "null"},
            ]
        }
    if kind == "auth_me":
        return {
            "type": "object",
            "required": ["principal_type"],
            "additionalProperties": True,
            "properties": {"principal_type": {"enum": ["api_key", "user"]}},
        }
    if kind.startswith("workspace"):
        return {
            "type": "object",
            "required": ["id"],
            "additionalProperties": True,
            "properties": {
                "id": {"type": "string"},
                "name": {"type": ["string", "null"]},
            },
        }
    if kind in {"api_key_revoke", "api_key_list"}:
        if kind == "api_key_list":
            return _data_schema("list")
        return {"type": "object", "additionalProperties": True}
    return {
        "type": "object",
        "required": ["id", "status"],
        "additionalProperties": True,
        "properties": {
            "id": {"type": "string"},
            "status": {"type": "string"},
            "output": {"type": ["object", "null"]},
            "error": {"type": ["object", "null"]},
        },
    }


def _return_schema(kind: str) -> dict[str, Any]:
    return {
        "oneOf": [
            {
                "type": "object",
                "required": ["status", "data"],
                "additionalProperties": False,
                "properties": {
                    "status": {"const": "success"},
                    "data": _data_schema(kind),
                },
            },
            ERROR_SCHEMA,
        ]
    }


def _mcp_annotations(operation: str) -> dict[str, bool]:
    """Describe remote side effects accurately to MCP clients."""

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
    return {
        "readOnlyHint": operation in read_only,
        "destructiveHint": operation in destructive,
    }


def _tool_name(slug: str, operation: str) -> str:
    prefixes = {
        "estimate_cost": "estimate",
        "start": "start",
        "retrieve": "get",
        "list": "list",
        "list_results": "list",
        "resume": "resume",
        "stop": "stop",
        "delete_data": "delete",
        "run": "run",
    }
    if operation == "estimate_cost":
        return f"Boltz_{prefixes[operation]}_{slug}_cost"
    if operation == "list_results":
        return f"Boltz_list_{slug}_results"
    if operation == "delete_data":
        return f"Boltz_delete_{slug}_data"
    return f"Boltz_{prefixes[operation]}_{slug}"


def _description(label: str, operation: str) -> str:
    descriptions = {
        "estimate_cost": f"Estimate the authoritative USD cost of an official Boltz {label} without creating a compute job. Use the matching start tool only after reviewing this estimate.",
        "start": f"Submit a paid asynchronous official Boltz {label}. Requires a stable idempotency key to prevent duplicate billing; returns the account-scoped job ID and initial status.",
        "retrieve": f"Retrieve one official Boltz {label} by its account-scoped ID, including lifecycle status, failure details, inputs, outputs, metrics, and temporary artifact URLs when available.",
        "list": f"List official Boltz {label} jobs visible to the current credential with cursor pagination and optional workspace filtering. Use returned IDs with the matching get or results tool.",
        "list_results": f"List generated results for one official Boltz {label} job with cursor pagination and optional result-ID filtering. The parent job ID comes from start or list.",
        "resume": f"Resume a stopped official Boltz {label} job. This changes remote compute state and may continue billable work, so explicit confirmation is required.",
        "stop": f"Stop an active official Boltz {label} job. This changes remote compute state and requires explicit confirmation; already generated results remain queryable when supported.",
        "delete_data": f"Permanently delete retained input and output data for one official Boltz {label} job while preserving its metadata record. This is irreversible and requires explicit confirmation.",
        "run": f"Run an official Boltz {label} end to end: submit the job, poll until completion, and persist downloaded results in a named local experiment directory. Reuse the required stable name when retrying to prevent duplicate paid submissions. Returns that directory path.",
    }
    return descriptions[operation]


def _product_tool(product: dict[str, Any], operation: str) -> dict[str, Any]:
    params_operations = {"estimate_cost", "start", "retrieve", "list", "list_results"}
    module_name = None
    if operation in params_operations:
        module_name = (
            f"boltz_api.types.{product['namespace']}."
            f"{product['base']}_{operation}_params"
        )
    positional = (
        ["id"]
        if operation in {"retrieve", "delete_data", "list_results", "resume", "stop"}
        else []
    )
    parameter = (
        _run_params_schema(product)
        if operation == "run"
        else _params_schema(module_name, positional)
    )
    fields: dict[str, Any] = {
        "resource": product["resource"],
        "operation": operation,
        "sdk_version": "0.46.0",
    }
    if positional:
        fields["positional_parameters"] = positional
    if operation == "start":
        fields["require_idempotency"] = True
        _require_idempotency(parameter)
    if operation in {"resume", "stop", "delete_data"}:
        message = {
            "resume": "confirm=true is required because resuming changes remote compute state and may continue billable work",
            "stop": "confirm=true is required because stopping changes remote compute state",
            "delete_data": "confirm=true is required because retained input/output data will be permanently deleted",
        }[operation]
        fields["confirmation_message"] = message
        _add_confirmation(parameter, message)

    if product["resource"] == "predictions.structure_and_binding" and operation in {
        "estimate_cost",
        "start",
    }:
        required = parameter.get("required", [])
        if "model" in required:
            required.remove("model")
        parameter["properties"]["model"]["default"] = "boltz-2.1"

    examples: list[dict[str, Any]] = []
    if (
        product["resource"] == "predictions.structure_and_binding"
        and operation == "estimate_cost"
    ):
        examples = [
            {
                "input": {
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
                },
                "model": "boltz-2.1",
            }
        ]
    elif operation == "list":
        examples = [{"limit": 1}]

    tool = {
        "name": _tool_name(product["slug"], operation),
        "type": "BoltzAPITool",
        "fields": fields,
        "description": _description(product["label"], operation),
        "required_api_keys": ["BOLTZ_API_KEY"],
        "required_packages": ["boltz_api"],
        "timeout": 60,
        "max_retries": 2,
        "mcp_annotations": _mcp_annotations(operation),
        "parameter": parameter,
        "test_examples": examples,
        "return_schema": _return_schema(operation),
    }
    if "$defs" in parameter:
        tool["mcp_schema_mode"] = "passthrough"
    return tool


def _admin_specs() -> list[dict[str, Any]]:
    return [
        {
            "name": "Boltz_create_workspace",
            "resource": "admin.workspaces",
            "operation": "create",
            "params": "boltz_api.types.admin.workspace_create_params",
            "kind": "workspace_create",
            "confirm": "confirm=true is required because this creates an organization workspace",
            "description": "Create an official Boltz workspace with optional name, data-retention policy, and spending limit. Requires an admin API key and explicit confirmation; returns the new workspace metadata.",
        },
        {
            "name": "Boltz_get_workspace",
            "resource": "admin.workspaces",
            "operation": "retrieve",
            "positional": ["workspace_id"],
            "kind": "workspace_retrieve",
            "description": "Retrieve one official Boltz workspace by workspace ID, including its name, archive state, default status, timestamps, and configured data-retention policy. Requires an admin API key.",
        },
        {
            "name": "Boltz_update_workspace",
            "resource": "admin.workspaces",
            "operation": "update",
            "params": "boltz_api.types.admin.workspace_update_params",
            "positional": ["workspace_id"],
            "kind": "workspace_update",
            "confirm": "confirm=true is required because this changes workspace configuration",
            "description": "Update an official Boltz workspace name or data-retention policy. Requires an admin API key and explicit confirmation; omitted fields remain unchanged.",
        },
        {
            "name": "Boltz_list_workspaces",
            "resource": "admin.workspaces",
            "operation": "list",
            "params": "boltz_api.types.admin.workspace_list_params",
            "kind": "list",
            "examples": [{"limit": 1}],
            "description": "List official Boltz workspaces using cursor pagination and optional exact-name filtering. Requires an admin API key and returns workspace IDs for subsequent management operations.",
        },
        {
            "name": "Boltz_archive_workspace",
            "resource": "admin.workspaces",
            "operation": "archive",
            "positional": ["workspace_id"],
            "kind": "workspace_archive",
            "confirm": "confirm=true is required because archiving disables the workspace",
            "description": "Archive an official Boltz workspace by workspace ID. This disables the remote workspace, requires an admin API key, and requires explicit confirmation before the mutation is sent.",
        },
        {
            "name": "Boltz_get_workspace_spending_limit",
            "resource": "admin.workspaces",
            "operation": "retrieve_spending_limit",
            "positional": ["workspace_id"],
            "kind": "spending_limit_get",
            "description": "Retrieve the lifetime spending limit currently configured for an official Boltz workspace. Requires an admin API key; returns null when no limit is configured.",
        },
        {
            "name": "Boltz_set_workspace_spending_limit",
            "resource": "admin.workspaces",
            "operation": "set_spending_limit",
            "params": "boltz_api.types.admin.workspace_set_spending_limit_params",
            "positional": ["workspace_id"],
            "kind": "spending_limit_set",
            "confirm": "confirm=true is required because this changes the workspace spending limit",
            "description": "Set the official Boltz workspace lifetime spending limit. Requires an admin API key and explicit confirmation; pass the official limit object and type='lifetime'.",
        },
        {
            "name": "Boltz_create_api_key",
            "resource": "admin.api_keys",
            "operation": "create",
            "params": "boltz_api.types.admin.api_key_create_params",
            "kind": "api_key_create",
            "confirm": "confirm=true is required because this creates a new credential whose secret is shown once",
            "description": "Create an official Boltz workspace API key with name, optional IP allow-list, expiry, mode, and workspace. Requires an admin key and confirmation; the returned secret is shown only once.",
        },
        {
            "name": "Boltz_list_api_keys",
            "resource": "admin.api_keys",
            "operation": "list",
            "params": "boltz_api.types.admin.api_key_list_params",
            "kind": "api_key_list",
            "examples": [{"limit": 1}],
            "description": "List official Boltz API-key metadata with cursor pagination and optional workspace filtering. Requires an admin key and never returns existing full secret values.",
        },
        {
            "name": "Boltz_revoke_api_key",
            "resource": "admin.api_keys",
            "operation": "revoke",
            "positional": ["api_key_id"],
            "kind": "api_key_revoke",
            "confirm": "confirm=true is required because revoking an API key is irreversible",
            "description": "Revoke an official Boltz API key by its key ID, immediately disabling that credential. Requires an admin key and explicit confirmation; pass the metadata ID, not the secret.",
        },
        {
            "name": "Boltz_list_usage",
            "resource": "admin.usage",
            "operation": "list",
            "params": "boltz_api.types.admin.usage_list_params",
            "kind": "usage_list",
            "description": "Query official Boltz usage over a required time range and hourly or daily window, optionally filtering applications/workspaces and grouping results. Requires an admin API key.",
        },
        {
            "name": "Boltz_get_auth_context",
            "resource": "auth",
            "operation": "me",
            "kind": "auth_me",
            "examples": [{}],
            "description": "Inspect the official Boltz authentication context for the current credential, including principal type, live/test mode, organization selection, and workspace scope when applicable.",
        },
        {
            "name": "Boltz_get_cli_version",
            "resource": "cli",
            "operation": "version",
            "params": "boltz_api.types.cli_version_params",
            "kind": "cli_version",
            "examples": [{}],
            "description": "Check an installed Boltz CLI version and platform against the latest and minimum supported official releases. Returns update availability, requirements, and install commands.",
        },
    ]


def _experiment_specs() -> list[dict[str, Any]]:
    """Describe the SDK's non-duplicative local experiment lifecycle helpers."""

    common_properties = {
        "run_dir": {"type": "string", "description": PARAMETER_DESCRIPTIONS["run_dir"]},
        "name": {
            "type": "string",
            "description": "Experiment directory name under root_dir.",
        },
        "root_dir": {
            "type": "string",
            "description": PARAMETER_DESCRIPTIONS["root_dir"],
        },
        "quiet": {
            "type": "boolean",
            "default": False,
            "description": PARAMETER_DESCRIPTIONS["quiet"],
        },
    }
    wait_properties = {
        **common_properties,
        "download_mode": {
            "type": ["string", "null"],
            "enum": ["everything", "metadata_only", None],
            "description": PARAMETER_DESCRIPTIONS["download_mode"],
        },
        "poll_interval_seconds": {
            "type": "number",
            "exclusiveMinimum": 0,
            "default": 5.0,
            "description": PARAMETER_DESCRIPTIONS["poll_interval_seconds"],
        },
    }
    existing_directory_requirement = {
        "oneOf": [
            {
                "required": ["run_dir"],
                "not": {
                    "anyOf": [
                        {"required": ["name"]},
                        {"required": ["root_dir"]},
                    ]
                },
            },
            {"required": ["name"], "not": {"required": ["run_dir"]}},
        ]
    }
    return [
        {
            "name": "Boltz_download_experiment_results",
            "operation": "download_results",
            "parameter": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": PARAMETER_DESCRIPTIONS["id"],
                    },
                    **wait_properties,
                    "workspace_id": {
                        "type": ["string", "null"],
                        "description": PARAMETER_DESCRIPTIONS["workspace_id"],
                    },
                },
                "anyOf": [
                    {"required": ["id"]},
                    {"required": ["run_dir"]},
                    {"required": ["name"]},
                ],
                "not": {"required": ["run_dir", "name"]},
                "additionalProperties": False,
            },
            "description": "Resume polling and download results for an existing official Boltz job ID or local experiment directory. This is the recovery path after an interrupted start/run call and returns the local experiment directory.",
        },
        {
            "name": "Boltz_wait_and_download_experiment",
            "operation": "wait_and_download",
            "parameter": {
                "type": "object",
                "properties": wait_properties,
                **existing_directory_requirement,
                "additionalProperties": False,
            },
            "description": "Resume an existing local official Boltz experiment, poll its remote job to a terminal state, and download pending results. Identify the experiment with run_dir or with name plus optional root_dir.",
        },
        {
            "name": "Boltz_stop_experiment",
            "operation": "stop",
            "parameter": {
                "type": "object",
                "properties": common_properties,
                **existing_directory_requirement,
                "additionalProperties": False,
            },
            "confirm": "confirm=true is required because stopping the local experiment changes remote compute state",
            "description": "Stop the remote pipeline recorded in an existing local official Boltz experiment directory. This changes remote compute state and requires explicit confirmation.",
        },
    ]


def _experiment_tool(spec: dict[str, Any]) -> dict[str, Any]:
    parameter = spec["parameter"]
    fields: dict[str, Any] = {
        "resource": "experiments",
        "operation": spec["operation"],
        "sdk_version": "0.46.0",
    }
    if spec.get("confirm"):
        fields["confirmation_message"] = spec["confirm"]
        _add_confirmation(parameter, spec["confirm"])
    tool = {
        "name": spec["name"],
        "type": "BoltzAPITool",
        "fields": fields,
        "description": spec["description"],
        "required_api_keys": ["BOLTZ_API_KEY"],
        "required_packages": ["boltz_api"],
        "timeout": 60,
        "max_retries": 2,
        "mcp_annotations": _mcp_annotations(spec["operation"]),
        "parameter": parameter,
        "test_examples": [],
        "return_schema": _return_schema("run"),
    }
    # These schemas have root-level alternatives (for example, id OR
    # run_dir OR name).  A Python **kwargs signature cannot advertise that
    # constraint, so preserve the authoritative schema for MCP clients.
    tool["mcp_schema_mode"] = "passthrough"
    return tool


def _admin_tool(spec: dict[str, Any]) -> dict[str, Any]:
    positional = spec.get("positional", [])
    parameter = _params_schema(spec.get("params"), positional)
    fields: dict[str, Any] = {
        "resource": spec["resource"],
        "operation": spec["operation"],
        "sdk_version": "0.46.0",
    }
    if positional:
        fields["positional_parameters"] = positional
    if spec.get("confirm"):
        fields["confirmation_message"] = spec["confirm"]
        _add_confirmation(parameter, spec["confirm"])
    tool = {
        "name": spec["name"],
        "type": "BoltzAPITool",
        "fields": fields,
        "description": spec["description"],
        "required_api_keys": ["BOLTZ_API_KEY"],
        "required_packages": ["boltz_api"],
        "timeout": 60,
        "max_retries": 2,
        "mcp_annotations": _mcp_annotations(spec["operation"]),
        "parameter": parameter,
        "test_examples": spec.get("examples", []),
        "return_schema": _return_schema(spec["kind"]),
    }
    if "$defs" in parameter:
        tool["mcp_schema_mode"] = "passthrough"
    return tool


def build_tools() -> list[dict[str, Any]]:
    """Build all official Boltz configs without writing to the repository."""

    tools = [
        _product_tool(product, operation)
        for product in PRODUCTS
        for operation in product["operations"]
    ]
    tools.extend(
        _product_tool(product, "run") for product in PRODUCTS if product.get("run")
    )
    tools.extend(_experiment_tool(spec) for spec in _experiment_specs())
    tools.extend(_admin_tool(spec) for spec in _admin_specs())

    api_key_info_tool = next(
        tool
        for tool in tools
        if tool["name"] == "Boltz_estimate_structure_binding_cost"
    )
    api_key_info_tool["api_key_info"] = BOLTZ_API_KEY_INFO

    names = [tool["name"] for tool in tools]
    if len(tools) != 72 or len(set(names)) != 72:
        raise RuntimeError(
            f"Expected 72 unique tools, found {len(tools)} / {len(set(names))}"
        )
    too_long = [name for name in names if len(name) > 55]
    if too_long:
        raise RuntimeError(f"Tool names exceed 55 characters: {too_long}")

    return tools


def render_tools(tools: list[dict[str, Any]] | None = None) -> str:
    """Render deterministic JSON suitable for the checked-in config file."""

    return json.dumps(tools if tools is not None else build_tools(), indent=2) + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT,
        help="Destination JSON path (defaults to the checked-in Boltz config)",
    )
    args = parser.parse_args(argv)

    tools = build_tools()
    args.output.write_text(render_tools(tools), encoding="utf-8")
    print(f"Generated {len(tools)} Boltz API tools at {args.output}")


if __name__ == "__main__":
    main()
