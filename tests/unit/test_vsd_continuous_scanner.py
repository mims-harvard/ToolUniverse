from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from tooluniverse.vsd_continuous_scanner import (
    VSDContinuousScannerError,
    build_continuous_scan_cycle,
    load_latest_continuous_scan,
    normalize_apis_guru_directory,
    run_scheduled_apis_guru_scan,
    summarize_continuous_scan,
    validate_continuous_scan_cycle,
    validate_directory_snapshot,
    write_continuous_scan_cycle,
)
from tooluniverse.vsd_source_intelligence import configured_source_inventory


class _ToolUniverse:
    def __init__(self, tools: list[dict] | None = None):
        tools = tools or []
        self.all_tool_dict = {tool["name"]: tool for tool in tools}
        self.all_tools = list(tools)


def _request(size: int = 1000) -> dict:
    return {
        "status_code": 200,
        "content_type": "application/json",
        "response_bytes": size,
        "redirects": 0,
    }


def _catalog(count: int, *, operations: int = 100) -> tuple[dict, dict[str, bytes]]:
    payload: dict = {}
    contracts: dict[str, bytes] = {}
    for index in range(count):
        name = f"provider{index}.example.org:service"
        version = f"1.0.{index}"
        url = f"https://api.apis.guru/v2/specs/{name}/{version}/openapi.json"
        payload[name] = {
            "preferred": version,
            "versions": {
                version: {
                    "added": "2026-08-01T00:00:00Z",
                    "info": {
                        "title": f"Provider {index} Evidence API",
                        "x-apisguru-categories": [f"category-{index % 4}"],
                    },
                    "openapiVer": "3.0.3",
                    "swaggerUrl": url,
                }
            },
        }
        document = {
            "openapi": "3.0.3",
            "info": {"title": f"Provider {index} Evidence API", "version": version},
            "servers": [{"url": f"https://provider{index}.example.org/api"}],
            "paths": {
                f"/records/{operation}": {
                    "get": {
                        "operationId": f"getRecord{operation}",
                        "responses": {
                            "200": {
                                "description": "Evidence record",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {"id": {"type": "string"}},
                                        }
                                    }
                                },
                            }
                        },
                    }
                }
                for operation in range(operations)
            },
        }
        contracts[url] = json.dumps(document, sort_keys=True).encode()
    return payload, contracts


def _directory(payload: dict, *, when: str = "2026-08-02T00:00:00+00:00") -> dict:
    return normalize_apis_guru_directory(
        payload,
        request=_request(len(json.dumps(payload))),
        retrieved_at=when,
    )


def _fetcher(contracts: dict[str, bytes]):
    def fetch(url: str, _timeout: float, maximum: int):
        raw = contracts[url]
        assert len(raw) <= maximum
        return raw, {
            "url": url,
            "redirects": 0,
            "response_bytes": len(raw),
            "content_type": "application/json",
        }

    return fetch


def test_directory_normalization_preserves_boundary_and_rejects_tampering():
    payload, _ = _catalog(3, operations=1)
    payload["legacy.example.org"] = {
        "preferred": "1.0",
        "versions": {
            "1.0": {
                "info": {"title": "Legacy"},
                "openapiVer": "2.0",
                "swaggerUrl": (
                    "https://api.apis.guru/v2/specs/legacy.example.org/1.0/swagger.json"
                ),
            }
        },
    }
    directory = _directory(payload)

    assert directory["record_count"] == 4
    assert directory["compatible_record_count"] == 3
    assert directory["unsupported_record_count"] == 1
    assert all(record["execution_allowed"] is False for record in directory["records"])
    assert validate_directory_snapshot(directory) == directory

    modified = copy.deepcopy(directory)
    modified["records"][0]["title"] = "Changed without resealing"
    with pytest.raises(VSDContinuousScannerError):
        validate_directory_snapshot(modified)


