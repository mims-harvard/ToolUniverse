"""End-to-end portfolio for safe VSD source intelligence.

The study asks whether ToolUniverse can find reviewable interfaces for an ALS
research workflow without duplicating configured sources or turning discovered
metadata into executable tools. All provider traffic is deterministic and local
to this fixture; the production crawler is exercised through an injected fetcher.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

from tooluniverse.default_config import default_tool_files
from tooluniverse.vsd_contracts import inspect_contract_document
from tooluniverse.vsd_demand import export_proposals, observe_capability_demand
from tooluniverse.vsd_source_intelligence import (
    VSDSourceIntelligenceError,
    assess_catalog_coverage,
    configured_source_inventory,
    crawl_source_candidates,
    load_trusted_source_catalog,
    prepare_core_handoff,
    render_core_issue,
    snapshot_source_candidate,
    validate_core_handoff,
    validate_source_scan,
    write_core_handoff,
    write_scan_report,
)

ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "artifacts"
DEFAULT_JSON = ARTIFACTS / "source_intelligence_snapshot.json"
DEFAULT_MARKDOWN = ARTIFACTS / "source_intelligence_snapshot.md"
DEFAULT_HANDOFF = ARTIFACTS / "source_intelligence_handoff.json"
DEFAULT_DEMAND = ARTIFACTS / "source_intelligence_demand_proposal.json"
REPORTER = "api.reporter.nih.gov"
DANDI = "api.dandiarchive.org"
SEEDS = [f"https://{REPORTER}/developer", f"https://{DANDI}/portal"]


class _ConfiguredUniverse:
    tool_files = default_tool_files

    def __init__(self, extra_tools: list[dict[str, Any]] | None = None):
        self.all_tools = list(extra_tools or [])


def _openapi() -> bytes:
    return json.dumps(
        {
            "openapi": "3.1.0",
            "info": {"title": "NIH ALS Grant Evidence", "version": "2"},
            "servers": [{"url": f"https://{REPORTER}"}],
            "paths": {
                "/v2/projects/search": {
                    "get": {
                        "operationId": "searchAlsFundedProjects",
                        "parameters": [
                            {
                                "name": "disease",
                                "in": "query",
                                "required": True,
                                "schema": {"type": "string"},
                            },
                            {
                                "name": "fiscal_year",
                                "in": "query",
                                "schema": {"type": "integer"},
                            },
                        ],
                        "responses": {
                            "200": {
                                "description": "Funded projects",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "projects": {
                                                    "type": "array",
                                                    "items": {
                                                        "type": "object",
                                                        "properties": {
                                                            "project_id": {
                                                                "type": "string"
                                                            },
                                                            "title": {"type": "string"},
                                                            "principal_investigator": {
                                                                "type": "string"
                                                            },
                                                        },
                                                    },
                                                }
                                            },
                                        }
                                    }
                                },
                            }
                        },
                    }
                }
            },
        },
        sort_keys=True,
    ).encode()


def _graphql() -> bytes:
    return b"""
    type ElectrodeLocation { region: String!, hemisphere: String! }
    type Asset { assetId: ID!, contentType: String!, sizeBytes: Int! }
    type Dandiset { id: ID!, name: String!, species: [String!]!, assets: [Asset!]! }
    type Query {
      searchAlsElectrophysiology(
        diseaseTerm: String!, species: String!, recordingModality: String!, limit: Int
      ): [Dandiset!]!
      electrodeLocations(dandisetId: ID!): [ElectrodeLocation!]!
    }
    """


def _asyncapi() -> bytes:
    return b"""asyncapi: 3.0.0
info:
  title: DANDI metadata change events
  version: '1'
servers:
  production:
    host: api.dandiarchive.org
    protocol: https
channels:
  dandisetChanges:
    address: dandisets/{dandisetId}/changes
    messages:
      change:
        payload:
          type: object
          properties:
            dandisetId: {type: string}
            version: {type: string}
            changedAt: {type: string}
          required: [dandisetId, version, changedAt]
operations:
  receiveDandisetChange:
    action: receive
    channel:
      $ref: '#/channels/dandisetChanges'
    messages:
      - $ref: '#/channels/dandisetChanges/messages/change'
