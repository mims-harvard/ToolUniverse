"""Round 91: BindingDB silently ignored its schema-declared filter params.

The tool's JSON schema declares `affinity_cutoff` (uniprot/pdb endpoints) and
`similarity_cutoff` (compound endpoint), but the code read `cutoff`/`similarity`
instead -- so a caller's filter value was silently dropped and the hardcoded
default was always used (confirmed live: passing affinity_cutoff=1 echoed
cutoff=10000). These tests capture the params actually sent to the BindingDB
REST layer and assert the schema-declared names now flow through.
"""

from unittest.mock import patch

from tooluniverse.bindingdb_tool import BindingDBTool


def _make(operation):
    cfg = {
        "name": f"BindingDB_{operation}",
        "type": "BindingDBTool",
        "fields": {"operation": operation},
        "parameter": {"type": "object", "properties": {}},
    }
    return BindingDBTool(cfg)


def test_affinity_cutoff_flows_to_uniprots_endpoint():
    tool = _make("get_ligands_by_uniprots")
    captured = {}

    def fake_http_get(path, params, timeout=30):
        captured["params"] = params
        return {"getLigandsByUniprotsResponse": {"affinities": []}}

    with patch("tooluniverse.bindingdb_tool._http_get", side_effect=fake_http_get):
        res = tool.run({"uniprot_ids": "P07900", "affinity_cutoff": 1})

    assert res["status"] == "success"
    assert captured["params"]["cutoff"] == 1
    assert res["data"]["cutoff"] == 1


def test_affinity_cutoff_defaults_when_omitted():
    tool = _make("get_ligands_by_uniprots")
    captured = {}

    def fake_http_get(path, params, timeout=30):
        captured["params"] = params
        return {"getLigandsByUniprotsResponse": {"affinities": []}}

    with patch("tooluniverse.bindingdb_tool._http_get", side_effect=fake_http_get):
        tool.run({"uniprot_ids": "P07900"})

    assert captured["params"]["cutoff"] == 10000


def test_legacy_cutoff_name_still_accepted():
    # Backward compatibility: the internal search_by_target caller passes `cutoff`.
    tool = _make("get_ligands_by_uniprots")
    captured = {}

    def fake_http_get(path, params, timeout=30):
        captured["params"] = params
        return {"getLigandsByUniprotsResponse": {"affinities": []}}

    with patch("tooluniverse.bindingdb_tool._http_get", side_effect=fake_http_get):
        tool.run({"uniprot_ids": "P07900", "cutoff": 42})

    assert captured["params"]["cutoff"] == 42


def test_affinity_cutoff_flows_to_pdb_endpoint():
    tool = _make("get_ligands_by_pdb")
    captured = {}

    def fake_http_get(path, params, timeout=30):
        captured["params"] = params
        return {"getLigandsByPDBsResponse": {"affinities": []}}

    with patch("tooluniverse.bindingdb_tool._http_get", side_effect=fake_http_get):
        tool.run({"pdb_ids": "2RGP", "affinity_cutoff": 5})

    assert captured["params"]["cutoff"] == 5


def test_similarity_cutoff_flows_to_compound_endpoint():
    tool = _make("get_targets_by_compound")
    captured = {}

    def fake_http_get(path, params, timeout=30):
        captured["params"] = params
        return {"getTargetByCompoundResponse": {"affinities": []}}

    with patch("tooluniverse.bindingdb_tool._http_get", side_effect=fake_http_get):
        res = tool.run({"smiles": "CCO", "similarity_cutoff": 0.5})

    assert captured["params"]["similarity"] == 0.5
    assert res["data"]["similarity"] == 0.5


def test_similarity_cutoff_defaults_when_omitted():
    tool = _make("get_targets_by_compound")
    captured = {}

    def fake_http_get(path, params, timeout=30):
        captured["params"] = params
        return {"getTargetByCompoundResponse": {"affinities": []}}

    with patch("tooluniverse.bindingdb_tool._http_get", side_effect=fake_http_get):
        tool.run({"smiles": "CCO"})

    assert captured["params"]["similarity"] == 0.85