def test_scanner_builds_hundreds_of_inert_draftable_previews(tmp_path: Path):
    payload, contracts = _catalog(4, operations=100)
    existing = {
        "name": "ExistingProviderRecord",
        "vsd_operation": {
            "method": "GET",
            "endpoint": "https://provider0.example.org/api/records/0",
        },
    }
    tooluniverse = _ToolUniverse([existing])
    cycle = build_continuous_scan_cycle(
        _directory(payload),
        inventory=configured_source_inventory(tooluniverse),
        registry_tools=[existing],
        snapshot_directory=tmp_path / "contracts",
        max_contracts=4,
        draftable_tool_target=300,
        contract_fetcher=_fetcher(contracts),
        scanned_at="2026-08-02T01:00:00+00:00",
    )

    metrics = cycle["metrics"]
    assert metrics["target_reached"] is True
    assert metrics["inspected_contract_count"] == 4
    assert metrics["operation_candidate_count"] == 400
    assert metrics["draftable_tool_count"] == 399
    assert metrics["existing_exact_operation_count"] == 1
    assert metrics["blocked_operation_count"] == 0
    assert (
        len(
            {
                item["preview"]["tool_name"]
                for item in cycle["operations"]
                if item["preview"]
            }
        )
        == 399
    )
    assert all(item["execution_allowed"] is False for item in cycle["operations"])
    assert not any("config" in item for item in cycle["operations"])
    assert len(list((tmp_path / "contracts").glob("*.openapi.json"))) == 4
    assert validate_continuous_scan_cycle(cycle) == cycle


def test_incremental_cycle_rotates_to_uninspected_contracts(tmp_path: Path):
    payload, contracts = _catalog(3, operations=10)
    tooluniverse = _ToolUniverse()
    directory = _directory(payload)
    first = build_continuous_scan_cycle(
        directory,
        inventory=configured_source_inventory(tooluniverse),
        registry_tools=[],
        snapshot_directory=tmp_path / "contracts",
        max_contracts=1,
        draftable_tool_target=5,
        contract_fetcher=_fetcher(contracts),
        scanned_at="2026-08-02T01:00:00+00:00",
    )
    second = build_continuous_scan_cycle(
        directory,
        inventory=configured_source_inventory(tooluniverse),
        registry_tools=[],
        snapshot_directory=tmp_path / "contracts",
        previous_cycle=first,
        max_contracts=1,
        draftable_tool_target=5,
        contract_fetcher=_fetcher(contracts),
        scanned_at="2026-08-02T02:00:00+00:00",
    )

    assert second["previous_cycle_id"] == first["cycle_id"]
    assert second["delta"]["added_count"] == 0
    assert second["delta"]["changed_count"] == 0
    assert second["delta"]["removed_count"] == 0
    assert first["attempted_record_ids"] != second["attempted_record_ids"]
    assert len(second["state"]["inspected_record_ids"]) == 2


def test_incremental_cycle_reports_add_change_and_remove(tmp_path: Path):
    payload, contracts = _catalog(2, operations=2)
    tooluniverse = _ToolUniverse()
    first = build_continuous_scan_cycle(
        _directory(payload),
        inventory=configured_source_inventory(tooluniverse),
        registry_tools=[],
        snapshot_directory=tmp_path / "contracts",
        max_contracts=1,
        draftable_tool_target=1,
        contract_fetcher=_fetcher(contracts),
        scanned_at="2026-08-02T01:00:00+00:00",
    )

    changed_payload = copy.deepcopy(payload)
    removed_name = sorted(changed_payload)[0]
    changed_payload.pop(removed_name)
    remaining_name = next(iter(changed_payload))
    preferred = changed_payload[remaining_name]["preferred"]
    changed_payload[remaining_name]["versions"][preferred]["info"]["title"] += (
        " Updated"
    )
    added_payload, added_contracts = _catalog(1, operations=2)
    added_name = next(iter(added_payload))
    added_payload[f"new-{added_name}"] = added_payload.pop(added_name)
    new_entry = added_payload[f"new-{added_name}"]
    new_version = new_entry["preferred"]
    old_url = new_entry["versions"][new_version]["swaggerUrl"]
    new_url = old_url.replace(
        "/provider0.example.org:service/", "/new-provider0.example.org:service/"
    )
    new_entry["versions"][new_version]["swaggerUrl"] = new_url
    changed_payload.update(added_payload)
    contracts[new_url] = next(iter(added_contracts.values()))

    second = build_continuous_scan_cycle(
        _directory(changed_payload, when="2026-08-02T02:00:00+00:00"),
        inventory=configured_source_inventory(tooluniverse),
        registry_tools=[],
        snapshot_directory=tmp_path / "contracts",
        previous_cycle=first,
        max_contracts=2,
        draftable_tool_target=2,
        contract_fetcher=_fetcher(contracts),
        scanned_at="2026-08-02T02:00:00+00:00",
    )

    assert second["delta"]["added_count"] == 1
    assert second["delta"]["changed_count"] == 1
    assert second["delta"]["removed_count"] == 1


