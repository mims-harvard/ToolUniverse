"""Round 007 fixes — verified from researcher-persona findings.

Covers three fixes:
- ClinVar silent-failure on a dbSNP rsID (Feature-007-001)
- DGIdb double-nested ``data.data`` envelope (Feature-007-002)
- BaseRESTTool ``lowercase_params`` for case-sensitive backends (Feature-007-003)
"""

import unittest
from unittest.mock import patch, MagicMock

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Feature-007-001: ClinVar rsID returns a real error, not silent success
# ---------------------------------------------------------------------------
class TestClinVarRsidSilentFailure(unittest.TestCase):
    """An rsID passed to a numeric-UID endpoint must not yield status:success."""

    def _make_tool(self):
        from tooluniverse.clinvar_tool import ClinVarGetClinicalSignificance

        config = {
            "name": "ClinVar_get_clinical_significance",
            "type": "ClinVarGetClinicalSignificance",
            "fields": {
                "endpoint": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils",
                "format": "json",
            },
        }
        return ClinVarGetClinicalSignificance(config)

    def test_rsid_returns_actionable_error(self):
        tool = self._make_tool()
        # NCBI esummary: HTTP 200 success envelope, empty uids, inline error.
        with patch.object(tool, "_make_request") as mock_request:
            mock_request.return_value = {
                "status": "success",
                "data": {
                    "error": "Invalid uid rs4244285 at position= 0",
                    "result": {"uids": []},
                },
                "url": "https://eutils.ncbi.nlm.nih.gov/...",
            }
            result = tool.run({"variant_id": "rs4244285"})
        self.assertEqual(result["status"], "error")
        self.assertIn("rs4244285", result["error"])
        self.assertIn("numeric ClinVar Variation ID", result["error"])
        # The raw NCBI message is surfaced too.
        self.assertIn("Invalid uid", result["error"])

    def test_missing_numeric_record_is_error_not_success(self):
        tool = self._make_tool()
        with patch.object(tool, "_make_request") as mock_request:
            mock_request.return_value = {
                "status": "success",
                "data": {"result": {"uids": []}},
            }
            result = tool.run({"variant_id": "99999999"})
        self.assertEqual(result["status"], "error")
        self.assertIn("99999999", result["error"])


# ---------------------------------------------------------------------------
# Feature-007-002: DGIdb envelope unwraps GraphQL data + adds metadata
# ---------------------------------------------------------------------------
class TestDGIdbEnvelope(unittest.TestCase):
    def test_unwraps_graphql_data_and_counts_nodes(self):
        """data holds the GraphQL payload directly with a node count."""
        from tooluniverse.dgidb_tool import DGIdbTool

        payload = {"data": {"genes": {"nodes": [{"name": "KRAS"}, {"name": "TP53"}]}}}
        env = DGIdbTool._envelope(payload, "genes")
        self.assertEqual(env["status"], "success")
        # No more data.data nesting: data holds the GraphQL payload directly.
        self.assertEqual(env["data"], {"genes": {"nodes": [{"name": "KRAS"}, {"name": "TP53"}]}})
        self.assertEqual(env["metadata"]["total"], 2)

    def test_graphql_errors_become_error_status(self):
        """A GraphQL errors block maps to status:error."""
        from tooluniverse.dgidb_tool import DGIdbTool

        env = DGIdbTool._envelope({"errors": [{"message": "boom"}]}, "genes")
        self.assertEqual(env["status"], "error")
        self.assertIn("boom", str(env["error"]))

    def test_empty_collection_total_zero(self):
        from tooluniverse.dgidb_tool import DGIdbTool

        env = DGIdbTool._envelope({"data": {"drugs": {"nodes": []}}}, "drugs")
        self.assertEqual(env["status"], "success")
        self.assertEqual(env["metadata"]["total"], 0)


# ---------------------------------------------------------------------------
# Feature-007-003: BaseRESTTool lowercase_params downcases before request
# ---------------------------------------------------------------------------
class TestBaseRESTLowercaseParams(unittest.TestCase):
    def _make_tool(self):
        from tooluniverse.base_rest_tool import BaseRESTTool

        config = {
            "name": "CPIC_get_drug_info",
            "type": "BaseRESTTool",
            "parameter": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
            "fields": {
                "endpoint": "https://api.cpicpgx.org/v1/drug?name=eq.{name}",
                "lowercase_params": ["name"],
            },
        }
        return BaseRESTTool(config)

    def test_capitalized_name_is_lowercased_in_url(self):
        """A capitalized name is downcased before the request URL is built."""
        tool = self._make_tool()
        captured = {}

        def fake_request(session, method, url, **kwargs):
            captured["url"] = url
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = []
            resp.headers = {"content-type": "application/json"}
            resp.text = "[]"
            return resp

        with patch(
            "tooluniverse.base_rest_tool.request_with_retry", side_effect=fake_request
        ):
            tool.run({"name": "Clopidogrel"})

        self.assertIn("name=eq.clopidogrel", captured["url"])
        self.assertNotIn("Clopidogrel", captured["url"])


if __name__ == "__main__":
    unittest.main()