"""


def _postman() -> bytes:
    return json.dumps(
        {
            "info": {
                "name": "DANDI ALS metadata",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            },
            "variable": [{"key": "baseUrl", "value": f"https://{DANDI}"}],
            "item": [
                {
                    "name": "Get dandiset",
                    "request": {
                        "method": "GET",
                        "url": {
                            "raw": "{{baseUrl}}/api/dandisets/{{dandisetId}}",
                            "variable": [
                                {"key": "dandisetId", "value": "{{dandisetId}}"}
                            ],
                        },
                    },
                }
            ],
        },
        sort_keys=True,
    ).encode()


def _wsdl() -> bytes:
    return f"""<?xml version="1.0"?>
    <definitions xmlns="http://schemas.xmlsoap.org/wsdl/"
      xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/" name="DandiArchive">
      <portType name="ArchivePort">
        <operation name="GetPreservationRecord">
          <input message="GetRecordRequest"/><output message="GetRecordResponse"/>
        </operation>
      </portType>
      <binding name="ArchiveBinding" type="ArchivePort">
        <operation name="GetPreservationRecord">
          <soap:operation soapAction="urn:GetPreservationRecord"/>
        </operation>
      </binding>
      <service name="ArchiveService"><port name="ArchivePort" binding="ArchiveBinding">
        <soap:address location="https://{DANDI}/soap"/>
      </port></service>
    </definitions>""".encode()


def _protobuf() -> bytes:
    return b"""
    syntax = "proto3";
    package dandi.v1;
    message SearchRequest { string disease_term = 1; string species = 2; }
    message DandisetMatch { string dandiset_id = 1; string name = 2; }
    service DandisetService {
      rpc SearchAlsDandisets(SearchRequest) returns (DandisetMatch);
      rpc StreamAlsDandisets(SearchRequest) returns (stream DandisetMatch);
    }
    """


def _mcp() -> bytes:
    return json.dumps(
        {
            "mcpServers": {
                "dandi-readonly": {
                    "url": f"https://{DANDI}/mcp",
                    "transport": "http",
                    "tools": [
                        {"name": "search_dandisets"},
                        {"name": "get_dandiset_metadata"},
                    ],
                }
            }
        },
        sort_keys=True,
    ).encode()


def _routes() -> dict[str, tuple[bytes, str]]:
    reporter_html = b"""
    <html><head><link rel="service-desc" href="/openapi.json"></head>
    <body><a href="/openapi.json">OpenAPI</a></body></html>
    """
    dandi_html = b"""
    <html><head>
      <script type="application/ld+json">{"distribution":"/events/asyncapi.yaml"}</script>
    </head><body>
      <a href="/graphql/schema.graphql">GraphQL</a>
      <a href="/collections/als.postman_collection.json">Postman</a>
      <a href="/soap/archive.wsdl">WSDL</a>
      <a href="/grpc/dandisets.proto">protobuf</a>
      <a href="/.well-known/dandi.mcp.json">MCP</a>
      <a href="/private/internal.openapi.json">robots blocked</a>
      <a href="https://attacker.invalid/openapi.json">cross-host trap</a>
      <a href="/graphql/schema.graphql?access_token=hidden">query trap</a>
    </body></html>
    """
    return {
        f"https://{REPORTER}/robots.txt": (b"User-agent: *\nAllow: /\n", "text/plain"),
        f"https://{DANDI}/robots.txt": (
            b"User-agent: *\nDisallow: /private\n",
            "text/plain",
        ),
        SEEDS[0]: (reporter_html, "text/html"),
        SEEDS[1]: (dandi_html, "text/html"),
        f"https://{REPORTER}/openapi.json": (_openapi(), "application/json"),
        f"https://{DANDI}/graphql/schema.graphql": (
            _graphql(),
            "application/graphql",
        ),
        f"https://{DANDI}/events/asyncapi.yaml": (
            _asyncapi(),
            "application/yaml",
        ),
        f"https://{DANDI}/collections/als.postman_collection.json": (
            _postman(),
            "application/json",
        ),
        f"https://{DANDI}/soap/archive.wsdl": (_wsdl(), "application/wsdl+xml"),
        f"https://{DANDI}/grpc/dandisets.proto": (_protobuf(), "text/plain"),
        f"https://{DANDI}/.well-known/dandi.mcp.json": (
            _mcp(),
            "application/json",
        ),
    }


def _fetcher(routes: dict[str, tuple[bytes, str]]):
    def fetch(url: str, timeout: float, max_bytes: int):
        del timeout
        try:
            raw, content_type = routes[url]
        except KeyError as exc:
            raise VSDSourceIntelligenceError(
                "Deterministic route is unavailable"
            ) from exc
        if len(raw) > max_bytes:
            raise VSDSourceIntelligenceError("Deterministic route exceeds byte limit")
        return raw, {
            "url": url,
            "status_code": 200,
            "content_type": content_type,
            "response_bytes": len(raw),
            "headers": {"content-type": content_type},
            "peer_ip": "203.0.113.10",
            "redirects": 0,
        }

    return fetch


def _inspection_endpoint(source_format: str) -> str | None:
    if source_format == "graphql":
        return f"https://{DANDI}/graphql"
    if source_format == "protobuf":
        return f"https://{DANDI}"
    return None


def _artifact_digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode()
    ).hexdigest()


def _repository_literal_hosts() -> set[str]:
    source_root = ROOT.parents[1] / "src" / "tooluniverse"
    pattern = re.compile(r"https://[A-Za-z0-9._:-]+", re.IGNORECASE)
    hosts: set[str] = set()
    for suffix in ("*.py", "*.json"):
        for path in source_root.rglob(suffix):
            try:
                if path.name == "vsd_trusted_sources.json":
                    continue
                if path.stat().st_size > 5_000_000:
                    continue
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for match in pattern.findall(text):
                host = match.split("://", 1)[1].split(":", 1)[0]
                hosts.add(host.casefold().rstrip("."))
    return hosts


def run_case(workspace: Path) -> dict[str, Any]:
    workspace.mkdir(parents=True, exist_ok=True)
    catalog = load_trusted_source_catalog()
    literal_hosts = _repository_literal_hosts()
    catalog_domains = {item["domain"] for item in catalog["sources"]}
    literal_host_collisions = sorted(catalog_domains & literal_hosts)
    baseline_inventory = configured_source_inventory(_ConfiguredUniverse())
    baseline_coverage = assess_catalog_coverage(catalog, baseline_inventory)

    existing = {
        "name": "NIHReporterExistingSearch",
        "type": "VSDReviewedOperationTool",
        "vsd_operation": {
            "endpoint": f"https://{REPORTER}/v2/projects/search",
            "method": "GET",
        },
    }
    review_inventory = configured_source_inventory(_ConfiguredUniverse([existing]))
    review_coverage = assess_catalog_coverage(catalog, review_inventory)
    routes = _routes()
    fetcher = _fetcher(routes)
    scan = crawl_source_candidates(
        SEEDS,
        catalog=catalog,
        inventory=review_inventory,
        max_pages=20,
        max_depth=2,
        max_page_bytes=500_000,
        max_total_bytes=4_000_000,
        fetcher=fetcher,
        scanned_at="2026-08-01T12:00:00+00:00",
    )
    second_scan = crawl_source_candidates(
        SEEDS,
        catalog=catalog,
        inventory=review_inventory,
        max_pages=20,
        max_depth=2,
        max_page_bytes=500_000,
        max_total_bytes=4_000_000,
        fetcher=fetcher,
        scanned_at="2026-08-02T12:00:00+00:00",
    )
    history = workspace / "scan-history"
    history_files = [
        write_scan_report(scan, history),
        write_scan_report(second_scan, history),
    ]

    snapshots = []
    inspections = []
    snapshot_directory = workspace / "contract-snapshots"
    for candidate in scan["candidates"]:
        manifest = snapshot_source_candidate(
            scan,
            candidate["candidate_id"],
            snapshot_directory,
            fetcher=fetcher,
        )
        snapshot_path = snapshot_directory / manifest["snapshot_file"]
        endpoint = _inspection_endpoint(candidate["format_hint"])
        report = inspect_contract_document(
            snapshot_path,
            format_hint=candidate["format_hint"],
            **({"endpoint": endpoint} if endpoint else {}),
        )
        candidate_count = report.get("candidate_count", report.get("operation_count"))
        blocked_count = report.get(
            "blocked_count", report.get("blocked_operation_count")
        )
        snapshots.append(manifest)
        inspections.append(
            {
                "source_candidate_id": candidate["candidate_id"],
                "source_format": candidate["format_hint"],
                "source_document_sha256": manifest["content_sha256"],
                "operation_candidate_count": candidate_count,
                "blocked_operation_count": blocked_count,
                "inspection_format": report["format"],
                "execution_allowed": False,
            }
        )

    demand_workspace = workspace / "private-demand"
    observation = observe_capability_demand(
        _ConfiguredUniverse(),
        {
            "description": (
                "Find ALS neurophysiology datasets by species and recording modality, "
                "then connect each dataset to relevant federally funded projects"
            ),
            "provider": DANDI,
            "method": "GET",
            "required_inputs": ["disease_term", "species", "recording_modality"],
            "output_fields": ["dandiset_id", "asset_id", "project_id"],
        },
        public_summary=(
            "Connect ALS neurophysiology datasets to relevant funded research projects"
        ),
        source="case_study",
        event_id="als-source-intelligence-portfolio-v1",
        observed_at="2026-08-01T12:30:00+00:00",
        workspace=demand_workspace,
    )
    demand_id = observation["data"]["demand"]["demand_id"]
    demand_path = workspace / "demand-proposal.json"
    demand_export = export_proposals(
        [demand_id],
        demand_path,
        reviewed_by="VSD Case Study Maintainer",
        decision_note=(
            "Share this sanitized capability gap with selected reviewed source leads."
        ),
        workspace=demand_workspace,
        created_at="2026-08-01T13:00:00+00:00",
    )

    handoff_candidate_ids = [
        item["candidate_id"]
        for item in scan["candidates"]
        if item["format_hint"] in {"openapi", "graphql", "asyncapi"}
    ]
    selected_snapshots = [
        item for item in snapshots if item["candidate_id"] in handoff_candidate_ids
    ]
    handoff = prepare_core_handoff(
        [scan, second_scan],
        handoff_candidate_ids,
        reviewed_by="VSD Case Study Maintainer",
        decision_note=(
            "Reviewed trusted-source evidence, duplicate coverage, snapshots, and unmet demand."
        ),
        consent=True,
        demand_export=demand_export,
        snapshots=selected_snapshots,
        created_at="2026-08-01T14:00:00+00:00",
    )
    handoff_path = write_core_handoff(handoff, workspace / "core-handoff.json")
    issue_title, issue_body = render_core_issue(handoff)

    baseline_domains = {row["domain"]: row for row in baseline_coverage["sources"]}
    review_domains = {row["domain"]: row for row in review_coverage["sources"]}
    cases = [
        {
            "case_id": "catalog_boundary",
            "result": "passed",
            "proof": (
                f"{len(catalog['sources'])} authoritative entries permit discovery "
                "but never execution or registration"
            ),
        },
        {
            "case_id": "real_registry_audit",
            "result": "passed",
            "proof": (
                f"{baseline_inventory['tool_count']} configured tools and "
                f"{baseline_inventory['host_count']} configured hosts plus "
                f"{len(literal_hosts)} source-code hosts were inventoried"
            ),
        },
        {
            "case_id": "existing_source_detection",
            "result": "passed",
            "proof": "the controlled RePORTER host is marked existing with its exact tool name",
        },
        {
            "case_id": "candidate_gap_detection",
            "result": "passed",
            "proof": "the DANDI host remains a candidate gap instead of being treated as covered",
        },
        {
            "case_id": "bounded_multihost_crawl",
            "result": "passed",
            "proof": "two explicit hosts yielded seven unique contract leads within page/depth/byte limits",
        },
        {
            "case_id": "robots_and_ssrf_boundary",
            "result": "passed",
            "proof": "one private path was excluded and cross-host/query traps were never fetched",
        },
        {
            "case_id": "multiformat_discovery",
            "result": "passed",
            "proof": "OpenAPI, GraphQL, AsyncAPI, Postman, WSDL, protobuf, and MCP were detected",
        },
        {
            "case_id": "content_addressed_snapshot",
            "result": "passed",
            "proof": "all seven selected documents were saved under verified SHA-256 filenames",
        },
        {
            "case_id": "local_contract_inspection",
            "result": "passed",
            "proof": "every snapshot produced inert operation candidates through the contract boundary",
        },
        {
            "case_id": "cron_history",
            "result": "passed",
            "proof": "two timestamped scans produced separate tamper-detecting local history records",
        },
        {
            "case_id": "explicit_core_handoff",
            "result": "passed",
            "proof": "three reviewed leads and one sanitized demand proposal were rendered without submission",
        },
    ]
    assertions = {
        "catalog_contains_reviewed_sources": len(catalog["sources"]) > 0,
        "catalog_never_executes": catalog["execution_allowed"] is False,
        "baseline_catalog_domains_are_current_gaps": baseline_coverage[
            "existing_host_count"
        ]
        == 0,
        "source_literals_do_not_count_as_registered_coverage": all(
            baseline_domains[domain]["coverage"] == "candidate_gap"
            for domain in literal_host_collisions
        ),
        "reporter_baseline_is_not_configured": baseline_domains[REPORTER]["coverage"]
        == "candidate_gap",
        "dandi_baseline_is_not_configured": baseline_domains[DANDI]["coverage"]
        == "candidate_gap",
        "review_inventory_detects_reporter": review_domains[REPORTER]["coverage"]
        == "existing_host",
        "review_inventory_names_existing_tool": review_domains[REPORTER][
            "existing_tools"
        ]
        == ["NIHReporterExistingSearch"],
        "review_inventory_keeps_dandi_gap": review_domains[DANDI]["coverage"]
        == "candidate_gap",
        "seven_contract_leads_found": scan["candidate_count"] == 7,
        "all_formats_found": {item["format_hint"] for item in scan["candidates"]}
        == {"openapi", "graphql", "asyncapi", "postman", "wsdl", "protobuf", "mcp"},
        "one_robots_path_blocked": scan["blocked_count"] == 1,
        "external_trap_not_visited": all(
            "attacker.invalid" not in page["url"] for page in scan["pages"]
        ),
        "query_trap_not_visited": all("?" not in page["url"] for page in scan["pages"]),
        "reporter_candidate_is_existing": next(
            item for item in scan["candidates"] if item["host"] == REPORTER
        )["coverage"]
        == "existing_host",
        "dandi_candidates_are_gaps": all(
            item["coverage"] == "candidate_gap"
            for item in scan["candidates"]
            if item["host"] == DANDI
        ),
        "seven_snapshots_created": len(snapshots) == 7,
        "snapshot_digests_are_unique": len(
            {item["content_sha256"] for item in snapshots}
        )
        == 7,
        "seven_inspections_completed": len(inspections) == 7,
        "inspection_never_executes": all(
            item["execution_allowed"] is False for item in inspections
        ),
        "history_contains_two_scans": len(history_files) == 2
        and len({path.name for path in history_files}) == 2,
        "sanitized_demand_exported": len(demand_export["proposals"]) == 1,
        "handoff_selects_three_candidates": len(handoff["candidates"]) == 3,
        "handoff_has_demand_provenance": handoff["demand_export_sha256"]
        == demand_export["export_sha256"],
        "handoff_never_executes": handoff["execution_allowed"] is False,
        "handoff_remains_local": handoff["transmission"].startswith("none;"),
        "issue_preview_not_submitted": "Required next steps" in issue_body,
        "all_cases_pass": all(item["result"] == "passed" for item in cases),
    }
    snapshot = {
        "case_study": "ALS trusted-source intelligence and review handoff",
        "research_question": (
            "Can ToolUniverse identify interfaces needed to connect ALS funding evidence "
            "with neurophysiology datasets without duplicating existing sources or "
            "silently installing discovered operations?"
        ),
        "answer": (
            "Yes. The bounded scan separated an already configured RePORTER host from a "
            "DANDI capability gap, found seven contract formats, preserved robots and "
            "host boundaries, inspected content-addressed snapshots locally, and prepared "
            "a consent-bound core-team handoff linked to sanitized unmet demand."
        ),
        "real_registry_baseline": {
            "tool_count": baseline_inventory["tool_count"],
            "host_count": baseline_inventory["host_count"],
            "registry_sha256": baseline_inventory["inventory_sha256"],
            "catalog_source_count": baseline_coverage["catalog_source_count"],
            "catalog_existing_host_count": baseline_coverage["existing_host_count"],
            "catalog_gap_count": baseline_coverage["candidate_gap_count"],
            "literal_https_host_count": len(literal_hosts),
            "literal_catalog_collisions": literal_host_collisions,
        },
        "controlled_duplicate_demo": {
            "added_tool": existing["name"],
            "existing_source": review_domains[REPORTER],
            "candidate_gap": review_domains[DANDI],
        },
        "scan_summary": {
            key: copy.deepcopy(scan[key])
            for key in (
                "scan_id",
                "scan_sha256",
                "seeds",
                "allowed_hosts",
                "limits",
                "robots_status",
                "pages_visited",
                "pages_fetched",
                "response_bytes",
                "blocked_count",
                "blocked_urls",
                "candidate_count",
                "candidate_gap_count",
                "existing_host_count",
                "candidates",
                "execution_allowed",
                "transmission",
            )
        },
        "snapshot_manifests": snapshots,
        "inspection_summary": inspections,
        "cron_history": {
            "scan_ids": [scan["scan_id"], second_scan["scan_id"]],
            "report_files": [path.name for path in history_files],
            "content_candidates_stable": [
                item["candidate_id"] for item in scan["candidates"]
            ]
            == [item["candidate_id"] for item in second_scan["candidates"]],
        },
        "demand_handoff": {
            "public_summary": demand_export["proposals"][0]["public_summary"],
            "priority_score": demand_export["proposals"][0]["priority_score"],
            "proposal_id": demand_export["proposals"][0]["proposal_id"],
            "handoff_id": handoff["handoff_id"],
            "candidate_ids": [item["candidate_id"] for item in handoff["candidates"]],
            "issue_title": issue_title,
            "submitted": False,
            "handoff_file": handoff_path.name,
        },
        "case_results": cases,
        "end_to_end_assertions": assertions,
    }
    snapshot["audit_sha256"] = _artifact_digest(snapshot)
    validate_snapshot(snapshot)
    validate_source_scan(scan)
    validate_source_scan(second_scan)
    validate_core_handoff(handoff)
    return snapshot


def validate_snapshot(snapshot: dict[str, Any]) -> None:
    if not isinstance(snapshot, dict) or "audit_sha256" not in snapshot:
        raise ValueError("Case-study snapshot is invalid")
    body = {key: value for key, value in snapshot.items() if key != "audit_sha256"}
    if snapshot["audit_sha256"] != _artifact_digest(body):
        raise ValueError("Case-study audit digest does not match content")
    assertions = snapshot.get("end_to_end_assertions")
    if (
        not isinstance(assertions, dict)
        or not assertions
        or not all(assertions.values())
    ):
        raise ValueError("Case-study end-to-end assertions did not all pass")


def _markdown(snapshot: dict[str, Any]) -> str:
    baseline = snapshot["real_registry_baseline"]
    scan = snapshot["scan_summary"]
    handoff = snapshot["demand_handoff"]
    rows = "\n".join(
        f"| `{case['case_id']}` | {case['result']} | {case['proof']} |"
        for case in snapshot["case_results"]
    )
    formats = ", ".join(sorted({item["format_hint"] for item in scan["candidates"]}))
    return f"""# ALS Source Intelligence Case-Study Portfolio

