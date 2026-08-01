"""End-to-end proof for reviewed dynamic REST execution through ToolUniverse."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from tooluniverse import ToolUniverse
from tooluniverse.vsd_dynamic_rest import (
    operation_digest,
    register_reviewed_rest_tool,
)

ACTIVE_STATUSES = (
    "RECRUITING|NOT_YET_RECRUITING|ACTIVE_NOT_RECRUITING|ENROLLING_BY_INVITATION"
)

SEARCH_TOOL = {
    "name": "VSDReviewedClinicalTrialsSearch",
    "type": "VSDDynamicRESTTool",
    "description": (
        "Search a reviewed ClinicalTrials.gov operation for active or upcoming "
        "studies by condition and location expression."
    ),
    "category": "special_tools",
    "cacheable": False,
    "mcp_annotations": {"readOnlyHint": True, "destructiveHint": False},
    "parameter": {
        "type": "object",
        "properties": {
            "condition": {"type": "string", "minLength": 2, "maxLength": 200},
            "location_query": {
                "type": "string",
                "minLength": 2,
                "maxLength": 500,
            },
            "page_size": {"type": "integer", "minimum": 1, "maximum": 20},
        },
        "required": ["condition", "location_query", "page_size"],
        "additionalProperties": False,
    },
    "vsd_operation": {
        "version": 1,
        "method": "GET",
        "endpoint": "https://clinicaltrials.gov/api/v2/studies",
        "path_arguments": {},
        "query_arguments": {
            "condition": "query.cond",
            "location_query": "query.locn",
            "page_size": "pageSize",
        },
        "fixed_query": {
            "format": "json",
            "countTotal": "true",
            "filter.overallStatus": ACTIVE_STATUSES,
        },
        "timeout_seconds": 30,
        "auth": {"type": "none"},
        "response_schema": {
            "type": "object",
            "properties": {
                "studies": {"type": "array", "maxItems": 20},
                "totalCount": {"type": "integer", "minimum": 0},
                "nextPageToken": {"type": "string"},
            },
            "required": ["studies"],
            "additionalProperties": True,
        },
    },
}

DETAIL_TOOL = {
    "name": "VSDReviewedClinicalTrialDetails",
    "type": "VSDDynamicRESTTool",
    "description": (
        "Retrieve one reviewed ClinicalTrials.gov study record by its validated "
        "NCT identifier."
    ),
    "category": "special_tools",
    "cacheable": False,
    "mcp_annotations": {"readOnlyHint": True, "destructiveHint": False},
    "parameter": {
        "type": "object",
        "properties": {"nct_id": {"type": "string", "pattern": "^NCT[0-9]{8}$"}},
        "required": ["nct_id"],
        "additionalProperties": False,
    },
    "vsd_operation": {
        "version": 1,
        "method": "GET",
        "endpoint": "https://clinicaltrials.gov/api/v2/studies/{nctId}",
        "path_arguments": {"nct_id": "nctId"},
        "query_arguments": {},
        "fixed_query": {"format": "json"},
        "timeout_seconds": 30,
        "auth": {"type": "none"},
        "response_schema": {
            "type": "object",
            "properties": {"protocolSection": {"type": "object"}},
            "required": ["protocolSection"],
            "additionalProperties": True,
        },
    },
}


def _module(study: dict[str, Any], name: str) -> dict[str, Any]:
    protocol = study.get("protocolSection") or {}
    value = protocol.get(name) or {}
    return value if isinstance(value, dict) else {}


def _clean_provider_text(value: Any) -> Any:
    """Repair common UTF-8-as-Latin-1 text and normalize whitespace."""
    if isinstance(value, dict):
        return {key: _clean_provider_text(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean_provider_text(item) for item in value]
    if not isinstance(value, str):
        return value
    repaired = value
    if any(marker in value for marker in ("\u00c2", "\u00c3", "\u00ce", "\u00e2")):
        try:
            repaired = value.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            repaired = value
    return re.sub(r"\s+", " ", repaired).strip()


def _study_summary(study: dict[str, Any]) -> dict[str, Any]:
    identification = _module(study, "identificationModule")
    status = _module(study, "statusModule")
    design = _module(study, "designModule")
    contacts = _module(study, "contactsLocationsModule")
    conditions = _module(study, "conditionsModule")
    arms = _module(study, "armsInterventionsModule")
    sponsor = _module(study, "sponsorCollaboratorsModule")
    locations = contacts.get("locations") or []
    interventions = arms.get("interventions") or []
    return _clean_provider_text(
        {
            "nct_id": identification.get("nctId"),
            "title": identification.get("briefTitle"),
            "overall_status": status.get("overallStatus"),
            "phases": design.get("phases") or [],
            "study_type": design.get("studyType"),
            "conditions": conditions.get("conditions") or [],
            "lead_sponsor": (sponsor.get("leadSponsor") or {}).get("name"),
            "interventions": [
                {"name": item.get("name"), "type": item.get("type")}
                for item in interventions
                if isinstance(item, dict)
            ],
            "us_locations": [
                {
                    "facility": item.get("facility"),
                    "city": item.get("city"),
                    "state": item.get("state"),
                    "status": item.get("status"),
                }
                for item in locations
                if isinstance(item, dict) and item.get("country") == "United States"
            ],
        }
    )


def _must_succeed(result: Any, tool_name: str) -> dict[str, Any]:
    if not isinstance(result, dict) or result.get("status") != "success":
        raise RuntimeError(
            f"{tool_name} did not return a successful result: {result!r}"
        )
    data = result.get("data")
    if not isinstance(data, dict) or "result" not in data or "provenance" not in data:
        raise RuntimeError(f"{tool_name} returned an incomplete evidence envelope")
    return data


def run_case() -> dict[str, Any]:
    """Run two reviewed operations from one API through one ToolUniverse instance."""
    tooluniverse = ToolUniverse()
    try:
        for config in (SEARCH_TOOL, DETAIL_TOOL):
            register_reviewed_rest_tool(tooluniverse, config)

        search_data = _must_succeed(
            tooluniverse.run_one_function(
                {
                    "name": SEARCH_TOOL["name"],
                    "arguments": {
                        "condition": "Amyotrophic Lateral Sclerosis",
                        "location_query": "AREA[LocationCountry]United States",
                        "page_size": 20,
                    },
                },
                use_cache=False,
            ),
            SEARCH_TOOL["name"],
        )
        studies = search_data["result"].get("studies") or []
        summaries = [_study_summary(study) for study in studies]
        summaries = [summary for summary in summaries if summary.get("nct_id")]
        if not summaries:
            raise RuntimeError("The reviewed ALS search returned no usable NCT records")
        selected_nct_id = sorted(summary["nct_id"] for summary in summaries)[0]

        detail_data = _must_succeed(
            tooluniverse.run_one_function(
                {
                    "name": DETAIL_TOOL["name"],
                    "arguments": {"nct_id": selected_nct_id},
                },
                use_cache=False,
            ),
            DETAIL_TOOL["name"],
        )
        detailed_summary = _study_summary(detail_data["result"])
        if detailed_summary.get("nct_id") != selected_nct_id:
            raise RuntimeError("The detail operation returned a different NCT record")

        statuses = Counter(
            item.get("overall_status") or "UNKNOWN" for item in summaries
        )
        phases = Counter(
            phase
            for item in summaries
            for phase in (item.get("phases") or ["NOT_APPLICABLE"])
        )
        intervention_types = Counter(
            intervention.get("type") or "UNKNOWN"
            for item in summaries
            for intervention in item.get("interventions") or []
        )
        states = Counter(
            location.get("state") or "UNSPECIFIED"
            for item in summaries
            for location in item.get("us_locations") or []
        )
        return {
            "case": {
                "question": (
                    "Which active or upcoming US ALS studies are returned by the "
                    "reviewed ClinicalTrials.gov search, and can a second generated "
                    "operation retrieve the selected study consistently?"
                ),
                "condition": "Amyotrophic Lateral Sclerosis",
                "location_query": "AREA[LocationCountry]United States",
                "status_filter": ACTIVE_STATUSES.split("|"),
                "interpretation_boundary": (
                    "This is an API execution and record-consistency proof, not trial "
                    "matching, eligibility assessment, or treatment advice."
                ),
            },
            "tool_contracts": [
                {
                    "name": config["name"],
                    "endpoint": config["vsd_operation"]["endpoint"],
                    "operation_sha256": operation_digest(config),
                }
                for config in (SEARCH_TOOL, DETAIL_TOOL)
            ],
            "search": {
                "returned_records": len(summaries),
                "provider_total_count": search_data["result"].get("totalCount"),
                "has_next_page": bool(search_data["result"].get("nextPageToken")),
                "status_counts": dict(sorted(statuses.items())),
                "phase_counts": dict(sorted(phases.items())),
                "intervention_type_counts": dict(sorted(intervention_types.items())),
                "top_location_states": states.most_common(10),
                "studies": summaries,
                "provenance": search_data["provenance"],
            },
            "detail_follow_up": {
                "selection_rule": "Lexicographically smallest returned valid NCT identifier",
                "selected_nct_id": selected_nct_id,
                "identifier_matches_search": any(
                    item["nct_id"] == detailed_summary["nct_id"] for item in summaries
                ),
                "study": detailed_summary,
                "provenance": detail_data["provenance"],
            },
        }
    finally:
        tooluniverse.close()


def render_markdown(evidence: dict[str, Any]) -> str:
    """Render a compact analyst-facing report from the evidence ledger."""
    case = evidence["case"]
    search = evidence["search"]
    follow_up = evidence["detail_follow_up"]
    lines = [
        "# Reviewed Dynamic REST ALS Validation",
        "",
        "## Decision Question",
        "",
        case["question"],
        "",
        "## Result",
        "",
        f"- Returned records: **{search['returned_records']}**",
        f"- Provider total matching records: **{search['provider_total_count']}**",
        f"- Additional page available: **{'yes' if search['has_next_page'] else 'no'}**",
        f"- Deterministic follow-up record: **{follow_up['selected_nct_id']}**",
        f"- Detail identifier matched search: **{str(follow_up['identifier_matches_search']).lower()}**",
        "",
        "## Cohort Summary",
        "",
        f"- Statuses: `{json.dumps(search['status_counts'], sort_keys=True)}`",
        f"- Phases: `{json.dumps(search['phase_counts'], sort_keys=True)}`",
        f"- Intervention types: `{json.dumps(search['intervention_type_counts'], sort_keys=True)}`",
        f"- Most represented US states: `{json.dumps(search['top_location_states'])}`",
        "",
        "## Returned Studies",
        "",
        "| NCT ID | Status | Phase | Title | US locations |",
        "| --- | --- | --- | --- | ---: |",
    ]
    for study in search["studies"]:
        title = str(study.get("title") or "").replace("|", "\\|")
        phases = ", ".join(study.get("phases") or ["N/A"])
        lines.append(
            f"| {study['nct_id']} | {study.get('overall_status') or 'N/A'} | "
            f"{phases} | {title} | {len(study.get('us_locations') or [])} |"
        )
    lines.extend(
        [
            "",
            "## Execution Evidence",
            "",
        ]
    )
    for contract in evidence["tool_contracts"]:
        lines.append(f"- `{contract['name']}`: `{contract['operation_sha256']}`")
    lines.extend(
        [
            f"- Search payload: `{search['provenance']['payload_sha256']}`",
            f"- Detail payload: `{follow_up['provenance']['payload_sha256']}`",
            "- Both calls used HTTPS GET, zero redirects, bounded JSON decoding, "
            "pinned DNS, schema validation, and the ToolUniverse `run_one_function()` path.",
            "",
            "## Interpretation Boundary",
            "",
            case["interpretation_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def write_artifacts(evidence: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    """Write machine-readable and human-readable evidence artifacts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "dynamic_rest_als_snapshot.json"
    markdown_path = output_dir / "dynamic_rest_als_snapshot.md"
    json_path.write_text(
        json.dumps(evidence, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_markdown(evidence), encoding="utf-8")
    return json_path, markdown_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).with_name("artifacts"),
    )
    arguments = parser.parse_args(argv)
    evidence = run_case()
    json_path, markdown_path = write_artifacts(evidence, arguments.output_dir)
    print(f"Wrote {json_path}")
    print(f"Wrote {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
