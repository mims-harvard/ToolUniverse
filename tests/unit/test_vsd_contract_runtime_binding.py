from __future__ import annotations

import base64
import copy
import hashlib
import json

import pytest
from google.protobuf import descriptor_pb2

from examples.vsd.multiformat_contract_case_study import _documents
from examples.vsd.reviewed_runtime_case_study import _http_config, _json_response
from examples.vsd.source_intelligence_case_study import DANDI, _asyncapi, _postman
from tooluniverse import vsd_promotion
from tooluniverse.vsd_reviewed_runtime import VSDReviewedOperationTool
from tooluniverse.vsd_contracts import (
    VSDContractError,
    inspect_contract_document,
    validate_contract_candidate,
)

pytestmark = pytest.mark.unit


def _candidate_map(tmp_path):
    selected = {
        "graphql": "disease",
        "asyncapi": "receiveSignal",
        "postman": "Participants/Motor trajectory",
        "wsdl": "PanelPort.GetSMNPanel",
        "protobuf": "variants.v1.VariantEvidenceService.GetEvidence",
        "mcp": "literature",
    }
    candidates = {}
    for definition in _documents():
        path = tmp_path / definition["name"]
        path.write_text(definition["contents"], encoding="utf-8")
        report = inspect_contract_document(path, endpoint=definition.get("endpoint"))
        for candidate in report["candidates"]:
            if candidate["name"] == selected.get(candidate["source_format"]):
                candidates[candidate["source_format"]] = candidate
    assert set(candidates) == set(selected)
    return candidates


def _descriptor_set(*, service_name: str = "VariantEvidenceService") -> str:
    descriptor = descriptor_pb2.FileDescriptorProto(
        name="variants.proto", package="variants.v1", syntax="proto3"
    )
    request = descriptor.message_type.add(name="VariantRequest")
    request.field.add(
        name="hgvs",
        number=1,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
    )
    request.field.add(
        name="assembly",
        number=2,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
    )
    response = descriptor.message_type.add(name="VariantEvidence")
    response.field.add(
        name="classification",
        number=1,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
    )
    response.field.add(
        name="score",
        number=2,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE,
    )
    service = descriptor.service.add(name=service_name)
    service.method.add(
        name="GetEvidence",
        input_type=".variants.v1.VariantRequest",
        output_type=".variants.v1.VariantEvidence",
    )
    return base64.b64encode(
        descriptor_pb2.FileDescriptorSet(file=[descriptor]).SerializeToString()
    ).decode()