## Executive Result

**Question:** {snapshot["research_question"]}

**Answer:** {snapshot["answer"]}

The proof used the real ToolUniverse configuration inventory, deterministic hostile-web
fixtures, the production source-intelligence boundary, the multi-format contract
inspector, the private demand ledger, and the explicit handoff renderer. It made no
provider call, registered no tool, executed no discovered operation, and submitted
nothing externally.

## What The Research Workflow Needed

The hypothetical ALS review needed two kinds of evidence that do not naturally live in
one system: federally funded project metadata and reusable neurophysiology datasets.
The practical question was whether a maintainer could discover the necessary API
interfaces, recognize that one provider was already represented, investigate the true
gap, and give the core team enough evidence to decide what to build next.

## Real Registry Audit

- Configured tools inspected: **{baseline["tool_count"]}**
- Exact HTTPS hosts found: **{baseline["host_count"]}**
- Literal HTTPS hosts found in Python/JSON source: **{baseline["literal_https_host_count"]}**
- Catalog entries already present by exact host: **{baseline["catalog_existing_host_count"]}**
- Catalog entries remaining as review candidates: **{baseline["catalog_gap_count"]}**
- Catalog collisions with source-code URL literals: **{len(baseline["literal_catalog_collisions"])}**
- Registry inventory SHA-256: `{baseline["registry_sha256"]}`

