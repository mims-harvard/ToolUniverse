"""Depth coverage for the chemical-safety-regulatory cluster.

Covers three new tools that reuse existing tool classes:
  - FDAGSRS_get_substance_relationships  (FDAGSRSTool / fda_gsrs_tool)
  - RxClass_get_class_hierarchy           (RxClassTool / rxclass_tool)
  - RxClass_get_disease_relations         (RxClassTool / rxclass_tool)

Each test mocks the upstream HTTP call so it runs offline, exercising both the
parse (success) path and a failure path. Every tool must always return a
{status: ...} envelope and never raise.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

pytestmark = pytest.mark.unit

_DATA = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"


def _load_config(filename, tool_name):
    cfgs = json.load(open(_DATA / filename))
    for cfg in cfgs:
        if cfg.get("name") == tool_name:
            return cfg
    raise AssertionError(f"{tool_name} not found in {filename}")


def _mock_resp(payload, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = payload
    resp.headers = {"content-type": "application/json"}
    resp.text = json.dumps(payload)
    resp.raise_for_status.return_value = None
    return resp


def _http_error_resp(status=500):
    resp = MagicMock()
    resp.status_code = status
    err = requests.exceptions.HTTPError(response=MagicMock(status_code=status))
    err.response = MagicMock(status_code=status)
    resp.raise_for_status.side_effect = err
    return resp


# ---------------------------------------------------------------------------
# FDAGSRS_get_substance_relationships
# ---------------------------------------------------------------------------

GSRS_FULL_PAYLOAD = {
    "uuid": "a05ec20c-8fe2-4e02-ba7f-df69e5e30248",
    "approvalID": "R16CO5Y76E",
    "_name": "Aspirin",
    "substanceClass": "chemical",
    "relationships": [
        {
            "type": "SALT/SOLVATE->PARENT",
            "interactionType": "",
            "qualification": "",
            "comments": "",
            "amount": {},
            "relatedSubstance": {
                "name": "Aspirin calcium",
                "approvalID": "WOD7W0DGZS",
                "substanceClass": "chemical",
            },
        },
        {
            "type": "IMPURITY->PARENT",
            "interactionType": "CHROMATOGRAPHIC PURITY (HPLC/UV)",
            "qualification": "EP",
            "comments": "IDENTIFIED AS IMPURITY E",
            "amount": {
                "highLimit": 0.15,
                "units": "%",
                "type": "WEIGHT PERCENT",
                "nonNumericValue": "peak area",
            },
            "relatedSubstance": {
                "name": "SALSALATE",
                "approvalID": "V9MO595C9I",
                "substanceClass": "reference",
            },
        },
        {
            "type": "METABOLITE ACTIVE->PARENT",
            "interactionType": "",
            "qualification": "",
            "comments": "",
            "amount": {},
            "relatedSubstance": {
                "name": "Salicylic acid",
                "approvalID": "O414PZ4LPZ",
                "substanceClass": "chemical",
            },
        },
        {
            "type": "ACTIVE MOIETY",
            "interactionType": "",
            "qualification": "",
            "comments": "",
            "amount": {},
            "relatedSubstance": {
                "name": "Aspirin",
                "approvalID": "R16CO5Y76E",
                "substanceClass": "chemical",
            },
        },
    ],
    "references": [
        {
            "docType": "EP",
            "citation": "EP 10.5",
            "publicDomain": True,
            "tags": [],
        },
        {
            "docType": "SRS_LOCATOR",
            "citation": "ASPIRIN [USP]",
            "publicDomain": True,
            "tags": [],
        },
    ],
}


def _make_gsrs():
    from tooluniverse.fda_gsrs_tool import FDAGSRSTool

    return FDAGSRSTool(
        _load_config("fda_gsrs_tools.json", "FDAGSRS_get_substance_relationships")
    )


class TestGSRSRelationships:
    def test_parse_success(self):
        """Full-view relationship graph + references parse correctly."""
        tool = _make_gsrs()
        with patch(
            "tooluniverse.fda_gsrs_tool.requests.get",
            return_value=_mock_resp(GSRS_FULL_PAYLOAD),
        ):
            out = tool.run({"unii": "R16CO5Y76E"})
        assert out["status"] == "success"
        md = out["metadata"]
        assert md["total_relationships"] == 4
        assert md["relationship_count"] == 4
        assert md["total_references"] == 2
        assert md["relationship_type_counts"]["SALT/SOLVATE->PARENT"] == 1
        rels = out["data"]["relationships"]
        salt = next(r for r in rels if r["type"] == "SALT/SOLVATE->PARENT")
        assert salt["relatedSubstanceName"] == "Aspirin calcium"
        assert salt["relatedSubstanceUnii"] == "WOD7W0DGZS"
        # amount object rendered to a string
        imp = next(r for r in rels if r["type"] == "IMPURITY->PARENT")
        assert isinstance(imp["amount"], str)
        assert "%" in imp["amount"]
        # references included by default
        assert len(out["data"]["references"]) == 2
        assert out["data"]["references"][0]["docType"] == "EP"

    def test_relationship_type_filter(self):
        """relationship_type substring filter narrows the edge set."""
        tool = _make_gsrs()
        with patch(
            "tooluniverse.fda_gsrs_tool.requests.get",
            return_value=_mock_resp(GSRS_FULL_PAYLOAD),
        ):
            out = tool.run({"unii": "R16CO5Y76E", "relationship_type": "METABOLITE"})
        assert out["status"] == "success"
        types = {r["type"] for r in out["data"]["relationships"]}
        assert types == {"METABOLITE ACTIVE->PARENT"}
        assert out["metadata"]["relationship_count"] == 1
        assert out["metadata"]["total_relationships"] == 4

    def test_include_references_false(self):
        """include_references=False drops references but keeps the total."""
        tool = _make_gsrs()
        with patch(
            "tooluniverse.fda_gsrs_tool.requests.get",
            return_value=_mock_resp(GSRS_FULL_PAYLOAD),
        ):
            out = tool.run({"unii": "R16CO5Y76E", "include_references": False})
        assert out["status"] == "success"
        assert out["data"]["references"] == []
        assert out["metadata"]["reference_count"] == 0
        # total still reported
        assert out["metadata"]["total_references"] == 2

    def test_missing_unii(self):
        """Missing unii returns a structured error, never raises."""
        tool = _make_gsrs()
        out = tool.run({})
        assert out["status"] == "error"
        assert "unii" in out["error"].lower()

    def test_http_error_path(self):
        """Upstream HTTP 500 becomes a structured error envelope."""
        tool = _make_gsrs()
        with patch(
            "tooluniverse.fda_gsrs_tool.requests.get",
            return_value=_http_error_resp(500),
        ):
            out = tool.run({"unii": "R16CO5Y76E"})
        assert out["status"] == "error"
        assert "500" in out["error"]

    def test_not_found_path(self):
        """Empty 200 body (no uuid) is reported as an error."""
        # 200 but empty/non-substance body
        tool = _make_gsrs()
        with patch(
            "tooluniverse.fda_gsrs_tool.requests.get",
            return_value=_mock_resp({}),
        ):
            out = tool.run({"unii": "ZZZZZZZZZZ"})
        assert out["status"] == "error"


# ---------------------------------------------------------------------------
# RxClass_get_class_hierarchy
# ---------------------------------------------------------------------------

CLASSGRAPH_PAYLOAD = {
    "rxclassGraph": {
        "rxclassMinConceptItem": [
            {
                "classId": "0",
                "className": "Anatomical Therapeutic Chemical",
                "classType": "ATC1-4",
            },
            {"classId": "N", "className": "NERVOUS SYSTEM", "classType": "ATC1-4"},
            {"classId": "N02", "className": "ANALGESICS", "classType": "ATC1-4"},
            {
                "classId": "N02B",
                "className": "OTHER ANALGESICS AND ANTIPYRETICS",
                "classType": "ATC1-4",
            },
            {
                "classId": "N02BA",
                "className": "Salicylic acid and derivatives",
                "classType": "ATC1-4",
            },
        ],
        "rxclassEdge": [
            {"classId1": "N", "rela": "isa", "classId2": "0"},
            {"classId1": "N02", "rela": "isa", "classId2": "N"},
            {"classId1": "N02B", "rela": "isa", "classId2": "N02"},
            {"classId1": "N02BA", "rela": "isa", "classId2": "N02B"},
        ],
    }
}


def _make_hierarchy():
    from tooluniverse.rxclass_tool import RxClassTool

    return RxClassTool(
        _load_config("rxclass_tools.json", "RxClass_get_class_hierarchy")
    )


class TestClassHierarchy:
    def test_parse_success(self):
        """classGraph ancestor chain is parsed leaf->root."""
        tool = _make_hierarchy()
        with patch(
            "tooluniverse.rxclass_tool.requests.get",
            return_value=_mock_resp(CLASSGRAPH_PAYLOAD),
        ):
            out = tool.run({"class_id": "N02BA"})
        assert out["status"] == "success"
        assert out["metadata"]["node_count"] == 5
        assert out["metadata"]["edge_count"] == 4
        path = out["data"]["ancestor_path"]
        ids = [n["classId"] for n in path]
        assert ids == ["N02BA", "N02B", "N02", "N", "0"]
        assert path[0]["className"] == "Salicylic acid and derivatives"
        assert path[-1]["classId"] == "0"
        assert out["metadata"]["depth"] == 5

    def test_empty_graph(self):
        """Empty graph returns success with empty nodes/path."""
        tool = _make_hierarchy()
        with patch(
            "tooluniverse.rxclass_tool.requests.get",
            return_value=_mock_resp({"rxclassGraph": {}}),
        ):
            out = tool.run({"class_id": "ZZZZ"})
        assert out["status"] == "success"
        assert out["data"]["nodes"] == []
        assert out["data"]["ancestor_path"] == []
        assert out["metadata"]["node_count"] == 0

    def test_missing_class_id(self):
        """Missing class_id returns a structured error."""
        tool = _make_hierarchy()
        out = tool.run({})
        assert out["status"] == "error"
        assert "class_id" in out["error"]

    def test_http_error_path(self):
        """Upstream HTTP 503 becomes a structured error envelope."""
        tool = _make_hierarchy()
        with patch(
            "tooluniverse.rxclass_tool.requests.get",
            return_value=_http_error_resp(503),
        ):
            out = tool.run({"class_id": "N02BA"})
        assert out["status"] == "error"
        assert "503" in out["error"]


# ---------------------------------------------------------------------------
# RxClass_get_disease_relations
# ---------------------------------------------------------------------------

MEDRT_REVERSE_PAYLOAD = {
    "drugMemberGroup": {
        "drugMember": [
            {"minConcept": {"rxcui": "10368", "name": "terbutaline", "tty": "IN"}},
            {"minConcept": {"rxcui": "10438", "name": "theophylline", "tty": "IN"}},
            {"minConcept": {"rxcui": "114970", "name": "zafirlukast", "tty": "IN"}},
        ]
    }
}

MEDRT_FORWARD_PAYLOAD = {
    "rxclassDrugInfoList": {
        "rxclassDrugInfo": [
            {
                "rxclassMinConceptItem": {
                    "classId": "D001249",
                    "className": "Asthma",
                    "classType": "DISEASE",
                },
                "minConcept": {"rxcui": "435", "name": "albuterol", "tty": "IN"},
                "rela": "may_treat",
                "relaSource": "MEDRT",
            },
            {
                "rxclassMinConceptItem": {
                    "classId": "D001986",
                    "className": "Bronchial Spasm",
                    "classType": "DISEASE",
                },
                "minConcept": {"rxcui": "435", "name": "albuterol", "tty": "IN"},
                "rela": "may_treat",
                "relaSource": "MEDRT",
            },
            {
                # duplicate of first (different drug form) -> deduped on key
                "rxclassMinConceptItem": {
                    "classId": "D001249",
                    "className": "Asthma",
                    "classType": "DISEASE",
                },
                "minConcept": {"rxcui": "435", "name": "albuterol", "tty": "IN"},
                "rela": "may_treat",
                "relaSource": "MEDRT",
            },
        ]
    }
}


def _make_disease():
    from tooluniverse.rxclass_tool import RxClassTool

    return RxClassTool(
        _load_config("rxclass_tools.json", "RxClass_get_disease_relations")
    )


class TestDiseaseRelations:
    def test_reverse_lookup(self):
        """Reverse MED-RT lookup lists ingredient drugs for a disease class."""
        tool = _make_disease()
        with patch(
            "tooluniverse.rxclass_tool.requests.get",
            return_value=_mock_resp(MEDRT_REVERSE_PAYLOAD),
        ) as get:
            out = tool.run({"class_id": "D001249", "rela": "may_treat", "ttys": "IN"})
        assert out["status"] == "success"
        assert out["metadata"]["direction"] == "reverse"
        assert out["metadata"]["rela_source"] == "MEDRT"
        assert out["metadata"]["count"] == 3
        names = {d["name"] for d in out["data"]}
        assert {"terbutaline", "theophylline", "zafirlukast"} == names
        # rela carried through from the request when members omit it
        assert all(d["rela"] == "may_treat" for d in out["data"])
        # verify MEDRT source was actually sent
        _, kwargs = get.call_args
        assert kwargs["params"]["relaSource"] == "MEDRT"

    def test_forward_lookup_dedup(self):
        """Forward MED-RT lookup returns disease classes and dedupes rows."""
        tool = _make_disease()
        with patch(
            "tooluniverse.rxclass_tool.requests.get",
            return_value=_mock_resp(MEDRT_FORWARD_PAYLOAD),
        ) as get:
            out = tool.run({"drug_name": "albuterol", "rela": "may_treat"})
        assert out["status"] == "success"
        assert out["metadata"]["direction"] == "forward"
        # 3 raw items but 1 is a duplicate -> 2 unique relations
        assert out["metadata"]["count"] == 2
        class_ids = {r["classId"] for r in out["data"]}
        assert class_ids == {"D001249", "D001986"}
        _, kwargs = get.call_args
        assert kwargs["params"]["relaSource"] == "MEDRT"
        assert kwargs["params"]["relas"] == "may_treat"

    def test_no_args_error(self):
        """No drug/class args returns a structured error."""
        tool = _make_disease()
        out = tool.run({})
        assert out["status"] == "error"
        assert "drug_name" in out["error"] or "class_id" in out["error"]

    def test_http_error_path(self):
        """Upstream HTTP 500 becomes a structured error envelope."""
        tool = _make_disease()
        with patch(
            "tooluniverse.rxclass_tool.requests.get",
            return_value=_http_error_resp(500),
        ):
            out = tool.run({"drug_name": "albuterol"})
        assert out["status"] == "error"
        assert "500" in out["error"]
