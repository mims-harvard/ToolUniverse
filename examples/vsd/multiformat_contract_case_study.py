"""Deterministic multi-format VSD contract inspection portfolio."""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

import yaml

from tooluniverse.vsd_contracts import (
    inspect_contract_document,
    validate_contract_candidate,
)

ARTIFACT_DIR = Path(__file__).with_name("artifacts")
JSON_ARTIFACT = ARTIFACT_DIR / "multiformat_contract_snapshot.json"
MARKDOWN_ARTIFACT = ARTIFACT_DIR / "multiformat_contract_snapshot.md"


def _documents() -> list[dict[str, Any]]:
    return [
        {
            "case": "Rare-disease registry GraphQL",
            "question": "Which genes and trials are linked to spinal muscular atrophy?",
            "name": "registry.graphql",
            "endpoint": "https://rare-registry.example.org/graphql",
            "contents": """
                input DiseaseFilter { mondoId: ID!, minEvidence: Float }
                type GeneEvidence { gene: String!, score: Float!, trials: [ID!]! }
                type Disease { id: ID!, label: String!, evidence: [GeneEvidence!]! }
                type Query { disease(filter: DiseaseFilter!): Disease }
                type Mutation { curateDisease(id: ID!, note: String!): Boolean! }
            """,
            "expected_format": "graphql",
            "expected_candidates": 2,
            "expected_reviewable": 1,
        },
        {
            "case": "Post-market safety AsyncAPI",
            "question": "Can new respiratory safety signals be represented without opening a listener?",
            "name": "safety.yaml",
            "contents": yaml.safe_dump(
                {
                    "asyncapi": "3.0.0",
                    "info": {"title": "Safety alerts", "version": "1"},
                    "servers": {
                        "prod": {
                            "host": "safety.example.org",
                            "protocol": "https",
                        }
                    },
                    "channels": {
                        "alerts": {
                            "address": "neuromuscular/safety/{drugId}",
                            "servers": [{"$ref": "#/servers/prod"}],
                        }
                    },
                    "operations": {
                        "receiveSignal": {
                            "action": "receive",
                            "channel": {"$ref": "#/channels/alerts"},
                            "messages": [{"$ref": "#/components/messages/signal"}],
                        }
                    },
                    "components": {
                        "messages": {
                            "signal": {
                                "payload": {
                                    "type": "object",
                                    "properties": {
                                        "drugId": {"type": "string"},
                                        "event": {"type": "string"},
                                        "caseCount": {"type": "integer"},
                                    },
                                    "required": ["drugId", "event", "caseCount"],
                                }
                            }
                        }
                    },
                },
                sort_keys=True,
            ),
            "expected_format": "asyncapi",
            "expected_candidates": 1,
            "expected_reviewable": 0,
        },
        {
            "case": "Natural-history cohort Postman collection",
            "question": "Which longitudinal motor scores are available for the SMA cohort?",
            "name": "cohort.postman_collection.json",
            "contents": json.dumps(
                {
                    "info": {
                        "name": "SMA natural history",
                        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
                    },
                    "variable": [
                        {"key": "baseUrl", "value": "https://cohort.example.org"}
                    ],
                    "item": [
                        {
                            "name": "Participants",
                            "item": [
                                {
                                    "name": "Motor trajectory",
                                    "request": {
                                        "method": "GET",
                                        "url": {
                                            "raw": "{{baseUrl}}/trajectory",
                                            "query": [
                                                {"key": "participant", "value": ""},
                                                {"key": "months", "value": ""},
                                            ],
                                        },
                                    },
                                },
                                {
                                    "name": "Annotate visit",
                                    "request": {
                                        "method": "POST",
                                        "url": "{{baseUrl}}/visits",
                                        "body": {"mode": "raw", "raw": "{}"},
                                    },
                                },
                            ],
                        }
                    ],
                },
                sort_keys=True,
            ),
            "expected_format": "postman",
            "expected_candidates": 2,
            "expected_reviewable": 1,
        },
        {
            "case": "Molecular diagnostics WSDL",
            "question": "Can a legacy laboratory panel result be identified without invoking SOAP?",
            "name": "diagnostics.wsdl",
            "contents": """<?xml version="1.0"?>
                <definitions xmlns="http://schemas.xmlsoap.org/wsdl/"
                  xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/" name="DiagnosticLab">
                  <portType name="PanelPort"><operation name="GetSMNPanel">
                    <input message="GetSMNPanelRequest"/><output message="GetSMNPanelResponse"/>
                  </operation></portType>
                  <binding name="PanelBinding" type="PanelPort"><operation name="GetSMNPanel">
                    <soap:operation soapAction="urn:GetSMNPanel"/>
                  </operation></binding>
                  <service name="DiagnosticLab"><port name="PanelPort" binding="PanelBinding">
                    <soap:address location="https://diagnostics.example.org/soap"/>
                  </port></service>
                </definitions>""",
            "expected_format": "wsdl",
            "expected_candidates": 1,
            "expected_reviewable": 0,
        },
        {
            "case": "Variant evidence gRPC/protobuf",
            "question": "Can SMN1 variant evidence and a streaming update be distinguished?",
            "name": "variants.proto",
            "endpoint": "https://variants.example.org",
            "contents": """
                syntax = "proto3";
                package variants.v1;
                message VariantRequest { string hgvs = 1; string assembly = 2; }
                message VariantEvidence { string classification = 1; double score = 2; }
                service VariantEvidenceService {
                  rpc GetEvidence(VariantRequest) returns (VariantEvidence);
                  rpc WatchEvidence(VariantRequest) returns (stream VariantEvidence);
                }
            """,
            "expected_format": "protobuf",
            "expected_candidates": 2,
            "expected_reviewable": 0,
        },
        {
            "case": "Literature synthesis MCP manifest",
            "question": "Can remote literature tools be inventoried without running a local server command?",
            "name": "literature.mcp.json",
            "contents": json.dumps(
                {
                    "mcpServers": {
                        "literature": {
                            "url": "https://literature.example.org/mcp",
                            "transport": "http",
                            "tools": [
                                {"name": "search_sma_trials"},
                                {"name": "summarize_smn2_evidence"},
                            ],
                        },
                        "local-unreviewed": {
                            "command": "python",
                            "args": ["server.py"],
                        },
                    }
                },
                sort_keys=True,
            ),
            "expected_format": "mcp",
            "expected_candidates": 2,
            "expected_reviewable": 1,
        },
    ]


