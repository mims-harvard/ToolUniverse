"""Run a real Docker lifecycle and ToolUniverse inference-contract smoke case."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tooluniverse import ToolUniverse
from tooluniverse.remote.docker_llm.provision import (
    load_provisioned_tool,
    plan_container,
    provision_container,
    remove_container,
    status_container,
    stop_container,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "docker_llm_smoke"
PROFILE = FIXTURE / "profile.json"
IMAGE = "tooluniverse/docker-llm-smoke:test"
ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
DEFAULT_JSON = ARTIFACTS / "docker_smoke_snapshot.json"
DEFAULT_MARKDOWN = ARTIFACTS / "docker_smoke_snapshot.md"
DEFAULT_RECORD = ARTIFACTS / "docker_provision_record.json"
PROMPT = """## Question
Assess whether the following mixed pharmacovigilance evidence warrants escalation for a possible drug-induced liver injury signal. Separate observed facts, conflicts, missing denominators, and next analyses.

## Spontaneous reports
Twenty-eight reports mention hepatocellular injury after exposure; nine include a positive dechallenge, two include a positive rechallenge, and seven have substantial concomitant-drug confounding. Reporting volume rose after a label change.

## Trial evidence
Across three randomized trials, ALT greater than three times the upper limit of normal occurred in 17 of 1,204 exposed participants and 6 of 1,198 controls. Trial follow-up ranged from 12 to 36 weeks, and severe baseline liver disease was excluded.

## Observational evidence
A claims analysis reports an adjusted hazard ratio of 1.42 with a 95% confidence interval of 0.96 to 2.10. Exposure was inferred from dispensing, outcome validation was available for 63 percent of cases, and residual alcohol-use confounding is plausible.

## Mechanistic evidence
An in-vitro assay found concentration-dependent mitochondrial stress above clinically observed free-drug concentrations. No validated human susceptibility biomarker is available.

