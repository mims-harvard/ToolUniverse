"""Unit tests for the two GtoPdb depth tools.

Covers parsing and error paths for:
- GtoPdb_get_ligand_properties (merges /structure + /molecularProperties)
- GtoPdb_get_disease_associations (merges /diseaseTargets + /diseaseLigands)

All HTTP is mocked at request_with_retry so no network access is needed.
The two tools issue two sequential GET calls each, so mocks use side_effect
to return a distinct response per endpoint (in call order).
"""

from unittest.mock import Mock, patch

from tooluniverse.gtopdb_tool import GtoPdbRESTTool


def _make_tool(endpoint):
    return GtoPdbRESTTool({"fields": {"endpoint": endpoint}})


def _mock_response(status_code, payload):
    resp = Mock()
    resp.status_code = status_code
    resp.json.return_value = payload
    resp.text = str(payload)
    return resp


LIGAND_ENDPOINT = (
    "https://www.guidetopharmacology.org/services/ligands/ligandProperties"
)
DISEASE_ENDPOINT = (
    "https://www.guidetopharmacology.org/services/diseases/diseaseAssociations"
)

# Real shapes captured live from GtoPdb (ligand 4139 = aspirin).
ASPIRIN_PROPS = {
    "hydrogenBondAcceptors": 3,
    "hydrogenBondDonors": 1,
    "rotatableBonds": 3,
    "topologicalPolarSurfaceArea": 63.6,
    "molecularWeight": 180.0422588,
    "logP": 1.422,
    "lipinskisRuleOfFive": 0,
}
ASPIRIN_STRUCTURE = {
    "ligandId": 4139,
    "ligandName": "aspirin",
    "iupacName": "2-acetyloxybenzoic acid",
    "smiles": "CC(=O)Oc1ccccc1C(=O)O",
    "inchi": "InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)",
    "inchiKey": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
}

# Disease 1161 (non-allergic asthma): one target, no ligands.
ASTHMA_TARGETS = [
    {
        "targetId": 2805,
        "disease": {"diseaseId": 1161, "name": "Non-allergic (intrinsic) asthma"},
        "role": "",
        "ligandTargetInteractions": [],
    }
]


# ---------------------------------------------------------------------------
# GAP 1: GtoPdb_get_ligand_properties
# ---------------------------------------------------------------------------


def test_ligand_properties_merges_structure_and_properties():
    tool = _make_tool(LIGAND_ENDPOINT)
    # Call order in _run_ligand_properties: molecularProperties, then structure.
    with patch(
        "tooluniverse.gtopdb_tool.request_with_retry",
        side_effect=[
            _mock_response(200, ASPIRIN_PROPS),
            _mock_response(200, ASPIRIN_STRUCTURE),
        ],
    ):
        result = tool.run({"ligand_id": 4139})

    assert result["status"] == "success"
    data = result["data"]
    # Structure fields merged at top level.
    assert data["smiles"] == "CC(=O)Oc1ccccc1C(=O)O"
    assert data["inchiKey"] == "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"
    assert data["iupacName"] == "2-acetyloxybenzoic acid"
    assert data["ligandName"] == "aspirin"
    # molecularProperties nested.
    assert data["molecularProperties"]["molecularWeight"] == 180.0422588
    assert data["molecularProperties"]["lipinskisRuleOfFive"] == 0
    assert "note" not in result


def test_ligand_properties_accepts_camelcase_alias():
    tool = _make_tool(LIGAND_ENDPOINT)
    with patch(
        "tooluniverse.gtopdb_tool.request_with_retry",
        side_effect=[
            _mock_response(200, ASPIRIN_PROPS),
            _mock_response(200, ASPIRIN_STRUCTURE),
        ],
    ):
        result = tool.run({"ligandId": 4139})
    assert result["status"] == "success"
    assert result["data"]["inchiKey"] == "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"


def test_ligand_properties_partial_when_one_endpoint_missing():
    """molecularProperties 404 but structure 200 -> still success with note."""
    tool = _make_tool(LIGAND_ENDPOINT)
    with patch(
        "tooluniverse.gtopdb_tool.request_with_retry",
        side_effect=[
            _mock_response(404, {"error": "not found"}),
            _mock_response(200, ASPIRIN_STRUCTURE),
        ],
    ):
        result = tool.run({"ligand_id": 4139})
    assert result["status"] == "success"
    assert result["data"]["smiles"] == "CC(=O)Oc1ccccc1C(=O)O"
    assert "molecularProperties" not in result["data"]
    assert "molecularProperties" in result["note"]