def run_case() -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    assertions: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="tooluniverse-vsd-contracts-") as directory:
        root = Path(directory)
        for definition in _documents():
            path = root / definition["name"]
            path.write_text(definition["contents"], encoding="utf-8")
            report = inspect_contract_document(
                path, endpoint=definition.get("endpoint")
            )
            for candidate in report["candidates"]:
                validate_contract_candidate(candidate)
            observed = {
                "case": definition["case"],
                "question": definition["question"],
                "source_format": report["source_format"],
                "source_document_sha256": report["source_document_sha256"],
                "candidate_count": report["candidate_count"],
                "reviewable_count": report["reviewable_count"],
                "blocked_count": report["blocked_count"],
                "operations": [
                    {
                        "candidate_id": item["candidate_id"],
                        "name": item["name"],
                        "kind": item["kind"],
                        "endpoint": item["endpoint"],
                        "blockers": item["blockers"],
                    }
                    for item in report["candidates"]
                ],
            }
            results.append(observed)
            checks = {
                "format_detected": report["source_format"]
                == definition["expected_format"],
                "operation_count_exact": report["candidate_count"]
                == definition["expected_candidates"],
                "reviewable_count_exact": report["reviewable_count"]
                == definition["expected_reviewable"],
                "all_candidates_inert": all(
                    item["execution_allowed"] is False
                    and item["approval_state"] == "unreviewed_candidate"
                    for item in report["candidates"]
                ),
            }
            for check, passed in checks.items():
                assertions.append(
                    {"case": definition["case"], "assertion": check, "passed": passed}
                )

    assertions.extend(
        [
            {
                "case": "Portfolio",
                "assertion": "six_contract_formats_covered",
                "passed": {item["source_format"] for item in results}
                == {"graphql", "asyncapi", "postman", "wsdl", "protobuf", "mcp"},
            },
            {
                "case": "Portfolio",
                "assertion": "unsafe_operations_have_blockers",
                "passed": all(
                    operation["blockers"]
                    for result in results
                    for operation in result["operations"]
                    if operation["kind"]
                    in {
                        "graphql_mutation",
                        "asyncapi_receive",
                        "soap_operation",
                        "grpc_rpc",
                    }
                ),
            },
            {
                "case": "Portfolio",
                "assertion": "source_and_candidate_provenance_complete",
                "passed": all(
                    len(result["source_document_sha256"]) == 64
                    and all(
                        len(item["candidate_id"]) == 16 for item in result["operations"]
                    )
                    for result in results
                ),
            },
        ]
    )
    if not all(item["passed"] for item in assertions):
        raise AssertionError([item for item in assertions if not item["passed"]])
    report_body = {
        "format": "vsd_multiformat_contract_case_v1",
        "case_title": "Spinal muscular atrophy heterogeneous evidence intake",
        "research_question": (
            "Can six incompatible provider contract formats be converted into a "
            "reviewable inventory for an SMA evidence workflow without executing "
            "provider calls, opening listeners, or running local commands?"
        ),
        "conclusion": (
            "Yes. Ten operations across six formats were inventoried with exact "
            "source and candidate identities; safe read candidates were separated "
            "from mutations, event transports, SOAP, gRPC, and local MCP commands "
            "that require later explicit review."
        ),
        "case_count": len(results),
        "operation_count": sum(item["candidate_count"] for item in results),
        "assertion_count": len(assertions),
        "results": results,
        "assertions": assertions,
    }
    return {
        **report_body,
        "case_sha256": hashlib.sha256(
            json.dumps(report_body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
    }


def _markdown(report: dict[str, Any]) -> str:
    rows = []
    for result in report["results"]:
        rows.append(
            f"| {result['case']} | `{result['source_format']}` | "
            f"{result['candidate_count']} | {result['reviewable_count']} | "
            f"{result['blocked_count']} |"
        )
    return "\n".join(
        [
            "# Multi-format VSD Contract Proof",
            "",
            "## Research question",
            "",
            report["research_question"],
            "",
            "## Result",
            "",
            report["conclusion"],
            "",
            "| Case | Format | Operations | Reviewable | Blocked |",
            "| --- | --- | ---: | ---: | ---: |",
            *rows,
            "",
            f"All {report['assertion_count']} assertions passed. Case identity: "
            f"`{report['case_sha256']}`.",
            "",
            "The inspection used only local contract files. No provider request, "
            "listener, RPC channel, or local MCP command was executed.",
            "",
        ]
    )


def main() -> None:
    report = run_case()
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_ARTIFACT.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    MARKDOWN_ARTIFACT.write_text(_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "passed",
                "cases": report["case_count"],
                "operations": report["operation_count"],
                "assertions": report["assertion_count"],
                "case_sha256": report["case_sha256"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
