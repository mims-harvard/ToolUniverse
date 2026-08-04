"""Regression tests for PubChem path-style input encoding."""

import copy
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.pubchem_tool import PubChemRESTTool


DATA_PATH = (
    Path(__file__).parents[2]
    / "src"
    / "tooluniverse"
    / "data"
    / "pubchem_tools.json"
)


@pytest.fixture(scope="module")
def configs():
    return {
        config["name"]: config
        for config in json.loads(DATA_PATH.read_text(encoding="utf-8"))
    }


@pytest.mark.parametrize(
    ("smiles", "encoded"),
    [
        ("N[C@@H](C)C(=O)O", "N%5BC%40%40H%5D%28C%29C%28%3DO%29O"),
        ("C\\C=C\\C", "C%5CC%3DC%5CC"),
    ],
)
def test_exact_smiles_path_encodes_reserved_characters(configs, smiles, encoded):
    tool = PubChemRESTTool(configs["PubChem_get_CID_by_SMILES"])

    url = tool._build_url({"smiles": smiles})

    assert f"/compound/smiles/{encoded}/cids/JSON" in url
    assert smiles not in url


@pytest.mark.parametrize(
    "tool_name",
    [
        "PubChem_get_CID_by_SMILES",
        "PubChem_search_compounds_by_substructure",
        "PubChem_search_compounds_by_similarity",
    ],
)
@pytest.mark.parametrize("smiles", ["C/C=C/C", "C#N", "C?C"])
def test_url_separator_smiles_move_out_of_path(configs, tool_name, smiles):
    tool = PubChemRESTTool(configs[tool_name])
    arguments = {"smiles": smiles}
    if tool_name == "PubChem_search_compounds_by_similarity":
        arguments["threshold"] = 0.9

    url = tool._build_url(arguments)

    assert "{smiles}" not in url
    assert smiles not in url
    assert "/smiles/cids/JSON" in url
    if "threshold" in arguments:
        assert "Threshold=90" in url


def test_multi_value_xrefs_keep_pubchem_comma_delimiter(configs):
    tool = PubChemRESTTool(configs["PubChem_get_compound_xrefs_by_CID"])

    list_url = tool._build_url(
        {"cid": 2244, "xref_types": ["RegistryID", "PatentID"]}
    )
    string_url = tool._build_url(
        {"cid": 2244, "xref_types": "RegistryID,PatentID"}
    )

    assert list_url == string_url
    assert "/xrefs/RegistryID,PatentID/JSON" in list_url
    assert "%2C" not in list_url


def test_compound_names_and_vendor_sources_are_encoded(configs):
    name_tool = PubChemRESTTool(configs["PubChem_get_CID_by_compound_name"])
    source_tool = PubChemRESTTool(configs["PubChem_get_substances_by_source"])

    name_url = name_tool._build_url({"name": "sodium chloride/solution"})
    source_url = source_tool._build_url({"source": "Vendor A/B"})

    assert "/name/sodium%20chloride%2Fsolution/cids/JSON" in name_url
    assert "/sourceall/Vendor%20A%2FB/sids/JSON" in source_url


def test_property_names_are_encoded_individually_and_comma_separated(configs):
    tool = PubChemRESTTool(configs["PubChem_get_compound_properties_by_CID"])

    url = tool._build_url(
        {"cid": 2244, "properties": ["MolecularWeight", "Custom/Property"]}
    )

    assert "/property/MolecularWeight,Custom%2FProperty/JSON" in url


def test_run_posts_reserved_smiles_and_preserves_caller_arguments(configs):
    tool = PubChemRESTTool(configs["PubChem_get_CID_by_SMILES"])
    arguments = {"smiles": "C/C=C/C"}
    original = copy.deepcopy(arguments)
    response = MagicMock(status_code=200)
    response.json.return_value = {"IdentifierList": {"CID": [62695]}}

    with patch("tooluniverse.pubchem_tool.requests.get") as get, patch(
        "tooluniverse.pubchem_tool.requests.post", return_value=response
    ) as post:
        result = tool.run(arguments)

    assert result == {
        "status": "success",
        "data": {"IdentifierList": {"CID": [62695]}},
    }
    assert "/compound/smiles/cids/JSON" in post.call_args.args[0]
    assert post.call_args.kwargs["data"] == {"smiles": "C/C=C/C"}
    get.assert_not_called()
    assert arguments == original


def test_run_keeps_simple_smiles_on_get(configs):
    tool = PubChemRESTTool(configs["PubChem_get_CID_by_SMILES"])
    response = MagicMock(status_code=200)
    response.json.return_value = {"IdentifierList": {"CID": [5950]}}

    with patch(
        "tooluniverse.pubchem_tool.requests.get", return_value=response
    ) as get, patch("tooluniverse.pubchem_tool.requests.post") as post:
        result = tool.run({"smiles": "N[C@@H](C)C(=O)O"})

    assert result["status"] == "success"
    assert "%5BC%40%40H%5D" in get.call_args.args[0]
    post.assert_not_called()


def test_alias_expansion_does_not_mutate_caller_arguments(configs):
    tool = PubChemRESTTool(configs["PubChem_get_CID_by_compound_name"])
    arguments = {"compound_name": "sodium chloride"}
    response = MagicMock(status_code=200)
    response.json.return_value = {"IdentifierList": {"CID": [5234]}}

    with patch("tooluniverse.pubchem_tool.requests.get", return_value=response):
        result = tool.run(arguments)

    assert result["status"] == "success"
    assert arguments == {"compound_name": "sodium chloride"}
