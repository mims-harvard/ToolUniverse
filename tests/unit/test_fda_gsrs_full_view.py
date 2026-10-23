"""Regression tests for FDA GSRS full-view enrichment (mocked HTTP).

GSRS returns codes/names/references as link stubs (``_codes``/``_names``) in the
default view and only inlines the real arrays with ``?view=full``. The tools
fetched substances without ``view=full`` and read ``codes``/``names``, which
were therefore always empty -- so cross-references and synonyms (the primary
value of a GSRS lookup) were silently dropped under ``status: success``. These
tests lock in that both the single-substance and search paths request the full
view and surface the enriched fields.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _tool(operation):
    from tooluniverse.fda_gsrs_tool import FDAGSRSTool

    return FDAGSRSTool(
        {"name": "t", "type": "FDAGSRSTool", "fields": {"operation": operation}}
    )


def _resp(json_body):
    r = MagicMock()
    r.status_code = 200
    r.raise_for_status.return_value = None
    r.json.return_value = json_body
    return r


# A full-view substance record: codes/names inlined, InChIKey under _inchiKey.
_FULL = {
    "uuid": "u1",
    "approvalID": "3G6A5W338E",
    "_name": "CAFFEINE",
    "substanceClass": "chemical",
    "status": "approved",
    "codes": [
        {"codeSystem": "CAS", "code": "58-08-2", "type": "PRIMARY"},
        {"codeSystem": "MESH", "code": "D002110", "type": "PRIMARY"},
    ],
    "names": [
        {"name": "CAFFEINE", "type": "of", "preferred": True},
        {"name": "1,3,7-TRIMETHYLXANTHINE", "type": "cn", "preferred": False},
    ],
    "structure": {
        "formula": "C8H10N4O2",
        "smiles": "Cn1cnc2c1c(=O)n(C)c(=O)n2C",
        "_inchiKey": "RYYVLZVUVIJVGH-UHFFFAOYSA-N",
        "mwt": 194.19,
    },
}


class TestGetSubstanceFullView(unittest.TestCase):
    def test_get_substance_requests_full_view_and_parses_arrays(self):
        """get_substance asks for view=full and surfaces codes/names/InChIKey."""
        tool = _tool("get_substance")
        with patch(
            "tooluniverse.fda_gsrs_tool.requests.get", return_value=_resp(_FULL)
        ) as get:
            result = tool._get_substance({"unii": "3G6A5W338E"})
        self.assertEqual(get.call_args.kwargs["params"], {"view": "full"})
        data = result["data"]
        self.assertEqual(len(data["codes"]), 2)
        self.assertEqual(len(data["names"]), 2)
        self.assertEqual(result["metadata"]["total_names"], 2)
        self.assertEqual(
            data["structure"]["inchiKey"], "RYYVLZVUVIJVGH-UHFFFAOYSA-N"
        )


class TestSearchFullView(unittest.TestCase):
    def test_search_requests_full_view_and_populates_xrefs(self):
        """search asks for view=full so xrefs/synonyms are non-empty."""
        tool = _tool("search_substances")
        body = {"content": [_FULL], "total": 1}
        with patch(
            "tooluniverse.fda_gsrs_tool.requests.get", return_value=_resp(body)
        ) as get:
            result = tool._search_substances({"query": "caffeine", "limit": 1})
        self.assertEqual(get.call_args.kwargs["params"].get("view"), "full")
        substance = result["data"][0]
        self.assertIn("CAS", substance["xrefs"])
        self.assertTrue(substance["synonyms"])

    def test_search_offset_removes_repeated_exact_match_pin(self):
        tool = _tool("search_substances")
        pin = dict(_FULL, uuid="pin", _name="Aspirin")
        ranked = [dict(_FULL, uuid=f"u{i}", _name=f"Result {i}") for i in range(3, 6)]
        probe = {"content": [pin], "total": 24}
        page = {"content": [pin, *ranked], "total": 24}
        with patch(
            "tooluniverse.fda_gsrs_tool.requests.get",
            side_effect=[_resp(probe), _resp(page)],
        ):
            result = tool._search_substances(
                {"query": "aspirin", "limit": 3, "offset": 3}
            )

        self.assertEqual([r["uuid"] for r in result["data"]], ["u3", "u4", "u5"])
        self.assertEqual(result["metadata"]["next_offset"], 6)
        self.assertTrue(result["metadata"]["repeated_exact_match_removed"])

    def test_search_rejects_coerced_or_clamped_pagination(self):
        tool = _tool("search_substances")
        with patch("tooluniverse.fda_gsrs_tool.requests.get") as get:
            for pagination in (
                {"limit": "2"},
                {"limit": True},
                {"limit": 0},
                {"limit": 51},
                {"offset": "2"},
                {"offset": -1},
                {"offset": False},
            ):
                result = tool._search_substances(
                    {"query": "caffeine", **pagination}
                )
                self.assertEqual(result["status"], "error", pagination)
        get.assert_not_called()

    def test_get_substance_does_not_truncate_names(self):
        tool = _tool("get_substance")
        full = dict(_FULL, names=[{"name": f"name-{i}"} for i in range(64)])
        with patch(
            "tooluniverse.fda_gsrs_tool.requests.get", return_value=_resp(full)
        ):
            result = tool._get_substance({"unii": "R16CO5Y76E"})
        self.assertEqual(len(result["data"]["names"]), 64)
        self.assertEqual(result["metadata"]["total_names"], 64)


if __name__ == "__main__":
    unittest.main()