def test_contract_failure_is_isolated_and_state_is_tamper_evident(tmp_path: Path):
    payload, contracts = _catalog(2, operations=3)
    first_url = sorted(contracts)[0]
    contracts[first_url] = b'{"not": "openapi"}'
    tooluniverse = _ToolUniverse()
    cycle = build_continuous_scan_cycle(
        _directory(payload),
        inventory=configured_source_inventory(tooluniverse),
        registry_tools=[],
        snapshot_directory=tmp_path / "contracts",
        max_contracts=2,
        draftable_tool_target=2,
        contract_fetcher=_fetcher(contracts),
        scanned_at="2026-08-02T01:00:00+00:00",
    )

    assert cycle["metrics"]["inspected_contract_count"] == 1
    assert cycle["metrics"]["failed_contract_count"] == 1
    assert cycle["metrics"]["draftable_tool_count"] == 3
    modified = copy.deepcopy(cycle)
    modified["metrics"]["draftable_tool_count"] = 4
    with pytest.raises(VSDContinuousScannerError):
        validate_continuous_scan_cycle(modified)


def test_non_public_contract_server_is_blocked_before_preview(tmp_path: Path):
    payload, contracts = _catalog(1, operations=2)
    url, raw = next(iter(contracts.items()))
    document = json.loads(raw)
    document["servers"] = [{"url": "https://provider.local/api"}]
    contracts[url] = json.dumps(document, sort_keys=True).encode()
    tooluniverse = _ToolUniverse()
    cycle = build_continuous_scan_cycle(
        _directory(payload),
        inventory=configured_source_inventory(tooluniverse),
        registry_tools=[],
        snapshot_directory=tmp_path / "contracts",
        max_contracts=1,
        draftable_tool_target=1,
        contract_fetcher=_fetcher(contracts),
        scanned_at="2026-08-02T01:00:00+00:00",
    )

    assert cycle["metrics"]["draftable_tool_count"] == 0
    assert cycle["metrics"]["blocked_operation_count"] == 2
    assert cycle["blocker_counts"] == {"server_host_not_publicly_addressable": 2}


def test_cycle_history_and_scheduled_entrypoint_are_reproducible(tmp_path: Path):
    payload, contracts = _catalog(2, operations=5)
    tooluniverse = _ToolUniverse()

    def catalog_fetcher(_url, _params, **_kwargs):
        return payload, _request(len(json.dumps(payload)))

    first = run_scheduled_apis_guru_scan(
        tooluniverse,
        tmp_path / "state",
        max_contracts=1,
        draftable_tool_target=3,
        catalog_fetcher=catalog_fetcher,
        contract_fetcher=_fetcher(contracts),
        scanned_at="2026-08-02T01:00:00+00:00",
    )
    assert Path(first["history_file"]).exists()
    assert Path(first["latest_file"]).exists()
    assert (
        summarize_continuous_scan(first["cycle"])["metrics"]["draftable_tool_count"]
        == 5
    )

    second = run_scheduled_apis_guru_scan(
        tooluniverse,
        tmp_path / "state",
        max_contracts=1,
        draftable_tool_target=3,
        catalog_fetcher=catalog_fetcher,
        contract_fetcher=_fetcher(contracts),
        scanned_at="2026-08-02T02:00:00+00:00",
    )
    assert second["cycle"]["previous_cycle_id"] == first["cycle"]["cycle_id"]
    assert load_latest_continuous_scan(tmp_path / "state") == second["cycle"]
    history, latest = write_continuous_scan_cycle(second["cycle"], tmp_path / "copy")
    assert history.exists() and latest.exists()