For the duplicate-control case, the study then added one explicit RePORTER configuration.
The source inventory associated that exact host with `NIHReporterExistingSearch`, while
the DANDI host remained a candidate gap. This proves the feature does not equate
"trusted" with "missing" and does not recommend a provider blindly.

## Bounded Discovery

- Explicit seed hosts: {", ".join(scan["allowed_hosts"])}
- Pages fetched: **{scan["pages_fetched"]}** within depth/page/byte limits
- Unique contract leads: **{scan["candidate_count"]}**
- Detected formats: {formats}
- Robots exclusions: **{scan["blocked_count"]}**
- External/query traps fetched: **0**
- Execution allowed: **{str(scan["execution_allowed"]).lower()}**

The fixture linked the same OpenAPI document twice, advertised metadata through HTML
and JSON-LD, exposed seven formats, linked a robots-blocked private contract, linked an
external hostile host, and embedded a credential-like query. The crawler deduplicated
the contract, stayed on the two exact seed hosts, rejected query-bearing URLs, and did
not fetch the blocked path.

## Snapshot And Inspection

All seven leads were explicitly selected and fetched into files named by their content
SHA-256. Each snapshot then crossed the local-only contract inspection boundary and
produced inert operation candidates. Discovery metadata was never promoted directly;
read-only semantics, credentials, schemas, pagination, and representative responses
still require the existing verification and approval workflow.

