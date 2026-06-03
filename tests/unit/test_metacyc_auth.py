"""MetaCyc BioCyc-account authentication (revival from broken_apis).

BioCyc gates its web services behind a free account. The tool now logs in
(POST email+password -> session cookie) and carries that session on every
getxml/xmlquery request. These tests cover the credential paths with mocks
(no live BioCyc account needed) plus the no-credentials guard.
"""

import unittest
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


def _make_tool():
    from tooluniverse.metacyc_tool import MetaCycTool

    return MetaCycTool(
        {"name": "MetaCyc_get_pathway", "type": "MetaCycTool", "fields": {}, "parameter": {}}
    )


def _resp(status_code, text="", url="https://websvc.biocyc.org/getxml"):
    r = MagicMock()
    r.status_code = status_code
    r.text = text
    r.url = url
    return r


_PATHWAY_XML = (
    "<?xml version='1.0'?><ptools-xml>"
    "<Pathway ID='META:GLYCOLYSIS' orgid='META' frameid='GLYCOLYSIS'>"
    "<common-name>glycolysis</common-name>"
    "<synonym>EMP pathway</synonym>"
    "<reaction-list>"
    "<Reaction frameid='RXN-1'/><Reaction frameid='RXN-2'/>"
    "</reaction-list></Pathway></ptools-xml>"
)

_SEARCH_XML = (
    "<?xml version='1.0'?><ptools-xml>"
    "<Pathway frameid='GLYCOLYSIS'><common-name>glycolysis</common-name></Pathway>"
    "<Pathway frameid='PWY-5484'><common-name>glycolysis II</common-name></Pathway>"
    "</ptools-xml>"
)


class TestMetaCycAuth(unittest.TestCase):
    def setUp(self):
        import os

        os.environ["BIOCYC_EMAIL"] = "user@example.com"
        os.environ["BIOCYC_PASSWORD"] = "secret"

    def tearDown(self):
        import os

        os.environ.pop("BIOCYC_EMAIL", None)
        os.environ.pop("BIOCYC_PASSWORD", None)

    def test_no_credentials_returns_actionable_error(self):
        import os

        os.environ.pop("BIOCYC_EMAIL", None)
        os.environ.pop("BIOCYC_PASSWORD", None)
        tool = _make_tool()
        result = tool.run({"operation": "get_pathway", "pathway_id": "GLYCOLYSIS"})
        self.assertEqual(result["status"], "error")
        self.assertIn("BIOCYC_EMAIL", result["error"])

    def test_get_pathway_logs_in_then_parses(self):
        tool = _make_tool()
        tool.session.post = MagicMock(return_value=_resp(200))
        tool.session.get = MagicMock(return_value=_resp(200, _PATHWAY_XML))

        result = tool.run({"operation": "get_pathway", "pathway_id": "GLYCOLYSIS"})

        tool.session.post.assert_called_once()  # logged in
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["name"], "glycolysis")
        self.assertEqual(result["data"]["reaction_ids"], ["RXN-1", "RXN-2"])

    def test_login_is_cached_across_calls(self):
        tool = _make_tool()
        tool.session.post = MagicMock(return_value=_resp(200))
        tool.session.get = MagicMock(return_value=_resp(200, _PATHWAY_XML))

        tool.run({"operation": "get_pathway", "pathway_id": "GLYCOLYSIS"})
        tool.run({"operation": "get_pathway", "pathway_id": "GLYCOLYSIS"})
        # Logged in only once even though two operations ran.
        self.assertEqual(tool.session.post.call_count, 1)

    def test_bad_credentials_surface_clear_error(self):
        tool = _make_tool()
        tool.session.post = MagicMock(return_value=_resp(401))

        result = tool.run({"operation": "get_pathway", "pathway_id": "GLYCOLYSIS"})
        self.assertEqual(result["status"], "error")
        self.assertIn("Invalid BioCyc credentials", result["error"])

    def test_search_parses_pathway_hits(self):
        tool = _make_tool()
        tool.session.post = MagicMock(return_value=_resp(200))
        tool.session.get = MagicMock(
            return_value=_resp(200, _SEARCH_XML, url="https://websvc.biocyc.org/xmlquery")
        )

        result = tool.run({"operation": "search_pathways", "query": "glycolysis"})
        self.assertEqual(result["status"], "success")
        ids = [h["pathway_id"] for h in result["data"]["results"]]
        self.assertEqual(ids, ["GLYCOLYSIS", "PWY-5484"])


if __name__ == "__main__":
    unittest.main()
