from __future__ import annotations

import json

import pytest

from tooluniverse import ToolUniverse
from tooluniverse import vsd_promotion, vsd_reviewed_runtime
from tooluniverse.vsd_contracts import inspect_contract_document

pytestmark = pytest.mark.unit


def _candidate(tmp_path):
    path = tmp_path / "diagnostics.wsdl"
    path.write_text(
        """<definitions xmlns="http://schemas.xmlsoap.org/wsdl/"
        xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/">
        <portType name="PanelPort"><operation name="GetSMNPanel">
        <input message="Request"/><output message="Response"/>
        </operation></portType>
        <binding name="PanelBinding" type="PanelPort"><operation name="GetSMNPanel">
        <soap:operation soapAction="urn:GetSMNPanel"/></operation></binding>
        <service name="Lab"><port name="PanelPort" binding="PanelBinding">
        <soap:address location="https://diagnostics.example.org/soap"/>
        </port></service></definitions>""",
        encoding="utf-8",
    )
    return inspect_contract_document(path)["candidates"][0]


def _config():
    return {
        "name": "ReviewedSMNPanel",
        "type": "VSDReviewedOperationTool",
        "description": "Retrieve an existing reviewed SMN molecular panel result without mutation.",
        "category": "special_tools",
        "cacheable": False,
        "parameter": {
            "type": "object",
            "properties": {"sample_id": {"type": "string", "pattern": "^S-[0-9]{3}$"}},
            "required": ["sample_id"],
            "additionalProperties": False,
        },
        "return_schema": {"type": "object"},
        "vsd_reviewed_operation": {
            "version": 1,
            "transport": "http",
            "protocol": "soap",
            "endpoint": "https://diagnostics.example.org/soap",
            "timeout_seconds": 20,
            "auth": {"type": "none"},
            "request": {
                "method": "POST",
                "reviewed_read_only": True,
                "fixed_headers": {"SOAPAction": "urn:GetSMNPanel"},
                "body": {
                    "mode": "soap",
                    "envelope": "<Envelope><Body><GetSMNPanel><sample>{sample_id}</sample></GetSMNPanel></Body></Envelope>",
                    "arguments": {"sample_id": "sample"},
                },
            },
            "response": {
                "format": "xml",
                "schema": {
                    "type": "object",
                    "properties": {"Envelope": {"type": "object"}},
                    "required": ["Envelope"],
                },
            },
            "pagination": {"type": "none"},
        },
    }


def _cases():
    return [
        {
            "arguments": {"sample_id": sample_id},
            "expect": {
                "result_type": "object",
                "required_fields": ["Envelope"],
                "equals": {},
                "required_paths": ["/Envelope/Body/Panel/gene"],
                "equals_paths": {"/Envelope/Body/Panel/sample": sample_id},
            },
        }
        for sample_id in ("S-101", "S-202", "S-303")
    ]


def test_reviewed_contract_uses_full_promotion_and_loading_pipeline(
    tmp_path, monkeypatch
):
    candidate = _candidate(tmp_path)
    assert candidate["blockers"] == [
        "soap_operation_requires_explicit_read_only_review"
    ]

    def exchange(**kwargs):
        body = kwargs["body"].decode()
        sample = body.split("<sample>", 1)[1].split("</sample>", 1)[0]
        raw = (
            f"<Envelope><Body><Panel><sample>{sample}</sample>"
            "<gene>SMN1</gene><copyNumber>1</copyNumber>"
            "</Panel></Body></Envelope>"
        ).encode()
        return raw, {
            "url": kwargs["url"],
            "status_code": 200,
            "content_type": "text/xml",
            "response_bytes": len(raw),
            "headers": {},
            "peer_ip": "203.0.113.10",
            "redirects": 0,
        }

    monkeypatch.setattr(vsd_reviewed_runtime, "_http_exchange", exchange)
    draft = vsd_promotion.create_reviewed_operation_draft(
        candidate,
        _config(),
        resolved_blockers=candidate["blockers"],
        review_note=(
            "The SOAP action is a side-effect-free retrieval operation; the fixed "
            "envelope exposes only the reviewed sample identifier."
        ),
        workspace=tmp_path,
    )
    assert (
        draft["config"]["vsd_promotion"]["candidate_sha256"]
        == candidate["candidate_sha256"]
    )
    evidence = vsd_promotion.verify_draft(
        draft["draft_id"], _cases(), workspace=tmp_path
    )
    assert evidence["all_cases_passed"] is True
    assert evidence["case_count"] == 3
    approval = vsd_promotion.approve_draft(
        draft["draft_id"],
        reviewed_by="Integration Reviewer",
        decision_note="Approved after three exact molecular panel retrieval cases passed.",
        workspace=tmp_path,
    )
    publication = vsd_promotion.publish_draft(draft["draft_id"], workspace=tmp_path)
    assert publication["approval_sha256"] == approval["approval_sha256"]

    tooluniverse = ToolUniverse()
    try:
        assert vsd_promotion.load_published_tools(tooluniverse, workspace=tmp_path) == [
            "ReviewedSMNPanel"
        ]
        response = tooluniverse.run_one_function(
            {"name": "ReviewedSMNPanel", "arguments": {"sample_id": "S-404"}},
            use_cache=False,
        )
    finally:
        tooluniverse.close()
    assert response["status"] == "success"
    assert response["data"]["result"]["Envelope"]["Body"]["Panel"] == {
        "sample": "S-404",
        "gene": "SMN1",
        "copyNumber": "1",
    }
    rendered = json.dumps(publication)
    assert "S-101" not in rendered


def test_draft_requires_exact_blocker_acknowledgement_and_matching_transport(tmp_path):
    candidate = _candidate(tmp_path)
    with pytest.raises(
        vsd_promotion.VSDPromotionError, match="every candidate blocker"
    ):
        vsd_promotion.create_reviewed_operation_draft(
            candidate,
            _config(),
            resolved_blockers=[],
            review_note="This note is intentionally long enough for validation.",
            workspace=tmp_path,
        )

    wrong = _config()
    wrong["vsd_reviewed_operation"]["protocol"] = "rest"
    with pytest.raises(vsd_promotion.VSDPromotionError, match="does not match"):
        vsd_promotion.create_reviewed_operation_draft(
            candidate,
            wrong,
            resolved_blockers=candidate["blockers"],
            review_note="This note is intentionally long enough for validation.",
            workspace=tmp_path,
        )
