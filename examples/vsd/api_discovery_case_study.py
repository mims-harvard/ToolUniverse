"""Demand-driven API discovery case using a real ToolUniverse tool call."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from tooluniverse import ToolUniverse

QUERY = "active cancer clinical trials primary site phase protocol"
DESIRED_CAPABILITIES = {
    "stable trial identifier": ("protocol",),
    "cancer site": ("primary", "site"),
    "study phase": ("phase",),
    "study title": ("title",),
    "opening date": ("date", "opened"),
    "principal investigator": ("principal", "investigator"),
}


def _tokens(value: Any) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", str(value or "").casefold()))


def _capability_matches(candidate: dict[str, Any]) -> dict[str, str | None]:
    fields = candidate.get("fields") or []
    matches: dict[str, str | None] = {}
    for capability, required_tokens in DESIRED_CAPABILITIES.items():
        match = None
        for field in fields:
            searchable = _tokens(f"{field.get('field')} {field.get('label')}")
            if set(required_tokens).issubset(searchable):
                match = str(field.get("field"))
                break
        matches[capability] = match
    return matches


def analyze_discovery(data: dict[str, Any]) -> dict[str, Any]:
    """Apply an explicit review-readiness screen to discovery candidates."""
    candidates = data.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("Discovery result did not contain a candidate list")
    reviewed = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise ValueError("Discovery result contained a non-object candidate")
        matches = _capability_matches(candidate)
        matched_count = sum(value is not None for value in matches.values())
        score = candidate.get("score") or {}
        ready = (
            candidate.get("execution_allowed") is False
            and candidate.get("approval_state") == "unreviewed_candidate"
            and score.get("api_ready") == 1.0
            and score.get("official_catalog_label") == 1.0
            and score.get("government_domain") == 1.0
            and matched_count >= 5
        )
        reviewed.append(
            {
                **candidate,
                "capability_matches": matches,
                "matched_capability_count": matched_count,
                "desired_capability_count": len(DESIRED_CAPABILITIES),
                "recommended_for_contract_review": ready,
            }
        )
    recommended = [
        candidate
        for candidate in reviewed
        if candidate["recommended_for_contract_review"]
    ]
    selected = (
        sorted(
            recommended,
            key=lambda item: (
                -item["matched_capability_count"],
                -item["score"]["total"],
                item["candidate_id"],
            ),
        )[0]
        if recommended
        else None
    )
    return {
        "query": data.get("query"),
        "catalog_result_count": data.get("catalog_result_count"),
        "normalized_candidate_count": len(reviewed),
        "recommended_candidate_count": len(recommended),
        "candidates": reviewed,
        "selected_candidate": selected,
        "selection_rule": (
            "Official catalog label, government API domain, API-ready schema, and "
            "at least five of six demanded capabilities; then most capabilities, "
            "highest discovery score, and stable candidate ID."
        ),
        "provenance": data.get("provenance"),
        "boundary": data.get("boundary"),
    }


def run_case() -> dict[str, Any]:
    """Search for a needed API and screen candidates without executing them."""
    tooluniverse = ToolUniverse()
    tooluniverse.load_tools(include_tools=["VSDDiscoverAPICandidates"], quiet=True)
    try:
        result = tooluniverse.run_one_function(
            {
                "name": "VSDDiscoverAPICandidates",
                "arguments": {"query": QUERY, "limit": 10},
            },
            use_cache=False,
        )
    finally:
        tooluniverse.close()
    if not isinstance(result, dict) or result.get("status") != "success":
        raise RuntimeError(f"Discovery did not succeed: {result!r}")
    analysis = analyze_discovery(result["data"])
    if analysis["selected_candidate"] is None:
        raise RuntimeError(
            "No candidate satisfied the documented review-readiness rule"
        )
    return {
        "case": {
            "question": (
                "Can ToolUniverse discover an API-ready public dataset for analyzing "
                "active cancer trials by protocol, site, phase, title, opening date, "
                "and investigator without executing an unreviewed endpoint?"
            ),
            "demand_query": QUERY,
            "desired_capabilities": list(DESIRED_CAPABILITIES),
            "interpretation_boundary": (
                "Selection means suitable for human contract review only. It does not "
                "approve the source, validate its scientific content, or execute it."
            ),
        },
        "analysis": analysis,
    }


def render_markdown(evidence: dict[str, Any]) -> str:
    """Render the discovery evidence as an analyst-facing review brief."""
    case = evidence["case"]
    analysis = evidence["analysis"]
    selected = analysis["selected_candidate"]
    lines = [
        "# Demand-Driven API Discovery Validation",
        "",
        "## Decision Question",
        "",
        case["question"],
        "",
        "## Search Result",
        "",
        f"- Demand query: `{case['demand_query']}`",
        f"- Catalog matches: **{analysis['catalog_result_count']}**",
        f"- Normalized API candidates: **{analysis['normalized_candidate_count']}**",
        f"- Candidates passing the review-readiness screen: **{analysis['recommended_candidate_count']}**",
        "",
        "## Candidate Comparison",
        "",
        "| Candidate | Score | Fields | Capabilities | Official | Government | Review next |",
        "| --- | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for candidate in analysis["candidates"]:
        name = str(candidate["name"]).replace("|", "\\|")
        score = candidate["score"]
        lines.append(
            f"| {name} | {score['total']:.4f} | {len(candidate['fields'])} | "
            f"{candidate['matched_capability_count']}/{candidate['desired_capability_count']} | "
            f"{'yes' if score['official_catalog_label'] else 'no'} | "
            f"{'yes' if score['government_domain'] else 'no'} | "
            f"{'yes' if candidate['recommended_for_contract_review'] else 'no'} |"
        )
    lines.extend(
        [
            "",
            "## Selected for Contract Review",
            "",
            f"- Name: **{selected['name']}**",
            f"- Candidate ID: `{selected['candidate_id']}`",
            f"- Proposed API endpoint: `{selected['api_endpoint']}`",
            f"- Catalog record: {selected['documentation_url']}",
            f"- Dataset updated: `{selected['updated_at']}`",
            "- Execution allowed: **no**",
            "",
            "| Requested capability | Candidate field |",
            "| --- | --- |",
        ]
    )
    for capability, field in selected["capability_matches"].items():
        lines.append(f"| {capability} | `{field or 'not found'}` |")
    lines.extend(
        [
            "",
            "## Reproducibility",
            "",
            f"- Catalog endpoint: `{analysis['provenance']['endpoint']}`",
            f"- Retrieved at: `{analysis['provenance']['retrieved_at']}`",
            f"- Catalog payload: `{analysis['provenance']['payload_sha256']}`",
            f"- Selection rule: {analysis['selection_rule']}",
            "",
            "## Interpretation Boundary",
            "",
            case["interpretation_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def write_artifacts(evidence: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    """Write the full evidence ledger and human-readable review brief."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "api_discovery_snapshot.json"
    markdown_path = output_dir / "api_discovery_snapshot.md"
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
