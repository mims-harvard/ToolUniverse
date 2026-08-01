from __future__ import annotations

import hashlib
import json

import pytest

from examples.docker_llm import run_smoke_case as study

pytestmark = pytest.mark.unit


def test_case_orchestrates_full_lifecycle_and_writes_reports(monkeypatch, tmp_path):
    prompt_hash = hashlib.sha256(study.PROMPT.encode()).hexdigest()
    security = {
        "running": True,
        "read_only_rootfs": True,
        "cap_drop": ["ALL"],
        "no_new_privileges": True,
        "privileged": False,
        "bind_mounts": 0,
        "host_binding": "127.0.0.1:19090",
        "pids_limit": 64,
        "memory_mb": 256,
        "cpus": 1.0,
    }
    provisioned = {
        "version": 1,
        "record_path": str(tmp_path / "workspace" / "approved" / "tool.json"),
        "record_sha256": "a" * 64,
        "profile_sha256": "b" * 64,
        "image_id": "sha256:" + "c" * 64,
        "docker_server_version": "27.5.1",
        "security": security,
    }
    statuses = iter(
        [
            {"exists": True, "security": {**security, "running": True}},
            {"exists": True, "security": {**security, "running": False}},
            {"exists": False},
        ]
    )
    monkeypatch.setattr(study, "_run", lambda command: "built")
    monkeypatch.setattr(
        study,
        "plan_container",
        lambda *args, **kwargs: {
            "docker_argv": ["docker", "run"],
            "profile_sha256": "b" * 64,
        },
    )
    monkeypatch.setattr(
        study, "provision_container", lambda *args, **kwargs: provisioned
    )
    monkeypatch.setattr(
        study, "status_container", lambda *args, **kwargs: next(statuses)
    )
    monkeypatch.setattr(
        study,
        "stop_container",
        lambda *args, **kwargs: {"stopped": True, "was_running": True},
    )
    monkeypatch.setattr(
        study,
        "remove_container",
        lambda *args, **kwargs: {
            "removed": True,
            "client_record_removed": True,
        },
    )
    monkeypatch.setattr(
        study,
        "load_provisioned_tool",
        lambda *args, **kwargs: "DockerEvidenceSynthesizer",
    )

    class FakeToolUniverse:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def run_one_function(self, call, use_cache=False):
            assert call["arguments"]["prompt"] == study.PROMPT
            assert use_cache is False
            return {
                "status": "success",
                "data": {
                    "response": f"prompt_sha256={prompt_hash}; evidence_sections=6",
                    "model": "fixture-evidence-synthesizer",
                    "usage": {"prompt_tokens": 200},
                    "provenance": {"payload_sha256": "d" * 64},
                },
            }

        def close(self):
            return None

    monkeypatch.setattr(study, "ToolUniverse", FakeToolUniverse)
    output_json = tmp_path / "snapshot.json"
    output_markdown = tmp_path / "snapshot.md"
    output_record = tmp_path / "record.json"
    result = study.run_case(
        host_port=19090,
        workspace=tmp_path / "workspace",
        output_json=output_json,
        output_markdown=output_markdown,
        output_record=output_record,
    )

    assert result["tooluniverse_inference"]["prompt_hash_verified"] is True
    assert result["lifecycle"]["absent_after_remove"] is True
    assert json.loads(output_json.read_text())["case"] == (
        "reviewed_docker_llm_lifecycle_and_complex_prompt"
    )
    assert json.loads(output_record.read_text())["image_id"].startswith("sha256:")
    report = output_markdown.read_text()
    assert "Inspected Container Policy" in report
    assert "deterministic infrastructure" in report
