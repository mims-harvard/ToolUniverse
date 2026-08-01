"""Offline case study proving VSD checks existing coverage before discovery."""

from __future__ import annotations

import json
from pathlib import Path

from tooluniverse import ToolUniverse
from tooluniverse.vsd_coverage import resolve_capability


DEMANDS = {
    "als_registry": {
        "description": "rare disease registry genes and phenotypes",
        "required_inputs": ["disease"],
    },
    "fda_label": {
        "description": "retrieve FDA drug label by set identifier",
        "provider": "FDA",
        "required_inputs": ["set_id"],
    },
    "drug_discovery_workflow": {
        "description": "complete disease target compound ADMET literature workflow",
    },
    "intentional_gap": {
        "description": "quantum microscope calibration waveform optimizer",
    },
}


def run_case() -> dict:
    tooluniverse = ToolUniverse()
    try:
        results = {
            name: resolve_capability(tooluniverse, request, limit=10)["data"]
            for name, request in DEMANDS.items()
        }
    finally:
        tooluniverse.close()
    assertions = {
        "als_uses_existing_registry": any(
            match["name"] in {"Orphanet_get_genes", "Orphanet_get_phenotypes"}
            for match in results["als_registry"]["matches"]
        ),
        "fda_uses_existing_tool_family": any(
            "FDA" in match["name"] for match in results["fda_label"]["matches"]
        ),
        "workflow_is_detected": results["drug_discovery_workflow"]["workflow_matches"]
        > 0,
        "real_gap_can_continue_to_discovery": results["intentional_gap"][
            "classification"
        ]
        == "missing",
    }
    return {
        "case": "registry-first capability resolution",
        "demands": DEMANDS,
        "results": results,
        "assertions": assertions,
        "all_assertions_passed": all(assertions.values()),
    }


def main() -> int:
    report = run_case()
    artifact = Path(__file__).parent / "artifacts" / "capability_coverage_snapshot.json"
    artifact.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True))
    return 0 if report["all_assertions_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