def _configs(candidates):
    graphql = _http_config(
        "BoundDiseaseGraphQL",
        "Retrieve one disease through the exact reviewed GraphQL root field.",
        candidates["graphql"]["endpoint"],
        protocol="graphql",
        properties={"filter": {"type": "object"}},
        request={
            "method": "POST",
            "reviewed_read_only": True,
            "body": {
                "mode": "graphql",
                "query": (
                    "query Disease($filter: DiseaseFilter!) "
                    "{ disease(filter: $filter) { id } }"
                ),
                "operation_name": "Disease",
                "arguments": {"filter": "filter"},
            },
        },
        response=_json_response(),
    )
    postman = _http_config(
        "BoundMotorTrajectory",
        "Retrieve the exact reviewed natural-history trajectory request.",
        candidates["postman"]["endpoint"],
        properties={
            "participant": {"type": "string"},
            "months": {"type": "string"},
        },
        request={
            "method": "GET",
            "query_arguments": {
                "participant": "participant",
                "months": "months",
            },
            "body": {"mode": "none"},
        },
        response=_json_response(),
    )
    wsdl = _http_config(
        "BoundSMNPanel",
        "Retrieve the exact reviewed molecular panel SOAP operation.",
        candidates["wsdl"]["endpoint"],
        protocol="soap",
        properties={"sample_id": {"type": "string"}},
        request={
            "method": "POST",
            "reviewed_read_only": True,
            "fixed_headers": {"SOAPAction": "urn:GetSMNPanel"},
            "body": {
                "mode": "soap",
                "envelope": (
                    "<Envelope><Body><GetSMNPanel><sample>{sample_id}</sample>"
                    "</GetSMNPanel></Body></Envelope>"
                ),
                "arguments": {"sample_id": "sample"},
            },
        },
        response={"format": "xml", "schema": {"type": "object"}},
    )
    grpc = {
        "name": "BoundVariantGRPC",
        "type": "VSDReviewedOperationTool",
        "description": "Retrieve the exact reviewed variant-evidence RPC operation.",
        "parameter": {
            "type": "object",
            "properties": {"request": {"type": "object"}},
            "required": ["request"],
            "additionalProperties": False,
        },
        "vsd_reviewed_operation": {
            "version": 1,
            "transport": "grpc",
            "protocol": "grpc",
            "endpoint": "variants.example.org:443",
            "method": "/variants.v1.VariantEvidenceService/GetEvidence",
            "descriptor_set_base64": _descriptor_set(),
            "request_type": "variants.v1.VariantRequest",
            "response_type": "variants.v1.VariantEvidence",
            "streaming": "unary",
            "max_messages": 1,
            "auth": {"type": "none"},
            "response": {"format": "json", "schema": {"type": "object"}},
        },
    }
    mcp = {
        "name": "BoundLiteratureMCP",
        "type": "VSDReviewedOperationTool",
        "description": "Invoke one exact reviewed literature tool on the declared server.",
        "parameter": {
            "type": "object",
            "properties": {"arguments": {"type": "object"}},
            "required": ["arguments"],
            "additionalProperties": False,
        },
        "vsd_reviewed_operation": {
            "version": 1,
            "transport": "mcp",
            "protocol": "mcp",
            "endpoint": candidates["mcp"]["endpoint"],
            "tool_name": "search_sma_trials",
            "auth": {"type": "none"},
            "response": {"format": "json", "schema": {"type": "object"}},
        },
    }
    event_schema = copy.deepcopy(candidates["asyncapi"]["input_schema"])
    asyncapi = {
        "name": "BoundSafetyEvent",
        "type": "VSDReviewedOperationTool",
        "description": "Validate one event from the exact reviewed AsyncAPI channel.",
        "parameter": {
            "type": "object",
            "properties": {"event": {"type": "object"}},
            "required": ["event"],
            "additionalProperties": False,
        },
        "vsd_reviewed_operation": {
            "version": 1,
            "transport": "event",
            "protocol": "asyncapi",
            "source_endpoint": candidates["asyncapi"]["endpoint"],
            "channel": candidates["asyncapi"]["contract"]["channel"],
            "event_argument": "event",
            "event_schema": event_schema,
            "auth": {"type": "none"},
            "response": {"format": "json", "schema": {"type": "object"}},
        },
    }
    return {
        "graphql": graphql,
        "asyncapi": asyncapi,
        "postman": postman,
        "wsdl": wsdl,
        "protobuf": grpc,
        "mcp": mcp,
    }


def _draft(candidate, config, workspace):
    return vsd_promotion.create_reviewed_operation_draft(
        candidate,
        config,
        resolved_blockers=candidate["blockers"],
        review_note=(
            "The exact provider, operation identity, parameters, and runtime bounds "
            "were reviewed against the content-addressed contract."
        ),
        workspace=workspace,
    )


def test_all_contract_formats_bind_exact_runtime_identity(tmp_path):
    candidates = _candidate_map(tmp_path)
    configs = _configs(candidates)
    for source_format, candidate in candidates.items():
        draft = _draft(candidate, configs[source_format], tmp_path / source_format)
        binding = draft["config"]["vsd_promotion"]["contract_binding"]
        assert binding["source_format"] == source_format
        assert binding["candidate_id"] == candidate["candidate_id"]
        assert len(binding["binding_sha256"]) == 64


@pytest.mark.parametrize(
    ("source_format", "mutation", "message"),
    [
        (
            "graphql",
            lambda config: config["vsd_reviewed_operation"].update(
                {"endpoint": "https://wrong.example.org/graphql"}
            ),
            "endpoint",
        ),
        (
            "postman",
            lambda config: config["vsd_reviewed_operation"]["request"][
                "query_arguments"
            ].update({"participant": "invented"}),
            "absent",
        ),
        (
            "wsdl",
            lambda config: config["vsd_reviewed_operation"]["request"][
                "fixed_headers"
            ].update({"SOAPAction": "urn:DifferentOperation"}),
            "SOAPAction",
        ),
        (
            "protobuf",
            lambda config: config["vsd_reviewed_operation"].update(
                {"method": "/variants.v1.VariantEvidenceService/WatchEvidence"}
            ),
            "descriptor",
        ),
        (
            "mcp",
            lambda config: config["vsd_reviewed_operation"].update(
                {"tool_name": "undeclared_tool"}
            ),
            "not declared",
        ),
        (
            "asyncapi",
            lambda config: config["vsd_reviewed_operation"].update(
                {"channel": "different/channel"}
            ),
            "channel",
        ),
    ],
)
def test_contract_binding_rejects_cross_provider_or_operation_substitution(
    tmp_path, source_format, mutation, message
):
    candidates = _candidate_map(tmp_path)
    config = copy.deepcopy(_configs(candidates)[source_format])
    mutation(config)
    with pytest.raises(vsd_promotion.VSDPromotionError, match=message):
        _draft(candidates[source_format], config, tmp_path / "rejected")