## Required output
Return a concise evidence table, identify contradictions and bias risks, state whether the signal is detected versus confirmed, and list three falsifiable follow-up analyses. Do not give patient-specific advice."""


def _run(command: list[str]) -> str:
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout)[-2000:])
    return result.stdout.strip()


def _markdown(snapshot: dict[str, Any]) -> str:
    security = snapshot["provisioning"]["security"]
    inference = snapshot["tooluniverse_inference"]
    return "\n".join(
        [
            "# Docker LLM Administrator Smoke Validation",
            "",
            "## Result",
            "",
            "A locally built service image was allowlisted, started through the administrator-only provisioner, inspected for the reviewed security settings, called through a freshly registered ToolUniverse tool, stopped, and removed.",
            "",
            f"- Docker server: `{snapshot['docker_server_version']}`",
            f"- Image ID: `{snapshot['provisioning']['image_id']}`",
            f"- Profile SHA-256: `{snapshot['provisioning']['profile_sha256']}`",
            f"- Tool: `{inference['tool_name']}`",
            f"- Prompt SHA-256 verified by service: **{str(inference['prompt_hash_verified']).lower()}**",
            f"- Response payload SHA-256: `{inference['payload_sha256']}`",
            "",
            "## Inspected Container Policy",
            "",
            "| Property | Observed |",
            "| --- | --- |",
            f"| Host binding | `{security['host_binding']}` |",
            f"| Read-only root filesystem | `{security['read_only_rootfs']}` |",
            f"| Linux capabilities dropped | `{', '.join(security['cap_drop'])}` |",
            f"| No new privileges | `{security['no_new_privileges']}` |",
            f"| Privileged | `{security['privileged']}` |",
            f"| Bind mounts | `{security['bind_mounts']}` |",
            f"| CPU limit | `{security['cpus']}` |",
            f"| Memory limit | `{security['memory_mb']} MB` |",
            f"| PID limit | `{security['pids_limit']}` |",
            "",
            "## Complicated Payload",
            "",
            f"The request contained `{inference['prompt_words']}` words across `{inference['evidence_sections']}` labeled sections covering spontaneous reports, trials, observational evidence, mechanistic evidence, and explicit output constraints. The service returned the exact prompt hash through the OpenAI-compatible endpoint, proving that the complete payload crossed Docker and ToolUniverse without truncation or substitution.",
            "",
            "## Boundary",
            "",
            "The fixture validates Docker lifecycle, isolation flags, health identity, client publication, request transport, response limits, and cleanup. It is deterministic infrastructure, not a real language model, so it does not validate synthesis quality or scientific conclusions.",
            "",
        ]
    )


def run_case(
    *,
    host_port: int,
    workspace: Path,
    output_json: Path,
    output_markdown: Path,
    output_record: Path,
) -> dict[str, Any]:
    _run(["docker", "build", "--pull", "--tag", IMAGE, str(FIXTURE)])
    previous_allowlist = os.environ.get("TOOLUNIVERSE_DOCKER_ALLOWED_IMAGES")
    os.environ["TOOLUNIVERSE_DOCKER_ALLOWED_IMAGES"] = IMAGE
    container_name = "tooluniverse-docker-llm-smoke-case"
    provisioned = None
    removed = None
    try:
        plan = plan_container(
            PROFILE, host_port=host_port, container_name=container_name
        )
        provisioned = provision_container(
            PROFILE,
            host_port=host_port,
            container_name=container_name,
            workspace=workspace,
        )
        running = status_container(
            PROFILE, host_port=host_port, container_name=container_name
        )
        record = {
            key: value for key, value in provisioned.items() if key != "record_path"
        }
        output_record.parent.mkdir(parents=True, exist_ok=True)
        output_record.write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

        runtime = ARTIFACTS / ".runtime"
        tooluniverse = ToolUniverse(
            tool_files={}, keep_default_tools=False, workspace=str(runtime)
        )
        try:
            name = load_provisioned_tool(
                tooluniverse, "DockerEvidenceSynthesizer", workspace=workspace
            )
            result = tooluniverse.run_one_function(
                {
                    "name": name,
                    "arguments": {
                        "prompt": PROMPT,
                        "temperature": 0.0,
                        "max_tokens": 700,
                    },
                },
                use_cache=False,
            )
        finally:
            tooluniverse.close()
        if not isinstance(result, dict) or result.get("status") != "success":
            raise RuntimeError(f"ToolUniverse inference failed: {result!r}")
        data = result["data"]
        prompt_hash = hashlib.sha256(PROMPT.encode("utf-8")).hexdigest()
        prompt_hash_verified = f"prompt_sha256={prompt_hash}" in data["response"]
        if not prompt_hash_verified:
            raise RuntimeError(
                "Container response did not confirm the exact prompt hash"
            )
        stopped = stop_container(
            PROFILE, host_port=host_port, container_name=container_name
        )
        stopped_status = status_container(
            PROFILE, host_port=host_port, container_name=container_name
        )
        if stopped_status["security"]["running"]:
            raise RuntimeError("Container remained running after stop")
        removed = remove_container(
            PROFILE,
            host_port=host_port,
            container_name=container_name,
            workspace=workspace,
            confirm=True,
        )
        final_status = status_container(
            PROFILE, host_port=host_port, container_name=container_name
        )
        if final_status["exists"]:
            raise RuntimeError("Container remained present after removal")
        snapshot = {
            "case": "reviewed_docker_llm_lifecycle_and_complex_prompt",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "docker_server_version": provisioned["docker_server_version"],
            "plan": plan,
            "provisioning": record,
            "tooluniverse_inference": {
                "tool_name": "DockerEvidenceSynthesizer",
                "prompt_sha256": prompt_hash,
                "prompt_hash_verified": prompt_hash_verified,
                "prompt_words": len(PROMPT.split()),
                "evidence_sections": PROMPT.count("## "),
                "response": data["response"],
                "model": data["model"],
                "usage": data["usage"],
                "payload_sha256": data["provenance"]["payload_sha256"],
            },
            "lifecycle": {
                "running_status_verified": running["security"]["running"],
                "stop": stopped,
                "stopped_status_verified": not stopped_status["security"]["running"],
                "remove": removed,
                "absent_after_remove": not final_status["exists"],
            },
            "interpretation_boundary": (
                "Infrastructure validation only; the deterministic fixture is not a "
                "real model and does not validate scientific synthesis quality."
            ),
        }
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        output_markdown.write_text(_markdown(snapshot), encoding="utf-8")
        return snapshot
    finally:
        if provisioned is not None and removed is None:
            try:
                remove_container(
                    PROFILE,
                    host_port=host_port,
                    container_name=container_name,
                    workspace=workspace,
                    confirm=True,
                )
            except Exception:
                pass
        if previous_allowlist is None:
            os.environ.pop("TOOLUNIVERSE_DOCKER_ALLOWED_IMAGES", None)
        else:
            os.environ["TOOLUNIVERSE_DOCKER_ALLOWED_IMAGES"] = previous_allowlist


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host-port", type=int, default=19090)
    parser.add_argument("--workspace", type=Path, default=ARTIFACTS / "workspace")
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--output-record", type=Path, default=DEFAULT_RECORD)
    args = parser.parse_args()
    snapshot = run_case(
        host_port=args.host_port,
        workspace=args.workspace,
        output_json=args.output_json,
        output_markdown=args.output_markdown,
        output_record=args.output_record,
    )
    print(
        json.dumps(
            {
                "image_id": snapshot["provisioning"]["image_id"],
                "prompt_hash_verified": snapshot["tooluniverse_inference"][
                    "prompt_hash_verified"
                ],
                "security": snapshot["provisioning"]["security"],
                "lifecycle": snapshot["lifecycle"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
