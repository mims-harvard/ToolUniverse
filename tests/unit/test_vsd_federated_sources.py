from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from tooluniverse import vsd_federated_sources as federated
from tooluniverse.vsd_federated_sources import (
    VSDFederatedSourceError,
    build_federated_scan,
    canonical_openapi_bytes,
    load_federated_source_manifest,
    validate_federated_scan,
    validate_federated_source_manifest,
)
from tooluniverse.vsd_source_intelligence import _digest

pytestmark = pytest.mark.unit


def _source(source_id: str, specification_url: str, runtime_base_url: str) -> dict:
    body = {
        "source_id": source_id,
        "name": f"{source_id.title()} biomedical evidence API",
        "organization": "Example Research Repository",
        "documentation_url": f"https://docs.{source_id}.example.org/api",
        "specification_url": specification_url,
        "runtime_base_url": runtime_base_url,
        "contract_format": "openapi",
        "topics": ["biomedical_evidence", "research_data"],
        "access": "public",
        "trust_basis": "official_repository",
        "review_state": "reviewed_contract_endpoint",
        "execution_allowed": False,
    }
    return {**body, "source_sha256": _digest(body)}


def _manifest(sources: list[dict]) -> dict:
    body = {
        "format": "vsd_federated_source_manifest_v1",
        "version": 1,
        "catalog_id": "example_biomedical_sources",
        "catalog_state": "reviewed_for_bounded_contract_discovery",
        "reviewed_at": "2026-08-02T00:00:00+00:00",
        "review_policy": "Source review permits contract retrieval only; every operation remains inert until separate verification, approval, publication, and explicit loading.",
        "execution_allowed": False,
        "automatic_registration": False,
        "sources": sources,
    }
    return {**body, "manifest_sha256": _digest(body)}


def _contract(title: str, paths: dict) -> bytes:
    return json.dumps(
        {
            "openapi": "3.0.3",
            "info": {"title": title, "version": "1.0.0"},
            "paths": paths,
        },
        sort_keys=True,
    ).encode()


