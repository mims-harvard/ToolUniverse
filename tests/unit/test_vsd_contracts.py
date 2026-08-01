from __future__ import annotations

import json
from copy import deepcopy

import pytest
import yaml

from tooluniverse.vsd_contracts import (
    VSDContractError,
    detect_contract_format,
    inspect_contract_document,
    validate_contract_candidate,
)
from tooluniverse.vsd_contracts_cli import main

pytestmark = pytest.mark.unit


def _write(tmp_path, name: str, contents: str | bytes):
    path = tmp_path / name
    if isinstance(contents, bytes):
        path.write_bytes(contents)
    else:
        path.write_text(contents, encoding="utf-8")
    return path


def test_graphql_sdl_inspects_queries_and_blocks_mutations(tmp_path):
    path = _write(
        tmp_path,
        "rare-disease.graphql",
        """
        enum EvidenceLevel { DEFINITIVE STRONG MODERATE }
        input DiseaseFilter { mondoId: ID!, minEvidence: EvidenceLevel }
        type GeneEvidence { gene: String!, score: Float! }
        type Disease { id: ID!, genes: [GeneEvidence!]! }
        type Query {
          disease(filter: DiseaseFilter!): Disease
          searchDiseases(term: String!, limit: Int): [Disease!]!
        }
        type Mutation { nominateGene(diseaseId: ID!, gene: String!): Boolean! }
        """,
    )
    report = inspect_contract_document(
        path, endpoint="https://registry.example.org/graphql"
    )

    assert report["source_format"] == "graphql"
    assert report["candidate_count"] == 3
    disease = next(item for item in report["candidates"] if item["name"] == "disease")
    mutation = next(
        item for item in report["candidates"] if item["name"] == "nominateGene"
    )
    assert disease["blockers"] == []
    assert disease["input_schema"]["required"] == ["filter"]
    assert disease["input_schema"]["properties"]["filter"]["properties"]["minEvidence"][
        "enum"
    ] == ["DEFINITIVE", "MODERATE", "STRONG"]
    assert mutation["blockers"] == ["graphql_mutation_requires_explicit_review"]
    assert validate_contract_candidate(disease) == disease


def test_graphql_introspection_json_is_supported(tmp_path):
    from graphql import build_schema, get_introspection_query, graphql_sync

    schema = build_schema("type Query { variant(id: ID!): String! }")
    result = graphql_sync(schema, get_introspection_query()).data
    path = _write(tmp_path, "schema.json", json.dumps({"data": result}))
    report = inspect_contract_document(
        path,
        format_hint="graphql",
        endpoint="https://genomics.example.org/graphql",
    )
    assert report["candidate_count"] == 1
    assert report["candidates"][0]["name"] == "variant"


def test_asyncapi_v2_preserves_event_schema_and_blocks_network_runtime(tmp_path):
    document = {
        "asyncapi": "2.6.0",
        "info": {"title": "Clinical alerts", "version": "1.0.0"},
        "servers": {
            "production": {
                "url": "https://events.example.org",
                "protocol": "https",
            }
        },
        "channels": {
            "rare-disease/alerts": {
                "subscribe": {
                    "operationId": "receiveRareDiseaseAlert",
                    "message": {
                        "payload": {
                            "type": "object",
                            "properties": {
                                "patientKey": {"type": "string"},
                                "mondoId": {"type": "string"},
                                "severity": {"type": "integer"},
                            },
                            "required": ["patientKey", "mondoId", "severity"],
                        }
                    },
                }
            }
        },
    }
    path = _write(tmp_path, "alerts.yaml", yaml.safe_dump(document))
    report = inspect_contract_document(path)
    candidate = report["candidates"][0]
    assert candidate["contract"]["channel"] == "rare-disease/alerts"
    assert candidate["output_schema"]["required"] == [
        "patientKey",
        "mondoId",
        "severity",
    ]
    assert "asyncapi_subscribe_requires_bounded_event_runtime" in candidate["blockers"]


