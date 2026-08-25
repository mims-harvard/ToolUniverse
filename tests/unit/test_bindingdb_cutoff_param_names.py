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


# ---------------------------------------------------------------------------
# Round 33: query-parameter *names* and the multi-id separator.
#
# BindingDB's REST spec documents singular parameter names even on the plural
# endpoints -- `uniprot=` on getLigandsByUniprots and `pdb=` on getLigandsByPDBs
# -- with multiple ids "separated by comma". The plural spellings do not fail
# loudly: `uniprots=` returns HTTP 200 with an empty affinities list (total data
# loss reported as success) and `pdbs=` returns HTTP 500. A semicolon-joined
# list is likewise accepted with HTTP 200 and matches nothing. These tests pin
# the wire format so neither can silently regress. Transport is mocked, so they
# run offline.
# ---------------------------------------------------------------------------


def _capture(operation, arguments, envelope):
    tool = _make(operation)
    captured = {}

    def fake_http_get(path, params, timeout=30):
        captured["path"] = path
        captured["params"] = params
        return envelope

    with patch("tooluniverse.bindingdb_tool._http_get", side_effect=fake_http_get):
        captured["result"] = tool.run(arguments)
    return captured


UNIPROT_ENVELOPE = {"getLindsByUniprotsResponse": {"affinities": []}}
PDB_ENVELOPE = {"getLindsByPDBsResponse": {"affinities": []}}


def test_uniprot_param_is_singular_not_plural():
    cap = _capture("get_ligands_by_uniprot", {"uniprot_id": "O43613"}, UNIPROT_ENVELOPE)
    assert cap["path"] == "getLigandsByUniprots"
    assert cap["params"]["uniprot"] == "O43613"
    assert "uniprots" not in cap["params"]


def test_uniprot_ids_are_comma_joined_not_semicolon_joined():
    cap = _capture(
        "get_ligands_by_uniprots",
        {"uniprot_ids": "O43613,O43614"},
        UNIPROT_ENVELOPE,
    )
    assert cap["params"]["uniprot"] == "O43613,O43614"
    assert ";" not in cap["params"]["uniprot"]


def test_semicolon_separated_input_is_normalised_to_commas_on_the_wire():
    # Older callers copied the `;` spelling from BindingDB's singular-endpoint
    # docs. Accept it on input, but never send it upstream.
    cap = _capture(
        "get_ligands_by_uniprots",
        {"uniprot_ids": "O43613;O43614"},
        UNIPROT_ENVELOPE,
    )
    assert cap["params"]["uniprot"] == "O43613,O43614"


def test_pdb_param_is_singular_not_plural():
    cap = _capture("get_ligands_by_pdb", {"pdb_ids": "1Q0L,3ANM"}, PDB_ENVELOPE)
    assert cap["path"] == "getLigandsByPDBs"
    assert cap["params"]["pdb"] == "1Q0L,3ANM"
    assert "pdbs" not in cap["params"]


def test_pdb_sends_declared_sequence_identity():
    # The schema declares `sequence_identity` with a default of 100, which
    # matches what the endpoint does when `identity` is omitted.
    cap = _capture("get_ligands_by_pdb", {"pdb_ids": "4S0V"}, PDB_ENVELOPE)
    assert cap["params"]["identity"] == 100

    cap = _capture(
        "get_ligands_by_pdb",
        {"pdb_ids": "4S0V", "sequence_identity": 85},
        PDB_ENVELOPE,
    )
    assert cap["params"]["identity"] == 85
    assert cap["result"]["data"]["sequence_identity"] == 85


def test_bdb_prefixed_payload_is_normalised_and_keeps_species():
    # getTargetByCompound namespaces every key with `bdb.`; without normalising
    # it the affinities list was dropped entirely and reported as an empty
    # success. `species` matters scientifically -- hits are often non-human.
    envelope = {
        "getLindsByUniprotResponse": {
            "bdb.smile": "CCO",
            "bdb.hit": "2",
            "bdb.affinities": [
                {
                    "bdb.monomerid": 91599,
                    "bdb.target": "5-hydroxytryptamine receptor 3A",
                    "bdb.species": "Mouse",
                    "bdb.affinity_type": "Ki",
                    "bdb.affinity": ">30000",
                },
                {
                    "bdb.monomerid": 91600,
                    "bdb.target": "Acetylcholine receptor",
                    "bdb.species": "Snail",
                    "bdb.affinity_type": "Ki",
                    "bdb.affinity": " 40",
                },
            ],
        }
    }
    cap = _capture("get_targets_by_compound", {"smiles": "CCO"}, envelope)
    affinities = cap["result"]["data"]["affinities"]
    assert len(affinities) == 2
    assert affinities[0]["species"] == "Mouse"
    assert affinities[1]["species"] == "Snail"
    assert affinities[0]["target"] == "5-hydroxytryptamine receptor 3A"
    # Qualified / whitespace-padded affinity strings survive verbatim -- they are
    # never coerced to numbers.
    assert affinities[0]["affinity"] == ">30000"
    assert affinities[1]["affinity"] == " 40"
    assert not any(k.startswith("bdb.") for k in affinities[0])


def test_empty_result_is_success_with_an_explicit_note():
    # An unmatched identifier is HTTP 200 + empty list upstream, which is a
    # genuine no-data answer, not a rejected request. Keep it a success but say
    # so, otherwise an empty list is indistinguishable from a malformed query.
    cap = _capture("get_ligands_by_uniprot", {"uniprot_id": "O43613"}, UNIPROT_ENVELOPE)
    assert cap["result"]["status"] == "success"
    assert cap["result"]["data"]["affinities"] == []
    assert "no matching records" in cap["result"]["data"]["note"]


def test_non_empty_result_has_no_empty_note():
    envelope = {
        "getLindsByUniprotsResponse": {
            "affinities": [{"monomerid": "1", "affinity": ">10"}]
        }
    }
    cap = _capture("get_ligands_by_uniprot", {"uniprot_id": "O43613"}, envelope)
    assert "note" not in cap["result"]["data"]
    assert cap["result"]["data"]["affinities"][0]["affinity"] == ">10"