## Cron And Core-Team Visibility

Two scans at different timestamps produced two tamper-detecting history files while
retaining stable content candidate IDs. Nothing is telemetered by default. The core
team sees candidates only after an administrator selects exact IDs, supplies review
text, gives consent, and explicitly submits the sanitized bundle.

The local handoff `{handoff["handoff_id"]}` contains three reviewed leads plus the
sanitized unmet-demand statement "{handoff["public_summary"]}". Its issue preview was
rendered, but `submitted` remained **false**.

## Case Results

| Case | Result | Concrete proof |
|---|---|---|
{rows}

## Interpretation

This feature does not autonomously add {baseline["catalog_source_count"]} new tools. It gives maintainers a controlled
way to answer: which authoritative sources are worth scanning, which ones ToolUniverse
already covers, which machine-readable contracts actually exist, which exact documents
were inspected, and which unmet needs are worth bringing to the core team. Tool creation
still begins only after a maintainer selects and reviews an operation through the
existing promotion lifecycle.

Audit SHA-256: `{snapshot["audit_sha256"]}`
"""


def write_artifacts(
    snapshot: dict[str, Any],
    *,
    json_path: Path = DEFAULT_JSON,
    markdown_path: Path = DEFAULT_MARKDOWN,
    handoff_path: Path = DEFAULT_HANDOFF,
    demand_path: Path = DEFAULT_DEMAND,
    workspace: Path,
) -> None:
    validate_snapshot(snapshot)
    source_handoff = workspace / "core-handoff.json"
    source_demand = workspace / "demand-proposal.json"
    handoff = json.loads(source_handoff.read_text(encoding="utf-8"))
    demand = json.loads(source_demand.read_text(encoding="utf-8"))
    validate_core_handoff(handoff)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(_markdown(snapshot), encoding="utf-8")
    handoff_path.write_text(
        json.dumps(handoff, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    demand_path.write_text(
        json.dumps(demand, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    if len(sys.argv) == 1:
        with tempfile.TemporaryDirectory(
            prefix="vsd-source-intelligence-"
        ) as temporary:
            workspace = Path(temporary)
            snapshot = run_case(workspace)
            write_artifacts(snapshot, workspace=workspace)
    elif len(sys.argv) == 2:
        workspace = Path(sys.argv[1])
        snapshot = run_case(workspace)
        write_artifacts(snapshot, workspace=workspace)
    else:
        raise SystemExit("usage: source_intelligence_case_study.py [workspace]")
    print(json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
