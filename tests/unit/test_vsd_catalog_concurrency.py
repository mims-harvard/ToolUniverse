from __future__ import annotations

import json
import multiprocessing
import os
import time
from pathlib import Path

import pytest

import tooluniverse.vsd_tool as vsd_tool

pytestmark = pytest.mark.unit


def _registration_worker(
    catalog_dir: str,
    source_id: str,
    start_event,
    results,
) -> None:
    """Register from an isolated process while widening the old lost-update race."""
    os.environ["TOOLUNIVERSE_VSD_DIR"] = catalog_dir
    vsd_tool._resolve_public_addresses = lambda host, port: ("93.184.216.34",)
    vsd_tool._safe_get_json = lambda endpoint, params: (
        {"ok": True},
        {
            "url": endpoint,
            "status_code": 200,
            "content_type": "application/json",
            "response_bytes": 12,
            "peer_ip": "93.184.216.34",
            "redirects": 0,
        },
    )

    original_load = vsd_tool._load_catalog

    def slow_load():
        catalog = original_load()
        time.sleep(0.25)
        return catalog

    vsd_tool._load_catalog = slow_load
    try:
        if not start_event.wait(timeout=10):
            raise RuntimeError("registration start event timed out")
        result = vsd_tool.VSDRegisterSource({}).run(
            {
                "source_id": source_id,
                "endpoint": "https://api.fda.gov/drug/label.json",
                "name": source_id,
            }
        )
        results.put((source_id, result["data"]["registered"], None))
    except Exception as exc:  # pragma: no cover - asserted in the parent process
        results.put((source_id, False, repr(exc)))
        raise


def _fake_probe(endpoint: str, params):
    del params
    return (
        {"ok": True},
        {
            "url": endpoint,
            "status_code": 200,
            "content_type": "application/json",
            "response_bytes": 12,
            "peer_ip": "93.184.216.34",
            "redirects": 0,
        },
    )


def test_concurrent_process_registrations_do_not_lose_updates(tmp_path):
    """Keep both updates when independent processes register concurrently."""
    context = multiprocessing.get_context("spawn")
    start_event = context.Event()
    results = context.Queue()
    processes = [
        context.Process(
            target=_registration_worker,
            args=(str(tmp_path), source_id, start_event, results),
        )
        for source_id in ("source_alpha", "source_beta")
    ]

    for process in processes:
        process.start()
    start_event.set()
    for process in processes:
        process.join(timeout=20)

    outcomes = [results.get(timeout=2) for _ in processes]
    assert outcomes == [
        ("source_alpha", True, None),
        ("source_beta", True, None),
    ] or outcomes == [
        ("source_beta", True, None),
        ("source_alpha", True, None),
    ]
    assert [process.exitcode for process in processes] == [0, 0]

    catalog = json.loads((tmp_path / "sources.json").read_text(encoding="utf-8"))
    assert set(catalog["sources"]) == {"source_alpha", "source_beta"}


def test_duplicate_registration_requires_explicit_replace(monkeypatch, tmp_path):
    """Preserve an existing source unless replacement is explicitly enabled."""
    monkeypatch.setenv("TOOLUNIVERSE_VSD_DIR", str(tmp_path))
    monkeypatch.setattr(vsd_tool, "_safe_get_json", _fake_probe)
    monkeypatch.setattr(
        vsd_tool,
        "_resolve_public_addresses",
        lambda host, port: ("93.184.216.34",),
    )
    tool = vsd_tool.VSDRegisterSource({})
    original = {
        "source_id": "openfda_case",
        "endpoint": "https://api.fda.gov/drug/label.json",
        "name": "Original",
    }

    first = tool.run(original)
    assert first["data"]["registered"] is True
    assert first["data"]["replaced"] is False
    assert "catalog_path" not in first["data"]

    with pytest.raises(ValueError, match="already registered"):
        tool.run({**original, "name": "Implicit overwrite"})

    replacement = tool.run({**original, "name": "Replacement", "replace": True})
    assert replacement["data"]["registered"] is True
    assert replacement["data"]["replaced"] is True
    assert replacement["data"]["source"]["name"] == "Replacement"


@pytest.mark.parametrize("replace", [0, 1, "true", None])
def test_registration_replace_must_be_boolean(monkeypatch, tmp_path, replace):
    """Require an actual boolean for the replacement control."""
    monkeypatch.setenv("TOOLUNIVERSE_VSD_DIR", str(tmp_path))
    monkeypatch.setattr(vsd_tool, "_safe_get_json", _fake_probe)
    monkeypatch.setattr(
        vsd_tool,
        "_resolve_public_addresses",
        lambda host, port: ("93.184.216.34",),
    )

    with pytest.raises(ValueError, match="replace must be a boolean"):
        vsd_tool.VSDRegisterSource({}).run(
            {
                "source_id": "openfda_case",
                "endpoint": "https://api.fda.gov/drug/label.json",
                "replace": replace,
            }
        )


def test_catalog_file_contains_no_host_path(monkeypatch, tmp_path):
    """Do not return or persist the host's catalog path in source records."""
    monkeypatch.setenv("TOOLUNIVERSE_VSD_DIR", str(tmp_path))
    monkeypatch.setattr(vsd_tool, "_safe_get_json", _fake_probe)
    monkeypatch.setattr(
        vsd_tool,
        "_resolve_public_addresses",
        lambda host, port: ("93.184.216.34",),
    )

    result = vsd_tool.VSDRegisterSource({}).run(
        {
            "source_id": "openfda_case",
            "endpoint": "https://api.fda.gov/drug/label.json",
        }
    )

    serialized = json.dumps(result, sort_keys=True)
    assert str(Path.home()) not in serialized
    assert str(tmp_path) not in serialized


def test_malformed_source_record_is_rejected_without_leaking_path(
    monkeypatch, tmp_path
):
    """Reject malformed catalog records without exposing filesystem paths."""
    monkeypatch.setenv("TOOLUNIVERSE_VSD_DIR", str(tmp_path))
    (tmp_path / "sources.json").write_text(
        json.dumps(
            {
                "version": 1,
                "sources": {
                    "bad_source": {
                        "source_id": "different_id",
                        "endpoint": "https://api.fda.gov/drug/label.json",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unsupported source record") as exc_info:
        vsd_tool.VSDListSources({}).run({})

    assert str(tmp_path) not in str(exc_info.value)
