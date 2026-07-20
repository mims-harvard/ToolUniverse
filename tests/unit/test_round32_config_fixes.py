"""Config-content regression guards for two Round 32 fixes that don't need
a live/mocked tool run to verify -- just that the JSON config says the
right thing.
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_DATA_DIR = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"


def _tool_config(filename, name):
    configs = json.loads((_DATA_DIR / filename).read_text())
    for cfg in configs:
        if cfg["name"] == name:
            return cfg
    raise AssertionError(f"{name} not found in {filename}")


class TestCpicDrugInfoEmptyResultNote:
    def test_empty_result_note_is_configured(self):
        cfg = _tool_config("cpic_tools.json", "CPIC_get_drug_info")
        note = cfg["fields"]["empty_result_note"]
        assert "cyclosporine" in note
        assert "FK506" in note


class TestChemblAdalimumabExampleIdCorrected:
    """Fix-R32B-7: multiple tool descriptions in chembl_tools.json claimed
    CHEMBL1201581 was adalimumab -- confirmed live via ChEMBL_get_drug that
    CHEMBL1201581 is actually infliximab ("Infliximab (chimeric mab)"), and
    CHEMBL1201580 is the real adalimumab (confirmed via its "D2E7"
    development-code biotherapeutic description and "Abrilada" biosimilar
    synonym). A researcher trusting the old example would silently pull
    the wrong drug's mechanism-of-action data."""

    def test_search_drugs_example_uses_correct_adalimumab_id(self):
        cfg = _tool_config("chembl_tools.json", "ChEMBL_search_drugs")
        desc = cfg["parameter"]["properties"]["molecule_chembl_id"]["description"]
        assert "CHEMBL1201580" in desc
        assert "CHEMBL1201581" not in desc

    def test_get_drug_mechanisms_example_uses_correct_adalimumab_id(self):
        cfg = _tool_config("chembl_tools.json", "ChEMBL_get_drug_mechanisms")
        desc = cfg["parameter"]["properties"]["drug_chembl_id"]["description"]
        assert "CHEMBL1201580" in desc
        assert "CHEMBL1201581" not in desc
