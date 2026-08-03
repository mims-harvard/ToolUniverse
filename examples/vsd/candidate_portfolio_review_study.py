"""Review every draft-ready candidate from the exhaustive VSD catalog scan."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Sequence
from urllib.parse import urlsplit

from tooluniverse.vsd_openapi import inspect_openapi_document
from tooluniverse.vsd_promotion import (
    VSDPromotionError,
    create_openapi_draft,
    publish_draft,
    verify_draft,
)
from tooluniverse.vsd_source_intelligence import _fetch_https

from examples.vsd.continuous_catalog_expansion_study import (
    CATALOG_RUNNERS,
    _history,
    validate_portfolio,
)
from examples.vsd.scanner_cancer_qualification_study import validate_study

HERE = Path(__file__).resolve().parent
POLICY_PATH = HERE / "candidate_portfolio_review_policy.json"
EXPANSION_PATH = HERE / "artifacts" / "continuous_catalog_expansion_study.json"
QUALIFICATION_PATH = HERE / "artifacts" / "scanner_cancer_qualification_study.json"
JSON_ARTIFACT = HERE / "artifacts" / "candidate_portfolio_review_study.json"
MARKDOWN_ARTIFACT = HERE / "artifacts" / "candidate_portfolio_review_study.md"
_HOST_ENV = "TOOLUNIVERSE_VSD_ALLOWED_HOSTS"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_PATH_PARAMETER_RE = re.compile(r"\{[^{}]+\}")
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_INITIAL_ELIGIBLE_DECISIONS = {
    "eligible_general_anonymous_verification_on_demand",
    "eligible_general_parameterized_verification_on_demand",
    "eligible_scientific_anonymous_verification",
    "eligible_scientific_parameterized_verification",
}
_FINAL_ELIGIBLE_DECISIONS = {
    "eligible_general_no_input_live_verification_on_demand",
    "eligible_general_parameterized_verification_on_demand",
    "eligible_scientific_no_input_live_verification",
    "eligible_scientific_parameterized_verification",
    "eligible_service_utility_verification_on_demand",
}
_SCIENTIFIC_ELIGIBLE_DECISIONS = {
    "eligible_scientific_no_input_live_verification",
    "eligible_scientific_parameterized_verification",
}


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _read_json(path: Path, *, maximum: int) -> Any:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > maximum:
        raise ValueError(f"Review input {path.name!r} is missing or too large")
    return json.loads(path.read_text(encoding="utf-8"))


def _string_list(value: Any, field: str, *, maximum: int = 100) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or len(value) > maximum
        or len(value) != len(set(value))
        or any(not isinstance(item, str) or not 1 <= len(item) <= 100 for item in value)
    ):
        raise ValueError(f"Review policy {field!r} is invalid")
    return list(value)


def validate_policy(value: Any) -> dict[str, Any]:
    required = {
        "format",
        "version",
        "stale_after_days",
        "live_shortlist_limit",
        "side_effect_tokens",
        "access_control_tokens",
        "credential_warning_tokens",
        "nonproduction_host_labels",
        "public_authority_suffixes",
        "service_utility_tokens",
        "scientific_strong_terms",
        "scientific_context_terms",
    }
    if (
        not isinstance(value, dict)
        or set(value) != required
        or value.get("format") != "vsd_candidate_portfolio_review_policy_v1"
        or value.get("version") != 1
        or type(value.get("stale_after_days")) is not int
        or not 365 <= value["stale_after_days"] <= 3650
        or type(value.get("live_shortlist_limit")) is not int
        or not 1 <= value["live_shortlist_limit"] <= 50
    ):
        raise ValueError("Candidate portfolio review policy is invalid")
    checked = dict(value)
    for field in (
        "side_effect_tokens",
        "access_control_tokens",
        "credential_warning_tokens",
        "nonproduction_host_labels",
        "public_authority_suffixes",
        "service_utility_tokens",
        "scientific_strong_terms",
        "scientific_context_terms",
    ):
        checked[field] = _string_list(value[field], field)
    token_fields = (
        "side_effect_tokens",
        "access_control_tokens",
        "credential_warning_tokens",
        "nonproduction_host_labels",
        "service_utility_tokens",
        "scientific_strong_terms",
        "scientific_context_terms",
    )
    for field in token_fields:
        normalized = [item.casefold() for item in checked[field]]
        if normalized != sorted(normalized) or any(
            not re.fullmatch(r"[a-z0-9-]+", item) for item in normalized
        ):
            raise ValueError(f"Review policy {field!r} must be normalized and sorted")
        checked[field] = normalized
    suffixes = [item.casefold() for item in checked["public_authority_suffixes"]]
    if suffixes != sorted(suffixes) or any(
        not item.startswith(".") for item in suffixes
    ):
        raise ValueError("Review policy authority suffixes are invalid")
    checked["public_authority_suffixes"] = suffixes
    return checked


def _timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ValueError("Review evidence timestamp is invalid") from exc
    if parsed.tzinfo is None:
        raise ValueError("Review evidence timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def _tokens(*values: Any) -> set[str]:
    text = " ".join(str(value or "") for value in values)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return set(_TOKEN_RE.findall(text.casefold()))


def load_catalog_cycles(state_root: Path) -> dict[str, list[dict[str, Any]]]:
    cycles = {
        catalog_id: _history(state_root / catalog_id)
        for catalog_id in sorted(CATALOG_RUNNERS)
    }
    if any(not items for items in cycles.values()):
        raise ValueError("Both exhaustive catalog histories are required")
    return cycles


def _candidate_inventory(
    catalog_cycles: dict[str, Sequence[dict[str, Any]]],
) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    identity_fields = (
        "candidate_sha256",
        "record_id",
        "host",
        "method",
        "path",
    )
    for catalog_id in sorted(catalog_cycles):
        cycles = catalog_cycles[catalog_id]
        records = {
            item["record_id"]: item for item in cycles[-1]["directory"]["records"]
        }
        for cycle in cycles:
            for operation in cycle["operations"]:
                preview = operation.get("preview")
                if preview is None:
                    continue
                record = records.get(operation["record_id"])
                if record is None:
                    raise ValueError("Candidate record is absent from catalog snapshot")
                review = {
                    "catalog_id": catalog_id,
                    "record_id": operation["record_id"],
                    "record_sha256": record["record_sha256"],
                    "record_updated_at": record["updated_at"],
                    "provider_name": record["provider_name"],
                    "categories": record["categories"],
                    "specification_url": record["specification_url"],
                    "api_title": operation["api_title"],
                    "api_version": operation["api_version"],
                    "content_sha256": operation["content_sha256"],
                    "candidate_id": operation["candidate_id"],
                    "candidate_sha256": operation["candidate_sha256"],
                    "operation_id": operation["operation_id"],
                    "method": operation["method"],
                    "host": operation["host"].casefold(),
                    "path": operation["path"],
                    "warnings": operation["warnings"],
                    "registry_coverage": operation["registry_coverage"],
                    "existing_tools": operation["existing_tools"],
                    "preview_tool_name": preview["tool_name"],
                    "preview_config_sha256": preview["config_sha256"],
                    "approval_state": operation["approval_state"],
                    "execution_allowed": operation["execution_allowed"],
                }
                key = review["preview_config_sha256"]
                previous = unique.get(key)
                if previous is not None and any(
                    previous[field] != review[field] for field in identity_fields
                ):
                    raise ValueError(
                        "Configuration hash maps to conflicting candidates"
                    )
                unique.setdefault(key, review)
    return [unique[key] for key in sorted(unique)]


def _endpoint_key(candidate: dict[str, Any]) -> str:
    return "|".join((candidate["host"], candidate["method"].upper(), candidate["path"]))


def _scientific_matches(
    candidate: dict[str, Any], policy: dict[str, Any], *, authority: bool
) -> tuple[list[str], int]:
    metadata_tokens = _tokens(
        candidate["api_title"],
        candidate["provider_name"],
        " ".join(candidate["categories"]),
    )
    operation_tokens = _tokens(candidate["operation_id"], candidate["path"])
    all_tokens = metadata_tokens | operation_tokens
    strong = sorted(all_tokens & set(policy["scientific_strong_terms"]))
    contextual = sorted(metadata_tokens & set(policy["scientific_context_terms"]))
    if not (strong or candidate["catalog_id"] == "smartapi" or authority):
        contextual = []
    matches = [*strong, *contextual]
    return matches, len(strong) * 2 + len(contextual)


def _preferred_endpoint_variants(
    candidates: list[dict[str, Any]],
) -> tuple[dict[str, str], Counter[str]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        groups[_endpoint_key(candidate)].append(candidate)
    preferred: dict[str, str] = {}
    sizes: Counter[str] = Counter()
    for key, items in groups.items():
        selected = max(
            items,
            key=lambda item: (
                item["record_updated_at"],
                item["api_version"],
                item["preview_config_sha256"],
            ),
        )
        preferred[key] = selected["preview_config_sha256"]
        sizes[key] = len(items)
    return preferred, sizes


def _review_candidate(
    candidate: dict[str, Any],
    *,
    policy: dict[str, Any],
    evaluated_at: datetime,
    preferred_variants: dict[str, str],
    endpoint_sizes: Counter[str],
) -> dict[str, Any]:
    operation_tokens = _tokens(candidate["operation_id"], candidate["path"])
    side_effects = sorted(operation_tokens & set(policy["side_effect_tokens"]))
    access_terms = sorted(operation_tokens & set(policy["access_control_tokens"]))
    service_utility = sorted(operation_tokens & set(policy["service_utility_tokens"]))
    warning_text = " ".join(candidate["warnings"]).casefold()
    credential_warnings = sorted(
        item for item in policy["credential_warning_tokens"] if item in warning_text
    )
    host_labels = _tokens(candidate["host"])
    nonproduction = sorted(host_labels & set(policy["nonproduction_host_labels"]))
    updated_at = _timestamp(candidate["record_updated_at"])
    age_days = max(0, (evaluated_at - updated_at).days)
    stale = age_days > policy["stale_after_days"]
    endpoint_key = _endpoint_key(candidate)
    superseded = (
        endpoint_sizes[endpoint_key] > 1
        and preferred_variants[endpoint_key] != candidate["preview_config_sha256"]
    )
    path_parameters = sorted(set(_PATH_PARAMETER_RE.findall(candidate["path"])))
    authority = any(
        candidate["host"].endswith(suffix)
        for suffix in policy["public_authority_suffixes"]
    )
    scientific_matches, scientific_score = _scientific_matches(
        candidate, policy, authority=authority
    )
    reasons: list[str] = []
    if side_effects:
        reasons.append("potential_side_effect_semantics")
    if access_terms or credential_warnings:
        reasons.append("possible_undeclared_access_control")
    if nonproduction:
        reasons.append("nonproduction_endpoint")
    if superseded:
        reasons.append("superseded_endpoint_variant")
    if stale:
        reasons.append("stale_catalog_metadata")
    if candidate["warnings"]:
        reasons.append("contract_warnings_present")
    if path_parameters:
        reasons.append("scenario_inputs_required")
    if scientific_score:
        reasons.append("scientific_vocabulary_match")
    if authority:
        reasons.append("public_authority_host")
    if service_utility:
        reasons.append("service_utility_operation")

    if side_effects:
        decision = "hold_potential_side_effect"
    elif access_terms or credential_warnings:
        decision = "hold_undeclared_access_control"
    elif nonproduction:
        decision = "hold_nonproduction_endpoint"
    elif superseded:
        decision = "superseded_endpoint_variant"
    elif stale:
        decision = "hold_stale_catalog_record"
    elif scientific_score and path_parameters:
        decision = "eligible_scientific_parameterized_verification"
    elif scientific_score:
        decision = "eligible_scientific_anonymous_verification"
    elif path_parameters:
        decision = "eligible_general_parameterized_verification_on_demand"
    else:
        decision = "eligible_general_anonymous_verification_on_demand"

    priority_score = (
        scientific_score * 100
        + (20 if authority else 0)
        + (10 if not path_parameters else 0)
        + (5 if age_days <= 365 else 0)
        - min(age_days // 365, 10)
        - len(candidate["warnings"]) * 3
    )
    return {
        **candidate,
        "endpoint_identity_sha256": _digest(endpoint_key),
        "endpoint_variant_count": endpoint_sizes[endpoint_key],
        "path_parameter_count": len(path_parameters),
        "record_age_days": age_days,
        "scientific_matches": scientific_matches,
        "scientific_term_matches": scientific_score,
        "public_authority_host": authority,
        "service_utility_tokens": service_utility,
        "risk_evidence": {
            "side_effect_tokens": side_effects,
            "access_control_tokens": access_terms,
            "credential_warning_tokens": credential_warnings,
            "nonproduction_host_labels": nonproduction,
        },
        "review_decision": decision,
        "review_reasons": sorted(set(reasons)),
        "review_state": "static_review_complete",
        "review_priority_score": priority_score,
        "source_trust": "catalog_record_only_requires_provider_review",
    }


def _shortlist(
    reviews: list[dict[str, Any]], maximum: int, *, decision: str
) -> list[dict[str, Any]]:
    eligible = [item for item in reviews if item["review_decision"] == decision]
    eligible.sort(
        key=lambda item: (
            -item["review_priority_score"],
            item["host"],
            item["operation_id"].casefold(),
            item["preview_config_sha256"],
        )
    )
    by_host: dict[str, list[dict[str, Any]]] = defaultdict(list)
    host_order: list[str] = []
    for item in eligible:
        if item["host"] not in by_host:
            host_order.append(item["host"])
        by_host[item["host"]].append(item)
    selected: list[dict[str, Any]] = []
    rank = 0
    while len(selected) < maximum and rank < 2:
        added = False
        for host in host_order:
            if rank >= len(by_host[host]):
                continue
            selected.append(by_host[host][rank])
            added = True
            if len(selected) >= maximum:
                break
        if not added:
            break
        rank += 1
    return selected


def build_static_review(
    catalog_cycles: dict[str, Sequence[dict[str, Any]]],
    expansion: Any,
    qualification: Any,
    policy: Any,
) -> dict[str, Any]:
    checked_expansion = validate_portfolio(expansion)
    checked_qualification = validate_study(qualification)
    checked_policy = validate_policy(policy)
    candidates = _candidate_inventory(catalog_cycles)
    expected = checked_expansion["combined_results"]
    config_hashes = {item["preview_config_sha256"] for item in candidates}
    if (
        len(candidates) != expected["unique_draft_ready_count"]
        or _digest(sorted(config_hashes)) != expected["draft_ready_set_sha256"]
    ):
        raise ValueError("Review inventory does not match exhaustive scan evidence")
    evaluated_at = max(
        _timestamp(cycles[-1]["scanned_at"]) for cycles in catalog_cycles.values()
    )
    preferred, endpoint_sizes = _preferred_endpoint_variants(candidates)
    reviews = [
        _review_candidate(
            item,
            policy=checked_policy,
            evaluated_at=evaluated_at,
            preferred_variants=preferred,
            endpoint_sizes=endpoint_sizes,
        )
        for item in candidates
    ]
    reviews.sort(
        key=lambda item: (
            item["review_decision"],
            -item["review_priority_score"],
            item["host"],
            item["operation_id"].casefold(),
            item["preview_config_sha256"],
        )
    )
    decision_counts = Counter(item["review_decision"] for item in reviews)
    reason_counts = Counter(
        reason for item in reviews for reason in item["review_reasons"]
    )
    catalog_counts = Counter(item["catalog_id"] for item in reviews)
    warning_counts = Counter(
        warning for item in reviews for warning in item["warnings"]
    )
    initial_live_decision = "eligible_scientific_anonymous_verification"
    shortlist = _shortlist(
        reviews,
        checked_policy["live_shortlist_limit"],
        decision=initial_live_decision,
    )
    host_counts = Counter(item["host"] for item in reviews)
    body = {
        "format": "vsd_candidate_portfolio_review_study_v1",
        "version": 1,
        "evaluation_mode": "exhaustive_static_review_with_bounded_live_verification",
        "generated_at": evaluated_at.isoformat(),
        "objective": (
            "Apply a documented review policy to every unique draft-ready scanner "
            "configuration and measure the smaller set that merits live verification."
        ),
        "review_boundary": (
            "Static review is a portfolio triage decision, not source approval. Catalog "
            "membership does not establish provider trust, anonymous accessibility, "
            "scientific validity, or permission to publish a tool."
        ),
        "policy": checked_policy,
        "source_evidence": {
            "expansion_portfolio_sha256": checked_expansion["portfolio_sha256"],
            "draft_ready_set_sha256": expected["draft_ready_set_sha256"],
            "expected_draft_ready_candidate_count": expected[
                "unique_draft_ready_count"
            ],
            "exhaustive_operation_candidate_count": expected["unique_operation_count"],
            "qualification_study_sha256": checked_qualification["study_sha256"],
            "previous_live_accepted_operation_count": len(
                checked_qualification["promotions"]
            ),
            "previous_live_rejected_operation_count": len(
                checked_qualification["rejections"]
            ),
            "previous_scientific_workflow_count": len(checked_qualification["studies"]),
        },
        "summary": {
            "reviewed_candidate_count": len(reviews),
            "reviewed_host_count": len(host_counts),
            "unique_endpoint_identity_count": len(endpoint_sizes),
            "duplicate_endpoint_variant_count": sum(
                count - 1 for count in endpoint_sizes.values()
            ),
            "scientific_candidate_count": sum(
                item["scientific_term_matches"] > 0 for item in reviews
            ),
            "statically_eligible_count": sum(
                item["review_decision"] in _INITIAL_ELIGIBLE_DECISIONS
                for item in reviews
            ),
            "held_or_superseded_count": sum(
                item["review_decision"] not in _INITIAL_ELIGIBLE_DECISIONS
                for item in reviews
            ),
            "anonymous_verification_eligible_count": sum(
                "anonymous_verification" in item["review_decision"] for item in reviews
            ),
            "parameterized_verification_eligible_count": sum(
                "parameterized_verification" in item["review_decision"]
                for item in reviews
            ),
            "live_shortlist_count": len(shortlist),
            "decision_counts": dict(sorted(decision_counts.items())),
            "reason_counts": dict(
                sorted(reason_counts.items(), key=lambda item: (-item[1], item[0]))
            ),
            "catalog_counts": dict(sorted(catalog_counts.items())),
            "warning_counts": dict(
                sorted(warning_counts.items(), key=lambda item: (-item[1], item[0]))
            ),
            "top_candidate_hosts": [
                {"host": host, "candidate_count": count}
                for host, count in sorted(
                    host_counts.items(), key=lambda item: (-item[1], item[0])
                )[:30]
            ],
        },
        "live_shortlist": [
            {
                key: item[key]
                for key in (
                    "catalog_id",
                    "record_id",
                    "specification_url",
                    "api_title",
                    "candidate_id",
                    "candidate_sha256",
                    "operation_id",
                    "host",
                    "path",
                    "preview_config_sha256",
                    "scientific_term_matches",
                    "review_priority_score",
                )
            }
            for item in shortlist
        ],
        "candidate_reviews": reviews,
        "contract_review": {
            "status": "not_run",
            "record_count": 0,
            "current_candidate_count": 0,
            "results": [],
        },
        "live_review": {
            "status": "not_run",
            "attempted_count": 0,
            "verified_count": 0,
            "results": [],
        },
    }
    shortlist_host_counts = Counter(item["host"] for item in shortlist)
    assertions = {
        "every_scan_candidate_received_a_review_decision": len(reviews)
        == expected["unique_draft_ready_count"]
        and len(decision_counts) > 1,
        "review_inventory_matches_exhaustive_scan": _digest(sorted(config_hashes))
        == expected["draft_ready_set_sha256"],
        "every_review_remains_inert_and_unapproved": all(
            item["approval_state"] == "unreviewed_operation_candidate"
            and item["execution_allowed"] is False
            and item["source_trust"] == "catalog_record_only_requires_provider_review"
            for item in reviews
        ),
        "every_review_has_one_deterministic_disposition": sum(decision_counts.values())
        == len(reviews),
        "live_shortlist_is_scientific_anonymous_and_host_balanced": all(
            next(
                review
                for review in reviews
                if review["preview_config_sha256"] == item["preview_config_sha256"]
            )["review_decision"]
            == initial_live_decision
            for item in shortlist
        )
        and max(shortlist_host_counts.values(), default=0)
        - min(shortlist_host_counts.values(), default=0)
        <= 1,
    }
    body["assertions"] = assertions
    if not all(assertions.values()):
        failed = sorted(key for key, result in assertions.items() if not result)
        raise AssertionError(
            f"Candidate portfolio static-review assertions failed: {failed!r}"
        )
    return {**body, "review_sha256": _digest(body)}


def _contract_candidate_evidence(candidate: dict[str, Any]) -> dict[str, Any]:
    parameters = candidate.get("parameters")
    if not isinstance(parameters, list):
        raise ValueError("Current contract candidate has no parameter inventory")
    required = [
        {
            "argument_name": item["argument_name"],
            "provider_name": item["provider_name"],
            "location": item["location"],
        }
        for item in parameters
        if item.get("required") is True
    ]
    response_schema = candidate.get("response_schema")
    response_type = (
        response_schema.get("type") if isinstance(response_schema, dict) else None
    )
    return {
        "contract_review_status": "current_candidate_confirmed",
        "current_warning_count": len(candidate.get("warnings", [])),
        "parameter_count": len(parameters),
        "required_parameter_count": len(required),
        "required_path_parameter_count": sum(
            item["location"] == "path" for item in required
        ),
        "required_query_parameter_count": sum(
            item["location"] == "query" for item in required
        ),
        "required_parameters": required,
        "response_schema_type": response_type,
        "response_expectation_available": _verification_expectation(candidate)
        is not None,
    }


def _scientific_families(reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in reviews:
        if (
            item["scientific_term_matches"] > 0
            and item["review_decision"] in _SCIENTIFIC_ELIGIBLE_DECISIONS
        ):
            groups[item["host"]].append(item)
    families = []
    for host, items in groups.items():
        operations = sorted(
            items,
            key=lambda item: (
                -item["review_priority_score"],
                item["operation_id"].casefold(),
            ),
        )
        families.append(
            {
                "host": host,
                "api_titles": sorted({item["api_title"] for item in items}),
                "candidate_count": len(items),
                "no_input_count": sum(
                    item["review_decision"]
                    == "eligible_scientific_no_input_live_verification"
                    for item in items
                ),
                "parameterized_count": sum(
                    item["review_decision"]
                    == "eligible_scientific_parameterized_verification"
                    for item in items
                ),
                "sample_operations": list(
                    dict.fromkeys(item["operation_id"] for item in operations)
                )[:8],
            }
        )
    return sorted(families, key=lambda item: (-item["candidate_count"], item["host"]))


def run_contract_review(static_review: Any) -> dict[str, Any]:
    checked = validate_review(static_review, require_contract=False, require_live=False)
    reviews = checked["candidate_reviews"]
    by_record: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in reviews:
        by_record[item["record_id"]].append(item)

    source_results: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    for index, record_id in enumerate(sorted(by_record), start=1):
        items = by_record[record_id]
        first = items[0]
        source_result: dict[str, Any] = {
            "record_id": record_id,
            "catalog_id": first["catalog_id"],
            "specification_url": first["specification_url"],
            "recorded_content_sha256s": sorted(
                {item["content_sha256"] for item in items}
            ),
            "reviewed_candidate_count": len(items),
        }
        try:
            raw, request = _fetch_https(first["specification_url"], 30, 1_000_000)
            with tempfile.TemporaryDirectory(
                prefix="tooluniverse-vsd-contract-review-"
            ) as directory:
                specification = Path(directory) / "specification.json"
                specification.write_bytes(raw)
                inspection = inspect_openapi_document(specification)
            current = {
                item["candidate_sha256"]: item for item in inspection["candidates"]
            }
            matched = 0
            for item in items:
                candidate = current.get(item["candidate_sha256"])
                if candidate is None:
                    item.update(
                        {
                            "contract_review_status": "candidate_changed_or_removed",
                            "review_state": "contract_review_complete",
                        }
                    )
                    continue
                matched += 1
                item.update(_contract_candidate_evidence(candidate))
                item["review_state"] = "contract_review_complete"
            source_result.update(
                {
                    "status": "contract_refreshed",
                    "http_status": request["status_code"],
                    "content_type": request["content_type"],
                    "response_bytes": request["response_bytes"],
                    "source_document_sha256": inspection["source_document_sha256"],
                    "current_candidate_count": len(inspection["candidates"]),
                    "matched_candidate_count": matched,
                    "changed_or_removed_candidate_count": len(items) - matched,
                }
            )
        except Exception as exc:  # noqa: BLE001
            for item in items:
                item.update(
                    {
                        "contract_review_status": "contract_refresh_failed",
                        "review_state": "contract_review_complete",
                    }
                )
            source_result.update(
                {
                    "status": "contract_refresh_failed",
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:1000],
                }
            )
        source_results.append(source_result)
        if index % 25 == 0 or index == len(by_record):
            print(
                json.dumps(
                    {
                        "contract_sources_reviewed": index,
                        "contract_source_total": len(by_record),
                    },
                    sort_keys=True,
                ),
                flush=True,
            )

    for item in reviews:
        initial = item["review_decision"]
        item["initial_review_decision"] = initial
        status = item["contract_review_status"]
        reasons = set(item["review_reasons"])
        if initial not in _INITIAL_ELIGIBLE_DECISIONS:
            decision = initial
        elif status == "contract_refresh_failed":
            decision = "hold_contract_refresh_failed"
            reasons.add("contract_refresh_failed")
        elif status == "candidate_changed_or_removed":
            decision = "hold_contract_drift"
            reasons.add("candidate_changed_or_removed")
        elif item["service_utility_tokens"]:
            decision = "eligible_service_utility_verification_on_demand"
        elif item["required_parameter_count"]:
            reasons.add("required_contract_parameters")
            decision = (
                "eligible_scientific_parameterized_verification"
                if item["scientific_term_matches"] > 0
                else "eligible_general_parameterized_verification_on_demand"
            )
        elif item["response_expectation_available"]:
            decision = (
                "eligible_scientific_no_input_live_verification"
                if item["scientific_term_matches"] > 0
                else "eligible_general_no_input_live_verification_on_demand"
            )
        else:
            decision = "hold_weak_response_contract"
            reasons.add("response_shape_cannot_support_verification_assertions")
        item["review_decision"] = decision
        item["review_reasons"] = sorted(reasons)
        status_counts[status] += 1

    reviews.sort(
        key=lambda item: (
            item["review_decision"],
            -item["review_priority_score"],
            item["host"],
            item["operation_id"].casefold(),
            item["preview_config_sha256"],
        )
    )
    decision_counts = Counter(item["review_decision"] for item in reviews)
    reason_counts = Counter(
        reason for item in reviews for reason in item["review_reasons"]
    )
    final_live_decision = "eligible_scientific_no_input_live_verification"
    shortlist = _shortlist(
        reviews,
        checked["policy"]["live_shortlist_limit"],
        decision=final_live_decision,
    )
    shortlist_host_counts = Counter(item["host"] for item in shortlist)
    summary = {
        **checked["summary"],
        "initial_decision_counts": checked["summary"]["decision_counts"],
        "initial_statically_eligible_count": checked["summary"][
            "statically_eligible_count"
        ],
        "decision_counts": dict(sorted(decision_counts.items())),
        "reason_counts": dict(
            sorted(reason_counts.items(), key=lambda item: (-item[1], item[0]))
        ),
        "contract_status_counts": dict(sorted(status_counts.items())),
        "review_eligible_count": sum(
            item["review_decision"] in _FINAL_ELIGIBLE_DECISIONS for item in reviews
        ),
        "held_or_superseded_count": sum(
            item["review_decision"] not in _FINAL_ELIGIBLE_DECISIONS for item in reviews
        ),
        "no_input_live_verification_eligible_count": sum(
            "no_input_live_verification" in item["review_decision"] for item in reviews
        ),
        "parameterized_verification_eligible_count": sum(
            "parameterized_verification" in item["review_decision"] for item in reviews
        ),
        "scientific_review_eligible_count": sum(
            item["scientific_term_matches"] > 0
            and item["review_decision"] in _SCIENTIFIC_ELIGIBLE_DECISIONS
            for item in reviews
        ),
        "service_utility_eligible_count": sum(
            item["review_decision"] == "eligible_service_utility_verification_on_demand"
            for item in reviews
        ),
        "live_shortlist_count": len(shortlist),
        "eligible_scientific_families": _scientific_families(reviews),
    }
    contract_review = {
        "status": "completed",
        "record_count": len(source_results),
        "refreshed_record_count": sum(
            item["status"] == "contract_refreshed" for item in source_results
        ),
        "failed_record_count": sum(
            item["status"] == "contract_refresh_failed" for item in source_results
        ),
        "current_candidate_count": status_counts["current_candidate_confirmed"],
        "changed_or_removed_candidate_count": status_counts[
            "candidate_changed_or_removed"
        ],
        "results_sha256": _digest(source_results),
        "results": source_results,
    }
    body = {
        key: value
        for key, value in checked.items()
        if key
        not in {
            "review_sha256",
            "assertions",
            "candidate_reviews",
            "contract_review",
            "live_review",
            "live_shortlist",
            "summary",
        }
    }
    body.update(
        {
            "summary": summary,
            "candidate_reviews": reviews,
            "contract_review": contract_review,
            "live_shortlist": [
                {
                    key: item[key]
                    for key in (
                        "catalog_id",
                        "record_id",
                        "specification_url",
                        "api_title",
                        "candidate_id",
                        "candidate_sha256",
                        "operation_id",
                        "host",
                        "path",
                        "preview_config_sha256",
                        "scientific_term_matches",
                        "review_priority_score",
                    )
                }
                for item in shortlist
            ],
            "live_review": {
                "status": "not_run",
                "attempted_count": 0,
                "verified_count": 0,
                "results": [],
            },
        }
    )
    assertions = dict(checked["assertions"])
    assertions.pop("live_shortlist_is_scientific_anonymous_and_host_balanced", None)
    assertions.update(
        {
            "all_candidate_sources_received_contract_review": sum(
                status_counts.values()
            )
            == len(reviews),
            "contract_review_covered_every_draft_producing_record": len(source_results)
            == len(by_record),
            "contract_shortlist_is_scientific_no_input_and_host_balanced": all(
                next(
                    review
                    for review in reviews
                    if review["preview_config_sha256"] == item["preview_config_sha256"]
                )["review_decision"]
                == final_live_decision
                for item in shortlist
            )
            and max(shortlist_host_counts.values(), default=0)
            - min(shortlist_host_counts.values(), default=0)
            <= 1,
            "contract_review_preserved_inert_approval_boundary": all(
                item["approval_state"] == "unreviewed_operation_candidate"
                and item["execution_allowed"] is False
                for item in reviews
            ),
        }
    )
    body["assertions"] = assertions
    if not all(assertions.values()):
        failed = sorted(key for key, result in assertions.items() if not result)
        raise AssertionError(f"Candidate contract-review assertions failed: {failed!r}")
    return {**body, "review_sha256": _digest(body)}


@contextmanager
def _allowed_hosts(hosts: set[str]) -> Iterator[None]:
    previous = os.environ.get(_HOST_ENV)
    existing = {
        item.strip().casefold() for item in (previous or "").split(",") if item.strip()
    }
    os.environ[_HOST_ENV] = ",".join(sorted(existing | hosts))
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(_HOST_ENV, None)
        else:
            os.environ[_HOST_ENV] = previous


def _verification_expectation(candidate: dict[str, Any]) -> dict[str, Any] | None:
    schema = candidate.get("response_schema")
    if not isinstance(schema, dict):
        return None
    result_type = schema.get("type")
    target = schema
    if result_type == "array":
        target = schema.get("items")
        if not isinstance(target, dict) or target.get("type") != "object":
            return None
    elif result_type != "object":
        return None
    properties = target.get("properties")
    if not isinstance(properties, dict) or not properties:
        return None
    required = target.get("required")
    fields = (
        [item for item in required if isinstance(item, str) and item in properties]
        if isinstance(required, list)
        else []
    )
    if not fields:
        fields = [sorted(properties)[0]]
    expectation = {
        "result_type": result_type,
        "required_fields": fields[:10],
        "required_paths": [],
    }
    if result_type == "array":
        expectation.update({"min_items": 0, "max_items": 100})
    return expectation


def run_live_review(static_review: Any) -> dict[str, Any]:
    checked = validate_review(static_review, require_live=False)
    results: list[dict[str, Any]] = []
    fetched: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for selected in checked["live_shortlist"]:
        result = {
            "preview_config_sha256": selected["preview_config_sha256"],
            "record_id": selected["record_id"],
            "candidate_sha256": selected["candidate_sha256"],
            "host": selected["host"],
            "operation_id": selected["operation_id"],
            "path": selected["path"],
        }
        try:
            if selected["record_id"] not in fetched:
                raw, request = _fetch_https(
                    selected["specification_url"], 30, 10_000_000
                )
                with tempfile.TemporaryDirectory(
                    prefix="tooluniverse-vsd-review-spec-"
                ) as directory:
                    specification = Path(directory) / "specification.json"
                    specification.write_bytes(raw)
                    inspection = inspect_openapi_document(specification)
                fetched[selected["record_id"]] = (inspection, request)
            inspection, request = fetched[selected["record_id"]]
            matches = [
                item
                for item in inspection["candidates"]
                if item["candidate_sha256"] == selected["candidate_sha256"]
            ]
            if len(matches) != 1:
                raise ValueError(
                    "Live contract no longer contains the reviewed candidate"
                )
            candidate = matches[0]
            if candidate["blockers"] or candidate["auth"] is not None:
                raise ValueError(
                    "Live candidate no longer satisfies anonymous draft policy"
                )
            host = (urlsplit(candidate["server_url"]).hostname or "").casefold()
            if host != selected["host"]:
                raise ValueError("Live candidate host differs from scanner evidence")
            required = [
                item["argument_name"]
                for item in candidate["parameters"]
                if item["required"] is True
            ]
            if required:
                result.update(
                    {
                        "decision": "deferred_required_parameters",
                        "required_parameters": sorted(required),
                    }
                )
                results.append(result)
                continue
            expectation = _verification_expectation(candidate)
            if expectation is None:
                result["decision"] = "deferred_unverifiable_response_shape"
                results.append(result)
                continue
            with tempfile.TemporaryDirectory(
                prefix="tooluniverse-vsd-review-"
            ) as workspace:
                draft = create_openapi_draft(
                    candidate,
                    tool_name=f"VSDReview{candidate['candidate_id'][:16]}",
                    description=(
                        "Reviewed live probe for a catalog-discovered read-only operation."
                    ),
                    workspace=workspace,
                    timeout_seconds=20,
                )
                premature_blocked = False
                try:
                    publish_draft(draft["draft_id"], workspace=workspace)
                except VSDPromotionError:
                    premature_blocked = True
                if not premature_blocked:
                    raise AssertionError("Unapproved review draft was published")
                cases = [{"arguments": {}, "expect": expectation} for _ in range(3)]
                with _allowed_hosts({host}):
                    evidence = verify_draft(
                        draft["draft_id"], cases, workspace=workspace
                    )
                result.update(
                    {
                        "decision": "verified_live_unapproved",
                        "specification_status": request["status_code"],
                        "specification_content_type": request["content_type"],
                        "specification_response_bytes": request["response_bytes"],
                        "source_document_sha256": inspection["source_document_sha256"],
                        "draft_sha256": draft["draft_sha256"],
                        "operation_sha256": draft["operation_sha256"],
                        "verification_sha256": evidence["verification_sha256"],
                        "verification_case_count": evidence["case_count"],
                        "verification_cases": evidence["cases"],
                        "premature_publication_blocked": premature_blocked,
                        "approval_state": "unapproved_verified_draft",
                        "publication_state": "not_published",
                    }
                )
        except Exception as exc:  # noqa: BLE001
            result.update(
                {
                    "decision": "rejected_or_deferred_at_live_review",
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:1000],
                }
            )
        results.append(result)
    counts = Counter(item["decision"] for item in results)
    live = {
        "status": "completed",
        "attempted_count": len(results),
        "verified_count": counts["verified_live_unapproved"],
        "decision_counts": dict(sorted(counts.items())),
        "results": results,
    }
    body = {
        key: value
        for key, value in checked.items()
        if key not in {"review_sha256", "assertions", "live_review"}
    }
    assertions = dict(checked["assertions"])
    assertions.update(
        {
            "entire_static_shortlist_received_a_live_disposition": len(results)
            == len(checked["live_shortlist"]),
            "live_review_never_approved_or_published_a_candidate": all(
                item.get("approval_state") in {None, "unapproved_verified_draft"}
                and item.get("publication_state") in {None, "not_published"}
                for item in results
            ),
            "verified_candidates_have_three_case_hash_bound_evidence": all(
                item.get("verification_case_count") == 3
                and _SHA256_RE.fullmatch(item.get("verification_sha256", ""))
                and item.get("premature_publication_blocked") is True
                for item in results
                if item["decision"] == "verified_live_unapproved"
            ),
        }
    )
    body.update({"live_review": live, "assertions": assertions})
    if not all(assertions.values()):
        failed = sorted(key for key, result in assertions.items() if not result)
        raise AssertionError(
            f"Candidate portfolio live-review assertions failed: {failed!r}"
        )
    return {**body, "review_sha256": _digest(body)}


def validate_review(
    value: Any, *, require_contract: bool = True, require_live: bool = True
) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or value.get("format") != "vsd_candidate_portfolio_review_study_v1"
        or value.get("version") != 1
    ):
        raise ValueError("Candidate portfolio review artifact is invalid")
    body = {key: item for key, item in value.items() if key != "review_sha256"}
    if value.get("review_sha256") != _digest(body):
        raise ValueError("Candidate portfolio review digest does not match")
    assertions = value.get("assertions")
    if not isinstance(assertions, dict) or not all(
        result is True for result in assertions.values()
    ):
        raise ValueError("Candidate portfolio review assertions did not pass")
    reviews = value.get("candidate_reviews")
    summary = value.get("summary")
    source_evidence = value.get("source_evidence")
    expected_candidate_count = (
        source_evidence.get("expected_draft_ready_candidate_count")
        if isinstance(source_evidence, dict)
        else None
    )
    if (
        not isinstance(reviews, list)
        or not isinstance(expected_candidate_count, int)
        or expected_candidate_count <= 0
        or len(reviews) != expected_candidate_count
        or not isinstance(summary, dict)
        or summary.get("reviewed_candidate_count") != len(reviews)
        or len({item.get("preview_config_sha256") for item in reviews}) != len(reviews)
    ):
        raise ValueError("Candidate portfolio review inventory is invalid")
    live = value.get("live_review")
    contract = value.get("contract_review")
    if not isinstance(contract, dict) or (
        require_contract and contract.get("status") != "completed"
    ):
        raise ValueError("Candidate portfolio contract review is incomplete")
    if not isinstance(live, dict) or (
        require_live and live.get("status") != "completed"
    ):
        raise ValueError("Candidate portfolio live review is incomplete")
    return json.loads(json.dumps(value))


def render_markdown(value: Any) -> str:
    review = validate_review(value)
    summary = review["summary"]
    lines = [
        "# VSD Candidate Portfolio Review",
        "",
        "## Scope",
        "",
        review["objective"],
        "",
        review["review_boundary"],
        "",
        "## Review Funnel",
        "",
        "| Stage | Count |",
        "| --- | ---: |",
        f"| Exhaustive operation candidates | {review['source_evidence']['exhaustive_operation_candidate_count']:,} |",
        f"| Mechanically draft-ready configurations | {summary['reviewed_candidate_count']:,} |",
        f"| Unique endpoint identities | {summary['unique_endpoint_identity_count']:,} |",
        f"| Initially eligible after metadata review | {summary['initial_statically_eligible_count']:,} |",
        f"| Draft-producing contracts refreshed | {review['contract_review']['refreshed_record_count']:,} / {review['contract_review']['record_count']:,} |",
        f"| Eligible after current-contract review | {summary['review_eligible_count']:,} |",
        f"| Eligible research-facing scientific candidates | {summary['scientific_review_eligible_count']:,} |",
        f"| Lower-value service utility candidates | {summary['service_utility_eligible_count']:,} |",
        f"| Held or superseded after portfolio review | {summary['held_or_superseded_count']:,} |",
        f"| Bounded live-review shortlist | {review['live_review']['attempted_count']:,} |",
        f"| Passed live verification and remained unapproved | {review['live_review']['verified_count']:,} |",
        "",
        "## Final Contract-Aware Dispositions",
        "",
        "| Decision | Candidates |",
        "| --- | ---: |",
    ]
    for decision, count in summary["decision_counts"].items():
        lines.append(f"| `{decision}` | {count:,} |")
    lines.extend(
        [
            "",
            "## Principal Review Signals",
            "",
            "| Signal | Candidates |",
            "| --- | ---: |",
        ]
    )
    for reason, count in list(summary["reason_counts"].items())[:20]:
        lines.append(f"| `{reason}` | {count:,} |")
    lines.extend(
        [
            "",
            "## Scientific Capability Families",
            "",
            "| Provider | Candidate operations | No-input | Parameterized | Examples |",
            "| --- | ---: | ---: | ---: | --- |",
        ]
    )
    for family in summary["eligible_scientific_families"]:
        examples = ", ".join(f"`{item}`" for item in family["sample_operations"][:4])
        lines.append(
            f"| {', '.join(family['api_titles'])} (`{family['host']}`) | "
            f"{family['candidate_count']:,} | {family['no_input_count']:,} | "
            f"{family['parameterized_count']:,} | {examples} |"
        )
    lines.extend(
        [
            "",
            "## Live Review",
            "",
            "The live phase selected at most one no-input scientific operation per "
            "host before considering another operation from the same host. Each "
            "candidate was rebound to the current catalog contract, checked for drift, "
            "and either deferred or executed three times through the normal isolated "
            "VSD verifier. No candidate was approved or published.",
            "",
            "| Outcome | Candidates |",
            "| --- | ---: |",
        ]
    )
    for decision, count in review["live_review"].get("decision_counts", {}).items():
        lines.append(f"| `{decision}` | {count:,} |")
    lines.extend(
        [
            "",
            "### Live Results",
            "",
            "| API | Operation | Host | Outcome | Evidence |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    by_hash = {item["preview_config_sha256"]: item for item in review["live_shortlist"]}
    for result in review["live_review"]["results"]:
        selected = by_hash[result["preview_config_sha256"]]
        evidence = (
            f"{result['verification_case_count']} hash-bound calls passed"
            if result["decision"] == "verified_live_unapproved"
            else result.get("error", "deferred")[:180]
            .replace("\r", " ")
            .replace("\n", " ")
            .replace("|", "\\|")
        )
        lines.append(
            f"| {selected['api_title']} | `{result['operation_id']}` | "
            f"`{result['host']}` | `{result['decision']}` | {evidence} |"
        )
    lines.extend(
        [
            "",
            "## Measured Contribution",
            "",
            "The gross count measures discovery breadth, while the reviewed and live "
            "counts measure usable growth potential. Every draft-producing contract was "
            f"refetched and all {summary['reviewed_candidate_count']:,} configuration "
            "hashes were matched to the current "
            "documents. VSD contributes a repeatable path from a missing capability to "
            "an inspectable candidate, then removes duplicates, stale sources, suspected "
            "access-control gaps, weak response contracts, and low-value utility "
            "operations before execution. The checked cancer qualification independently "
            "shows the later stages: four scanner-derived operations passed verification, "
            "approval, publication, fresh ToolUniverse loading, and twenty workflow "
            "calls, while four plausible candidates failed closed on live schema drift.",
            "",
            "The review does not establish provider endorsement or scientific truth. "
            "Candidates marked eligible still require a concrete demand, provider "
            "governance review, representative inputs when applicable, live verification, "
            "explicit approval, and lifecycle monitoring.",
            "",
            "The machine-readable ledger contains the decision and evidence for every "
            "candidate plus the refresh result for every draft-producing contract.",
            "",
            f"Review SHA-256: `{review['review_sha256']}`.",
            "",
        ]
    )
    return "\n".join(lines)


def write_artifacts(review: Any) -> tuple[Path, Path]:
    checked = validate_review(review)
    JSON_ARTIFACT.write_text(
        json.dumps(checked, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    MARKDOWN_ARTIFACT.write_text(render_markdown(checked), encoding="utf-8")
    return JSON_ARTIFACT, MARKDOWN_ARTIFACT


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--state-root",
        type=Path,
        help="Parent directory containing the APIs.guru and SmartAPI scan histories",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate the checked artifacts without network access",
    )
    parser.add_argument(
        "--static-only",
        action="store_true",
        help="Build the complete static ledger without provider-operation calls",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.validate_only:
        checked = validate_review(_read_json(JSON_ARTIFACT, maximum=12_000_000))
        if MARKDOWN_ARTIFACT.read_text(encoding="utf-8") != render_markdown(checked):
            raise ValueError("Candidate portfolio Markdown is out of sync")
        print(json.dumps({"review_sha256": checked["review_sha256"]}, sort_keys=True))
        return 0
    if args.state_root is None:
        raise ValueError("--state-root is required when generating the review")
    cycles = load_catalog_cycles(args.state_root)
    static = build_static_review(
        cycles,
        _read_json(EXPANSION_PATH, maximum=2_000_000),
        _read_json(QUALIFICATION_PATH, maximum=5_000_000),
        _read_json(POLICY_PATH, maximum=64_000),
    )
    if args.static_only:
        print(
            json.dumps(
                {
                    "review_sha256": static["review_sha256"],
                    "summary": static["summary"],
                    "live_shortlist": static["live_shortlist"],
                },
                sort_keys=True,
            )
        )
        return 0
    contract_reviewed = run_contract_review(static)
    review = run_live_review(contract_reviewed)
    json_path, markdown_path = write_artifacts(review)
    print(
        json.dumps(
            {
                "json": str(json_path),
                "markdown": str(markdown_path),
                "review_sha256": review["review_sha256"],
                "summary": review["summary"],
                "live_review": {
                    key: review["live_review"][key]
                    for key in ("attempted_count", "verified_count", "decision_counts")
                },
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