def test_ligand_properties_invalid_id_returns_error():
    """Both endpoints fail (404 + 500) -> structured error, no exception."""
    tool = _make_tool(LIGAND_ENDPOINT)
    with patch(
        "tooluniverse.gtopdb_tool.request_with_retry",
        side_effect=[
            _mock_response(404, {"error": "not found"}),
            _mock_response(500, {"error": "Server error: l is null"}),
        ],
    ):
        result = tool.run({"ligand_id": 99999999})
    assert result["status"] == "error"
    assert "99999999" in result["error"]


def test_ligand_properties_missing_id_returns_error():
    tool = _make_tool(LIGAND_ENDPOINT)
    result = tool.run({})
    assert result["status"] == "error"
    assert "ligand_id" in result["error"]


def test_ligand_properties_network_exception_is_caught():
    """request_with_retry raising -> error dict, never propagates."""
    tool = _make_tool(LIGAND_ENDPOINT)
    with patch(
        "tooluniverse.gtopdb_tool.request_with_retry",
        side_effect=ConnectionError("boom"),
    ):
        result = tool.run({"ligand_id": 4139})
    assert result["status"] == "error"
    assert "boom" in result["error"]


# ---------------------------------------------------------------------------
# GAP 2: GtoPdb_get_disease_associations
# ---------------------------------------------------------------------------


def test_disease_associations_merges_targets_and_ligands():
    tool = _make_tool(DISEASE_ENDPOINT)
    # Call order: diseaseTargets, then diseaseLigands.
    with patch(
        "tooluniverse.gtopdb_tool.request_with_retry",
        side_effect=[
            _mock_response(200, ASTHMA_TARGETS),
            _mock_response(200, []),
        ],
    ):
        result = tool.run({"disease_id": 1161})

    assert result["status"] == "success"
    assert result["target_count"] == 1
    assert result["ligand_count"] == 0
    data = result["data"]
    assert data["diseaseId"] == 1161
    assert data["diseaseTargets"][0]["targetId"] == 2805
    assert data["diseaseLigands"] == []


def test_disease_associations_with_ligands():
    tool = _make_tool(DISEASE_ENDPOINT)
    ligands = [{"ligandId": 5702, "approved": True}, {"ligandId": 8001}]
    with patch(
        "tooluniverse.gtopdb_tool.request_with_retry",
        side_effect=[
            _mock_response(200, ASTHMA_TARGETS),
            _mock_response(200, ligands),
        ],
    ):
        result = tool.run({"disease_id": 34})
    assert result["status"] == "success"
    assert result["ligand_count"] == 2
    assert result["data"]["diseaseLigands"][0]["ligandId"] == 5702


def test_disease_associations_accepts_camelcase_alias():
    tool = _make_tool(DISEASE_ENDPOINT)
    with patch(
        "tooluniverse.gtopdb_tool.request_with_retry",
        side_effect=[
            _mock_response(200, ASTHMA_TARGETS),
            _mock_response(200, []),
        ],
    ):
        result = tool.run({"diseaseId": 1161})
    assert result["status"] == "success"
    assert result["data"]["diseaseId"] == 1161


def test_disease_associations_invalid_id_returns_error():
    """diseaseTargets 500 + diseaseLigands quirk 200/[] -> error (not empty success)."""
    tool = _make_tool(DISEASE_ENDPOINT)
    with patch(
        "tooluniverse.gtopdb_tool.request_with_retry",
        side_effect=[
            _mock_response(500, {"error": "Server error: d is null"}),
            _mock_response(200, []),
        ],
    ):
        result = tool.run({"disease_id": 99999999})
    assert result["status"] == "error"
    assert "99999999" in result["error"]


def test_disease_associations_missing_id_returns_error():
    tool = _make_tool(DISEASE_ENDPOINT)
    result = tool.run({})
    assert result["status"] == "error"
    assert "disease_id" in result["error"]


def test_disease_associations_network_exception_is_caught():
    tool = _make_tool(DISEASE_ENDPOINT)
    with patch(
        "tooluniverse.gtopdb_tool.request_with_retry",
        side_effect=RuntimeError("kaboom"),
    ):
        result = tool.run({"disease_id": 1161})
    assert result["status"] == "error"
    assert "kaboom" in result["error"]