def _operation(method: str = "get") -> dict:
    return {
        method: {
            "operationId": f"{method}Evidence",
            "responses": {
                "200": {
                    "description": "Evidence",
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


def _inventory() -> dict:
    body = {
        "format": "vsd_source_inventory_v1",
        "version": 1,
        "tool_count": 2,
        "host_count": 1,
        "hosts": [{"host": "api.shared.example.org", "tools": ["ExistingTool"]}],
    }
    return {**body, "inventory_sha256": _digest(body)}


def test_packaged_manifest_has_twenty_reviewed_service_sources():
    manifest = load_federated_source_manifest()

    assert len(manifest["sources"]) == 20
    assert len({item["specification_url"] for item in manifest["sources"]}) == 20
    assert len({item["source_id"] for item in manifest["sources"]}) == 20
    assert all(item["contract_format"] == "openapi" for item in manifest["sources"])
    assert all(item["execution_allowed"] is False for item in manifest["sources"])


def test_scan_is_generic_deduplicated_and_inert(tmp_path: Path):
    first_url = "https://contracts.one.example.org/openapi.json"
    second_url = "https://contracts.two.example.org/openapi.json"
    manifest = _manifest(
        [
            _source("source_one", first_url, "https://api.shared.example.org/v1"),
            _source("source_two", second_url, "https://api.shared.example.org/v1"),
        ]
    )
    contracts = {
        first_url: _contract(
            "First Evidence API",
            {
                "/existing": _operation(),
                "/gap": _operation(),
                "/write": _operation("post"),
            },
        ),
        second_url: _contract(
            "Second Evidence API",
            {"/gap": _operation(), "/new": _operation()},
        ),
    }

    def fetch(url: str, _timeout: float, maximum: int):
        raw = contracts[url]
        assert len(raw) <= maximum
        return raw, {
            "url": url,
            "redirects": 0,
            "response_bytes": len(raw),
            "content_type": "application/json",
        }

    existing = {
        "name": "ExistingOperation",
        "vsd_operation": {
            "method": "GET",
            "endpoint": "https://api.shared.example.org/v1/existing",
        },
    }
    scan = build_federated_scan(
        manifest,
        inventory=_inventory(),
        registry_tools=[existing],
        snapshot_directory=tmp_path / "contracts",
        contract_fetcher=fetch,
        scanned_at="2026-08-02T01:00:00+00:00",
    )

    assert validate_federated_scan(scan) == scan
    assert scan["metrics"] == {
        "manifest_source_count": 2,
        "successful_source_count": 2,
        "failed_source_count": 0,
        "operation_candidate_count": 5,
        "unique_operation_identity_count": 4,
        "structurally_draftable_count": 4,
        "net_new_preview_count": 2,
        "existing_exact_operation_count": 1,
        "existing_host_gap_count": 2,
        "new_host_candidate_count": 0,
        "duplicate_source_operation_count": 1,
        "blocked_operation_count": 1,
    }
    assert {item["registry_coverage"] for item in scan["operations"]} == {
        "blocked",
        "duplicate_federated_source",
        "existing_exact",
        "existing_host_gap",
    }
    assert all(item["execution_allowed"] is False for item in scan["operations"])
    assert all(
        item["preview"] is None
        or set(item["preview"]) == {"tool_name", "config_sha256"}
        for item in scan["operations"]
    )


def test_manifest_and_scan_reject_tampering(tmp_path: Path):
    manifest = load_federated_source_manifest()
    changed = copy.deepcopy(manifest)
    changed["sources"][0]["runtime_base_url"] = "https://attacker.example.org/api"
    with pytest.raises(VSDFederatedSourceError, match="identity"):
        validate_federated_source_manifest(changed)

    source = _source(
        "source_one",
        "https://contracts.one.example.org/openapi.json",
        "https://api.one.example.org/v1",
    )
    raw = _contract("Evidence", {"/records": _operation()})

    def fetch(url: str, _timeout: float, _maximum: int):
        return raw, {
            "url": url,
            "redirects": 0,
            "response_bytes": len(raw),
            "content_type": "application/json",
        }

    scan = build_federated_scan(
        _manifest([source]),
        inventory={
            **_inventory(),
            "tool_count": 0,
            "host_count": 0,
            "hosts": [],
            "inventory_sha256": _digest(
                {
                    "format": "vsd_source_inventory_v1",
                    "version": 1,
                    "tool_count": 0,
                    "host_count": 0,
                    "hosts": [],
                }
            ),
        },
        registry_tools=[],
        snapshot_directory=tmp_path / "contracts",
        contract_fetcher=fetch,
        scanned_at="2026-08-02T01:00:00+00:00",
    )
    changed_scan = copy.deepcopy(scan)
    changed_scan["metrics"]["net_new_preview_count"] = 100_000
    with pytest.raises(VSDFederatedSourceError, match="identity"):
        validate_federated_scan(changed_scan)

    changed_scan = copy.deepcopy(scan)
    changed_scan["sources"][0]["preview_count"] = 99
    body = {
        key: item
        for key, item in changed_scan.items()
        if key not in {"scan_id", "scan_sha256"}
    }
    changed_scan["scan_sha256"] = _digest(body)
    changed_scan["scan_id"] = changed_scan["scan_sha256"][:16]
    with pytest.raises(VSDFederatedSourceError, match="source metrics"):
        validate_federated_scan(changed_scan)


def test_provider_metadata_is_declarative_not_embedded_in_scanner_code():
    manifest = load_federated_source_manifest()
    source = Path(
        __import__("tooluniverse.vsd_federated_sources", fromlist=["__file__"]).__file__
    ).read_text(encoding="utf-8")

    assert all(item["specification_url"] not in source for item in manifest["sources"])
    assert all(item["runtime_base_url"] not in source for item in manifest["sources"])


def test_preview_generation_failure_remains_blocked_and_internally_consistent(
    monkeypatch, tmp_path: Path
):
    source = _source(
        "source_one",
        "https://contracts.one.example.org/openapi.json",
        "https://api.one.example.org/v1",
    )
    raw = _contract("Evidence", {"/records": _operation()})

    def fetch(url: str, _timeout: float, _maximum: int):
        return raw, {
            "url": url,
            "redirects": 0,
            "response_bytes": len(raw),
            "content_type": "application/json",
        }

    def fail_preview(*_args):
        raise ValueError("generation failed")

    monkeypatch.setattr(federated, "_preview_config", fail_preview)
    scan = build_federated_scan(
        _manifest([source]),
        inventory={
            **_inventory(),
            "tool_count": 0,
            "host_count": 0,
            "hosts": [],
            "inventory_sha256": _digest(
                {
                    "format": "vsd_source_inventory_v1",
                    "version": 1,
                    "tool_count": 0,
                    "host_count": 0,
                    "hosts": [],
                }
            ),
        },
        registry_tools=[],
        snapshot_directory=tmp_path / "contracts",
        contract_fetcher=fetch,
        scanned_at="2026-08-02T01:00:00+00:00",
    )

    assert validate_federated_scan(scan) == scan
    assert scan["metrics"]["structurally_draftable_count"] == 0
    assert scan["metrics"]["blocked_operation_count"] == 1
    assert scan["blocker_counts"] == {"preview_generation_failed": 1}


def test_semantically_identical_contract_representations_share_identity(tmp_path: Path):
    document = json.loads(_contract("Stable Evidence", {"/records": _operation()}))
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
    second.write_text(json.dumps(document, indent=4), encoding="utf-8")

    first_bytes, first_digest = canonical_openapi_bytes(first)
    second_bytes, second_digest = canonical_openapi_bytes(second)

    assert first.read_bytes() != second.read_bytes()
    assert first_bytes == second_bytes
    assert first_digest == second_digest
