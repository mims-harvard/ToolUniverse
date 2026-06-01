"""Unit tests for PubChem property-selection.

Regression for Feature-008B-01 / 007K-02: PubChem_get_compound_properties_by_CID
hardcoded its property set and silently ignored a caller-supplied
`properties` argument, so a user could not retrieve MolecularFormula /
InChIKey / XLogP despite the tool being named "...properties...".
"""
import pytest

from tooluniverse.pubchem_tool import PubChemRESTTool


def _make_tool():
    return PubChemRESTTool(
        {
            "name": "PubChem_get_compound_properties_by_CID",
            "type": "PubChemRESTTool",
            "fields": {
                "endpoint": "/compound/cid/{cid}/property/{property_list}/JSON",
                "property_list": ["MolecularWeight", "IUPACName", "CanonicalSMILES"],
            },
            "parameter": {"type": "object", "properties": {}},
        }
    )


@pytest.mark.unit
def test_user_properties_list_overrides_default():
    url = _make_tool()._build_url(
        {"cid": 2519, "properties": ["MolecularFormula", "InChIKey", "XLogP"]}
    )
    assert "/property/MolecularFormula,InChIKey,XLogP/JSON" in url
    assert "MolecularWeight" not in url  # default set not used


@pytest.mark.unit
def test_user_properties_comma_string_overrides_default():
    url = _make_tool()._build_url({"cid": 2519, "properties": "MolecularFormula,TPSA"})
    assert "/property/MolecularFormula,TPSA/JSON" in url


@pytest.mark.unit
def test_default_property_list_used_when_not_supplied():
    url = _make_tool()._build_url({"cid": 2519})
    assert "/property/MolecularWeight,IUPACName,CanonicalSMILES/JSON" in url