def test_postman_template_requires_explicit_complete_parameter_map(tmp_path):
    path = tmp_path / "dandi.postman_collection.json"
    path.write_bytes(_postman())
    candidate = inspect_contract_document(path)["candidates"][0]
    config = _http_config(
        "BoundDandisetLookup",
        "Retrieve one DANDI record through the explicitly mapped path variable.",
        f"https://{DANDI}/api/dandisets/{{dandiset_id}}",
        properties={"dandiset_id": {"type": "string"}},
        request={
            "method": "GET",
            "path_arguments": {"dandiset_id": "dandiset_id"},
            "body": {"mode": "none"},
        },
        response=_json_response(),
    )
    config["vsd_contract_parameters"] = {"dandisetId": "dandiset_id"}
    draft = _draft(candidate, config, tmp_path / "mapped")
    binding = draft["config"]["vsd_promotion"]["contract_binding"]
    assert binding["parameter_map"] == {"dandisetId": "dandiset_id"}
    assert binding["identity"]["endpoint"].endswith("/{dandiset_id}")

    missing = copy.deepcopy(config)
    missing.pop("vsd_contract_parameters")
    with pytest.raises(
        vsd_promotion.VSDPromotionError, match="every endpoint variable"
    ):
        _draft(candidate, missing, tmp_path / "missing")


def test_grpc_descriptor_must_contain_exact_reviewed_rpc(tmp_path):
    candidates = _candidate_map(tmp_path)
    config = _configs(candidates)["protobuf"]
    config["vsd_reviewed_operation"]["descriptor_set_base64"] = _descriptor_set(
        service_name="DifferentService"
    )
    with pytest.raises(vsd_promotion.VSDPromotionError, match="descriptor"):
        _draft(candidates["protobuf"], config, tmp_path / "bad-descriptor")


def test_asyncapi_local_channel_message_reference_preserves_payload_schema(tmp_path):
    path = tmp_path / "dandi.asyncapi.yaml"
    path.write_bytes(_asyncapi())
    candidate = inspect_contract_document(path)["candidates"][0]
    assert candidate["input_schema"]["required"] == [
        "dandisetId",
        "version",
        "changedAt",
    ]
    assert set(candidate["input_schema"]["properties"]) == {
        "dandisetId",
        "version",
        "changedAt",
    }


def test_contract_candidate_rejects_unknown_field_with_recomputed_digest(tmp_path):
    candidate = copy.deepcopy(_candidate_map(tmp_path)["graphql"])
    candidate["hidden_instruction"] = "substitute another provider"
    body = {
        key: value
        for key, value in candidate.items()
        if key not in {"candidate_id", "candidate_sha256"}
    }
    digest = hashlib.sha256(
        json.dumps(
            body, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode()
    ).hexdigest()
    candidate.update({"candidate_id": digest[:16], "candidate_sha256": digest})
    with pytest.raises(VSDContractError, match="fields"):
        validate_contract_candidate(candidate)


def test_bound_asyncapi_provenance_uses_source_endpoint_and_keeps_channel(tmp_path):
    candidates = _candidate_map(tmp_path)
    config = _configs(candidates)["asyncapi"]
    event = {"drugId": "drug-1", "event": "infection", "caseCount": 4}
    data = VSDReviewedOperationTool(config).run({"event": event})["data"]
    assert data["result"] == event
    assert data["provenance"]["provider"] == "safety.example.org"
    assert data["provenance"]["endpoint"] == "https://safety.example.org"
    assert data["provenance"]["runtime"]["channel"] == ("neuromuscular/safety/{drugId}")
