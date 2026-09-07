"""Regression guard for Fix-27B-03: UniProtIDMap_gene_to_uniprot silently
swallowed an unrecognized species parameter and answered for the wrong
organism.

Confirmed live before the fix:
``{"gene_names": "GRIN2B", "organism": "mouse"}`` returned
``status: success`` with ``species_taxid: 9606`` and six *human*
accessions (Q13224, ...). The documented call
``{"gene_names": "GRIN2B", "tax_id": 10090}`` returns
``species_taxid: 10090`` with Q01097 (mouse Grin2b) -- so the caller was
handed a confident cross-species wrong answer rather than an empty
result or an error. Arbitrary junk keys were accepted the same way.

BaseTool.validate_parameters intentionally leaves a mixed valid/unknown
key set alone unless the unknown key fuzzy-matches an unset schema
property, and ``organism`` is not a near-miss of ``tax_id``. It does,
however, honor ``additionalProperties: false`` through jsonschema, which
these schemas previously omitted. Fixed with a config-only change to
src/tooluniverse/data/uniprot_idmapping_tools.json, so the rejection
happens at input validation -- before any network call.
"""

import json
from pathlib import Path

import pytest

from tooluniverse.uniprot_idmapping_tool import UniProtIDMappingTool

pytestmark = pytest.mark.unit

_CONFIG_PATH = (
    Path(__file__).parent.parent.parent
    / "src"
    / "tooluniverse"
    / "data"
    / "uniprot_idmapping_tools.json"
)

_ALL_TOOL_NAMES = [
    "UniProtIDMap_convert_ids",
    "UniProtIDMap_to_pdb",
    "UniProtIDMap_gene_to_uniprot",
    "UniProtIDMap_list_databases",
]


def _load_config(name):
    for cfg in json.loads(_CONFIG_PATH.read_text()):
        if cfg["name"] == name:
            return cfg
    raise AssertionError(f"tool config not found: {name}")


def _tool(name):
    return UniProtIDMappingTool(_load_config(name))


class TestUnknownParametersRejected:
    def test_organism_is_rejected_and_named_in_the_error(self):
        error = _tool("UniProtIDMap_gene_to_uniprot").validate_parameters(
            {"gene_names": "GRIN2B", "organism": "mouse"}
        )
        assert error is not None
        assert "organism" in str(error)

    def test_arbitrary_unknown_key_is_rejected(self):
        error = _tool("UniProtIDMap_gene_to_uniprot").validate_parameters(
            {"gene_names": "GRIN2B", "zzzbogus": "xyz"}
        )
        assert error is not None
        assert "zzzbogus" in str(error)

    def test_documented_species_call_is_accepted(self):
        error = _tool("UniProtIDMap_gene_to_uniprot").validate_parameters(
            {"gene_names": "GRIN2B", "tax_id": 10090}
        )
        assert error is None

    def test_all_declared_parameters_still_accepted(self):
        error = _tool("UniProtIDMap_gene_to_uniprot").validate_parameters(
            {"gene_names": "INS", "tax_id": 9606, "reviewed_only": True}
        )
        assert error is None

    @pytest.mark.parametrize("name", _ALL_TOOL_NAMES)
    def test_every_tool_in_the_file_declares_additional_properties_false(self, name):
        assert _load_config(name)["parameter"]["additionalProperties"] is False

    def test_internal_keys_are_stripped_before_validation(self):
        """BaseTool.validate_parameters filters ``ctx`` and
        ``_tooluniverse_stream`` before handing arguments to jsonschema, so
        additionalProperties: false must not reject them."""
        error = _tool("UniProtIDMap_gene_to_uniprot").validate_parameters(
            {"gene_names": "GRIN2B", "ctx": object(), "_tooluniverse_stream": True}
        )
        assert error is None

    def test_list_databases_accepts_empty_arguments(self):
        assert _tool("UniProtIDMap_list_databases").validate_parameters({}) is None

    def test_sibling_tools_reject_unknown_keys(self):
        convert = _tool("UniProtIDMap_convert_ids").validate_parameters(
            {"ids": "TP53", "from_db": "Gene_Name", "organism": "mouse"}
        )
        assert convert is not None and "organism" in str(convert)

        to_pdb = _tool("UniProtIDMap_to_pdb").validate_parameters(
            {"uniprot_ids": "P04637", "zzzbogus": "xyz"}
        )
        assert to_pdb is not None and "zzzbogus" in str(to_pdb)


class TestTaxIdDocumentation:
    def test_tax_id_description_states_it_is_optional_and_human_by_default(self):
        desc = _load_config("UniProtIDMap_gene_to_uniprot")["parameter"]["properties"][
            "tax_id"
        ]["description"]
        assert "Required." not in desc
        assert "Optional" in desc
        assert "9606" in desc and "10090" in desc
