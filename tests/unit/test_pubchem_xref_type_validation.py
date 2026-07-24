"""PubChem xref_types validation (Feature-008B-4).

``PubChem_get_compound_xrefs_by_CID`` forwarded ``xref_types`` straight into
PubChem's ``/xrefs/{type}`` endpoint, which accepts only a fixed vocabulary.
Database-specific names (ChEBI, KEGG, InChIKey) produced an opaque HTTP 400
"Invalid xrefs type". The tool now validates up front and returns an
actionable error that lists the valid types and points to ``RegistryID``.
"""

import unittest

import pytest

pytestmark = pytest.mark.unit


def _make_tool():
    from tooluniverse.pubchem_tool import PubChemRESTTool

    return PubChemRESTTool(
        {
            "name": "PubChem_get_compound_xrefs_by_CID",
            "type": "PubChemRESTTool",
            "fields": {
                "endpoint": "/compound/cid/{cid}/xrefs/{xref_types}/JSON",
            },
            "parameter": {"properties": {}, "required": []},
        }
    )


class TestXrefTypeValidation(unittest.TestCase):
    def test_invalid_db_specific_type_is_rejected_with_guidance(self):
        tool = _make_tool()
        result = tool.run({"cid": 5280343, "xref_types": ["ChEBI", "KEGG"]})
        self.assertEqual(result["status"], "error")
        msg = result["error"]
        self.assertIn("ChEBI", msg)
        # Points the caller at the correct field and the valid vocabulary.
        self.assertIn("RegistryID", msg)
        self.assertIn("not separate xref types", msg)

    def test_valid_type_builds_url_without_error(self):
        tool = _make_tool()
        url = tool._build_url({"cid": 5280343, "xref_types": ["RegistryID"]})
        self.assertIn("/xrefs/RegistryID/", url)

    def test_comma_string_form_is_validated_too(self):
        tool = _make_tool()
        result = tool.run({"cid": 5280343, "xref_types": "InChIKey"})
        self.assertEqual(result["status"], "error")
        self.assertIn("InChIKey", result["error"])


if __name__ == "__main__":
    unittest.main()