def test_asyncapi_v3_operation_references_are_supported(tmp_path):
    document = {
        "asyncapi": "3.0.0",
        "info": {"title": "Variant events", "version": "2"},
        "servers": {"production": {"host": "events.example.org", "protocol": "https"}},
        "channels": {
            "variantAlerts": {
                "address": "variants/{variantId}/alerts",
                "servers": [{"$ref": "#/servers/production"}],
            }
        },
        "operations": {
            "receiveVariantAlert": {
                "action": "receive",
                "channel": {"$ref": "#/channels/variantAlerts"},
                "messages": [{"$ref": "#/components/messages/variantAlert"}],
            }
        },
        "components": {
            "messages": {
                "variantAlert": {
                    "payload": {
                        "type": "object",
                        "properties": {"variantId": {"type": "string"}},
                    }
                }
            }
        },
    }
    path = _write(tmp_path, "asyncapi.json", json.dumps(document))
    candidate = inspect_contract_document(path)["candidates"][0]
    assert candidate["kind"] == "asyncapi_receive"
    assert candidate["endpoint"] == "https://events.example.org"
    assert candidate["contract"]["channel"] == "variants/{variantId}/alerts"
    assert candidate["output_schema"]["properties"]["variantId"] == {"type": "string"}


def test_postman_collection_resolves_declared_variables_but_not_secrets(tmp_path):
    document = {
        "info": {
            "name": "Oncology evidence",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "variable": [{"key": "baseUrl", "value": "https://evidence.example.org"}],
        "item": [
            {
                "name": "Evidence",
                "item": [
                    {
                        "name": "Find variants",
                        "request": {
                            "method": "GET",
                            "url": {
                                "raw": "{{baseUrl}}/variants?gene={{gene}}",
                                "query": [{"key": "gene", "value": "{{gene}}"}],
                            },
                        },
                    },
                    {
                        "name": "Submit review",
                        "request": {
                            "method": "POST",
                            "url": "{{baseUrl}}/review",
                            "body": {"mode": "raw", "raw": "{}"},
                        },
                    },
                ],
            }
        ],
    }
    path = _write(tmp_path, "oncology.postman_collection.json", json.dumps(document))
    report = inspect_contract_document(path)
    get, post = report["candidates"]
    assert get["name"] == "Evidence/Find variants"
    assert "unresolved_postman_variable:gene" in get["blockers"]
    assert "postman_non_read_method_requires_explicit_review" in post["blockers"]
    assert "postman_raw_body_requires_review" in post["blockers"]


def test_wsdl_inspects_soap_operation_without_resolving_external_entities(tmp_path):
    path = _write(
        tmp_path,
        "laboratory.wsdl",
        """<?xml version="1.0"?>
        <definitions xmlns="http://schemas.xmlsoap.org/wsdl/"
          xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/" name="LabService">
          <portType name="LabPort">
            <operation name="GetGeneticPanel">
              <input message="GetPanelRequest"/><output message="GetPanelResponse"/>
            </operation>
          </portType>
          <binding name="LabBinding" type="LabPort">
            <operation name="GetGeneticPanel">
              <soap:operation soapAction="urn:GetGeneticPanel"/>
            </operation>
          </binding>
          <service name="LabService"><port name="LabPort" binding="LabBinding">
            <soap:address location="https://lab.example.org/soap"/>
          </port></service>
        </definitions>""",
    )
    candidate = inspect_contract_document(path)["candidates"][0]
    assert candidate["name"] == "LabPort.GetGeneticPanel"
    assert candidate["contract"]["soap_action"] == "urn:GetGeneticPanel"
    assert candidate["blockers"] == [
        "soap_operation_requires_explicit_read_only_review"
    ]

    malicious = _write(
        tmp_path,
        "external.wsdl",
        '<!DOCTYPE x [<!ENTITY file SYSTEM "file:///etc/passwd">]><definitions/>',
    )
    with pytest.raises(VSDContractError, match="DTDs and entities"):
        inspect_contract_document(malicious)


def test_protobuf_inspects_unary_and_streaming_rpcs(tmp_path):
    path = _write(
        tmp_path,
        "genomics.proto",
        """
        syntax = "proto3";
        package genomics.v1;
        message VariantRequest { string variant_id = 1; repeated string transcript = 2; }
        message Evidence { string gene = 1; double score = 2; }
        service VariantService {
          rpc GetEvidence(VariantRequest) returns (Evidence);
          rpc WatchEvidence(VariantRequest) returns (stream Evidence);
        }
        """,
    )
    report = inspect_contract_document(path, endpoint="https://grpc.example.org")
    assert report["candidate_count"] == 2
    unary, streaming = report["candidates"]
    assert unary["name"] == "genomics.v1.VariantService.GetEvidence"
    assert unary["input_schema"]["properties"]["variant_id"]["field_number"] == 1
    assert "grpc_server_stream_requires_bounded_runtime" in streaming["blockers"]


def test_mcp_manifest_distinguishes_remote_tools_from_local_commands(tmp_path):
    document = {
        "mcpServers": {
            "literature": {
                "url": "https://mcp.example.org/mcp",
                "transport": "http",
                "tools": [{"name": "search_trials"}],
            },
            "unsafe-local": {"command": "python", "args": ["server.py"]},
        }
    }
    path = _write(tmp_path, "research.mcp.json", json.dumps(document))
    report = inspect_contract_document(path)
    remote, local = report["candidates"]
    assert remote["name"] == "literature"
    assert remote["contract"]["declared_tools"] == ["search_trials"]
    assert "mcp_local_command_not_allowed" in local["blockers"]


def test_detection_validation_integrity_and_bounds_fail_closed(tmp_path):
    gql = _write(tmp_path, "schema.gql", "type Query { ping: String }")
    assert detect_contract_format(gql) == "graphql"

    candidate = inspect_contract_document(
        gql, endpoint="https://api.example.org/graphql"
    )["candidates"][0]
    modified = deepcopy(candidate)
    modified["endpoint"] = "https://attacker.example.org/graphql"
    with pytest.raises(VSDContractError, match="digest"):
        validate_contract_candidate(modified)

    duplicate = _write(
        tmp_path, "duplicate.json", '{"asyncapi":"2.6.0","asyncapi":"3.0.0"}'
    )
    with pytest.raises(VSDContractError, match="Duplicate"):
        inspect_contract_document(duplicate, format_hint="asyncapi")

    large = _write(tmp_path, "large.proto", b"x" * 1_000_001)
    with pytest.raises(VSDContractError, match="1 MB"):
        inspect_contract_document(large)


def test_cli_writes_deterministic_report(tmp_path, capsys):
    path = _write(tmp_path, "schema.graphql", "type Query { disease(id: ID!): String }")
    output = tmp_path / "report.json"
    args = [
        str(path),
        "--endpoint",
        "https://api.example.org/graphql",
        "--output",
        str(output),
    ]
    assert main(args) == 0
    first = output.read_bytes()
    assert main(args) == 0
    assert output.read_bytes() == first
    assert json.loads(first)["candidate_count"] == 1
    assert capsys.readouterr().err == ""


def test_openapi_is_delegated_to_existing_hardened_inspector(tmp_path):
    document = {
        "openapi": "3.0.3",
        "info": {"title": "Disease API", "version": "1"},
        "servers": [{"url": "https://api.example.org"}],
        "paths": {
            "/disease": {
                "get": {
                    "operationId": "getDisease",
                    "responses": {
                        "200": {
                            "description": "ok",
                            "content": {
                                "application/json": {"schema": {"type": "object"}}
                            },
                        }
                    },
                }
            }
        },
    }
    path = _write(tmp_path, "openapi.json", json.dumps(document))
    report = inspect_contract_document(path)
    assert report["format"] == "vsd_openapi_inspection_v1"
    assert report["promotable_count"] == 1
