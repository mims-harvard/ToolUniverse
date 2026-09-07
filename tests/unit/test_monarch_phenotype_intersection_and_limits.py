"""Monarch phenotype tools: deterministic, complete, and honest about failure.

Three defects, all verified live against https://api-v3.monarchinitiative.org
before the fix:

1. ``get_joint_associated_diseases_by_HPO_ID_list`` sliced an unordered ``set``
   to ``limit``. Three identical calls for HP:0002524 (Cataplexy) returned three
   different 5-disease differentials; whether Niemann-Pick type C -- the one
   treatable secondary cataplexy -- appeared depended on the process hash seed.

2. Each phenotype leg was fetched with a hard-coded ``limit=500`` and that one
   page was intersected as if it were the phenotype's whole disease set.
   HP:0001250 (Seizure) has ``total: 5331`` upstream, so the leg carried 9% of
   its diseases. Seizure + Cataplexy returned exactly one disease and omitted
   Niemann-Pick C1/C2, which carry both phenotypes.

3. ``get_HPO_ID_by_phenotype`` multiplies the requested limit by 3 to survive
   client-side namespace filtering. Monarch rejects ``limit > 500`` with HTTP
   422, so any request above 166 produced a 422 body returned under
   ``status: "success"`` -- quoting ``"input": "501"``, an internal over-fetch
   factor the caller never supplied, leaking out as if it were their argument.
"""

import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

CONFIG = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "tooluniverse"
    / "data"
    / "monarch_tools.json"
)


def _tool(cls_name, tool_name):
    """Build the tool from its real shipped config, not a hand-rolled stub."""
    from tooluniverse import restful_tool

    with open(CONFIG) as fh:
        for cfg in json.load(fh):
            if cfg["name"] == tool_name:
                return getattr(restful_tool, cls_name)(cfg)
    raise AssertionError(f"{tool_name} not in monarch_tools.json")


JOINT_TOOL = "get_joint_associated_diseases_by_HPO_ID_list"
SEARCH_TOOL = "get_HPO_ID_by_phenotype"


def _page(labels, total):
    return {
        "items": [{"subject_label": name} for name in labels],
        "total": total,
    }


class TestJointDiseasesDeterminism(unittest.TestCase):
    def test_intersection_is_stable_and_follows_upstream_rank_order(self):
        tool = _tool("MonarchDiseasesForMultiplePhenoTool", JOINT_TOOL)
        ranked = ["disease %02d" % i for i in range(1, 12)]

        outputs = []
        for _ in range(3):
            with patch(
                "tooluniverse.restful_tool.execute_RESTful_query",
                return_value=_page(ranked, len(ranked)),
            ):
                outputs.append(tool.run({"HPO_ID_list": ["HP:0002524"], "limit": 5}))

        first = outputs[0]
        self.assertEqual(first["diseases"], ranked[:5], "lost upstream rank order")
        for other in outputs[1:]:
            self.assertEqual(other["diseases"], first["diseases"])
        # The caller must be able to see that 5 is not the whole answer.
        self.assertEqual(first["total_matched"], 11)

    def test_intersection_keeps_only_diseases_present_in_every_leg(self):
        tool = _tool("MonarchDiseasesForMultiplePhenoTool", JOINT_TOOL)
        legs = [
            _page(["Niemann-Pick disease type C", "narcolepsy 1", "other"], 3),
            _page(["Niemann-Pick disease type C", "unrelated"], 2),
        ]
        with patch("tooluniverse.restful_tool.execute_RESTful_query", side_effect=legs):
            result = tool.run(
                {"HPO_ID_list": ["HP:0001250", "HP:0002524"], "limit": 50}
            )
        self.assertEqual(result, ["Niemann-Pick disease type C"])


class TestJointDiseasesPagination(unittest.TestCase):
    def test_a_leg_larger_than_one_page_is_paged_not_truncated(self):
        """Seizure has 5331 associations; one page of 500 is not the answer."""
        tool = _tool("MonarchDiseasesForMultiplePhenoTool", JOINT_TOOL)
        page1 = _page(["d%04d" % i for i in range(500)], 750)
        page2 = _page(["d%04d" % i for i in range(500, 750)], 750)
        calls = []

        def fake(endpoint_url, variables=None):
            calls.append(dict(variables or {}))
            return page1 if len(calls) == 1 else page2

        with patch("tooluniverse.restful_tool.execute_RESTful_query", fake):
            result = tool.run({"HPO_ID_list": ["HP:0001250"], "limit": 1000})

        self.assertEqual(len(calls), 2, "second page was never requested")
        self.assertEqual(calls[0]["offset"], 0)
        self.assertEqual(calls[1]["offset"], 500)
        self.assertEqual(len(result), 750)
        # A disease only reachable on page 2 must be present.
        self.assertIn("d0700", result)

    def test_still_short_of_total_is_disclosed_not_silently_returned(self):
        tool = _tool("MonarchDiseasesForMultiplePhenoTool", JOINT_TOOL)
        # Upstream claims 9999 but stops yielding rows: budget exhausted.
        with patch(
            "tooluniverse.restful_tool.execute_RESTful_query",
            return_value=_page(["a", "b"], 9999),
        ):
            result = tool.run({"HPO_ID_list": ["HP:0001250"], "limit": 50})

        self.assertIn("warning", result)
        self.assertIn("truncated", result["warning"].lower())
        self.assertIn("HP:0001250", result["warning"])
        self.assertIn("partial", result["warning"].lower())


class TestJointDiseasesContract(unittest.TestCase):
    """The object form must satisfy the tool's own declared return_schema."""

    def _schema(self):
        with open(CONFIG) as fh:
            for cfg in json.load(fh):
                if cfg["name"] == JOINT_TOOL:
                    return cfg["return_schema"]
        raise AssertionError("config missing")

    def test_object_form_validates_against_return_schema(self):
        import jsonschema

        tool = _tool("MonarchDiseasesForMultiplePhenoTool", JOINT_TOOL)
        ranked = ["disease %02d" % i for i in range(1, 12)]
        with patch(
            "tooluniverse.restful_tool.execute_RESTful_query",
            return_value=_page(ranked, len(ranked)),
        ):
            # Truncated by limit, but nothing went wrong -> no 'warning'.
            result = tool.run({"HPO_ID_list": ["HP:0001250"], "limit": 5})

        self.assertNotIn("warning", result)
        jsonschema.validate(result, self._schema())

    def test_offset_selects_a_different_page_of_the_intersection(self):
        """'offset' was overwritten by the pager and became a silent no-op."""
        tool = _tool("MonarchDiseasesForMultiplePhenoTool", JOINT_TOOL)
        ranked = ["disease %02d" % i for i in range(1, 12)]
        pages = []
        for off in (0, 1):
            with patch(
                "tooluniverse.restful_tool.execute_RESTful_query",
                return_value=_page(ranked, len(ranked)),
            ):
                pages.append(
                    tool.run(
                        {"HPO_ID_list": ["HP:0001250"], "limit": 3, "offset": off}
                    )["diseases"]
                )
        self.assertEqual(pages[0], ranked[0:3])
        self.assertEqual(pages[1], ranked[1:4])
        self.assertNotEqual(pages[0], pages[1])

    def test_caller_offset_is_not_sent_as_the_pager_offset(self):
        tool = _tool("MonarchDiseasesForMultiplePhenoTool", JOINT_TOOL)
        seen = []

        def fake(endpoint_url, variables=None):
            seen.append(dict(variables or {}))
            return _page(["a", "b"], 2)

        with patch("tooluniverse.restful_tool.execute_RESTful_query", fake):
            tool.run({"HPO_ID_list": ["HP:0001250"], "limit": 5, "offset": 7})

        self.assertEqual(seen[0]["offset"], 0, "caller offset leaked into the leg")

    def test_empty_running_intersection_stops_fetching_later_phenotypes(self):
        """Each extra leg costs up to 20 upstream requests; none can refill it."""
        tool = _tool("MonarchDiseasesForMultiplePhenoTool", JOINT_TOOL)
        legs = [_page(["only-a"], 1), _page(["only-b"], 1)]
        calls = {"n": 0}

        def fake(endpoint_url, variables=None):
            calls["n"] += 1
            return legs[min(calls["n"] - 1, len(legs) - 1)]

        with patch("tooluniverse.restful_tool.execute_RESTful_query", fake):
            result = tool.run(
                {"HPO_ID_list": ["HP:1", "HP:2", "HP:3", "HP:4"], "limit": 5}
            )

        self.assertEqual(result, [])
        self.assertEqual(calls["n"], 2, "kept paging after the intersection emptied")


class TestUpstreamValidationBodyIsNotSuccess(unittest.TestCase):
    def _search_tool(self):
        return _tool("MonarchTool", SEARCH_TOOL)

    def test_over_fetch_is_clamped_to_the_upstream_ceiling(self):
        """limit=167 * 3 = 501, which Monarch 422s. It must be clamped."""
        from tooluniverse.restful_tool import _MONARCH_MAX_LIMIT

        tool = self._search_tool()
        sent = {}

        def fake(endpoint_url, variables=None):
            sent.update(variables or {})
            return {"items": [], "total": 0}

        with patch("tooluniverse.restful_tool.execute_RESTful_query", fake):
            tool.run({"query": "seizure", "limit": 167})

        self.assertLessEqual(sent["limit"], _MONARCH_MAX_LIMIT)

    def test_unsatisfiable_limit_errors_instead_of_returning_a_short_page(self):
        """A limit this tool cannot serve must fail like its sibling does.

        Clamping alone made get_HPO_ID_by_phenotype answer limit=600 with 490
        items under status:"success" and no note, while Monarch_search_gene --
        same class, no result_id_prefix, so no clamp -- errored on the same
        request. Two tools on one class must not disagree about the contract.
        """
        from tooluniverse.restful_tool import _MONARCH_MAX_LIMIT

        tool = self._search_tool()
        called = []

        def fake(endpoint_url, variables=None):
            called.append(variables)
            return {"items": [], "total": 0}

        for bad in (_MONARCH_MAX_LIMIT + 1, 1000, 0, -5):
            with patch("tooluniverse.restful_tool.execute_RESTful_query", fake):
                result = tool.run({"query": "abnormality", "limit": bad})
            self.assertEqual(result["status"], "error", f"limit={bad}")
            self.assertIn("limit", result["error"])
        self.assertEqual(called, [], "an unsatisfiable limit still hit the network")

    def test_negative_limit_never_reaches_the_wire(self):
        """limit=-5 used to put the inflated -15 upstream."""
        tool = self._search_tool()
        post = MagicMock(return_value={"items": [], "total": 0})
        with patch("tooluniverse.restful_tool.execute_RESTful_query", post):
            result = tool.run({"query": "seizure", "limit": -5})
        self.assertEqual(result["status"], "error")
        post.assert_not_called()
        self.assertNotIn("-15", json.dumps(result))

    def test_short_page_after_namespace_filtering_is_disclosed(self):
        """490 of a requested 500 must not pass for a complete page."""
        tool = self._search_tool()
        # 500 fetched (the ceiling), only 490 survive the HP: filter.
        items = [{"id": "HP:%07d" % i} for i in range(490)]
        items += [{"id": "MP:%07d" % i} for i in range(10)]
        with patch(
            "tooluniverse.restful_tool.execute_RESTful_query",
            return_value={"items": items, "total": 3959},
        ):
            result = tool.run({"query": "abnormality", "limit": 500})

        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]["items"]), 490)
        self.assertIn("note", result)
        self.assertIn("490", result["note"])
        self.assertIn("500", result["note"])

    def test_complete_page_carries_no_note(self):
        tool = self._search_tool()
        with patch(
            "tooluniverse.restful_tool.execute_RESTful_query",
            return_value={
                "items": [{"id": "HP:%07d" % i} for i in range(60)],
                "total": 60,
            },
        ):
            result = tool.run({"query": "seizure", "limit": 20})
        self.assertEqual(len(result["data"]["items"]), 20)
        self.assertNotIn("note", result)

    def test_small_limits_still_over_fetch(self):
        tool = self._search_tool()
        sent = {}

        def fake(endpoint_url, variables=None):
            sent.update(variables or {})
            return {"items": [], "total": 0}

        with patch("tooluniverse.restful_tool.execute_RESTful_query", fake):
            tool.run({"query": "seizure", "limit": 20})

        self.assertEqual(sent["limit"], 60)

    def test_validation_body_is_returned_as_an_error(self):
        tool = self._search_tool()
        body = {
            "detail": [
                {
                    "type": "less_than_equal",
                    "loc": ["query", "limit"],
                    "msg": "Input should be less than or equal to 500",
                    "input": "501",
                    "ctx": {"le": 500},
                }
            ]
        }
        with patch(
            "tooluniverse.restful_tool.execute_RESTful_query", return_value=body
        ):
            result = tool.run({"query": "seizure", "limit": 167})

        self.assertEqual(result["status"], "error")
        self.assertIn("less than or equal to 500", result["error"])
        # The raw body must not come back: it echoes "input": "501", the
        # internally-inflated limit, not the 167 the caller supplied.
        blob = json.dumps(result)
        self.assertNotIn("501", blob)
        self.assertNotIn("upstream_response", blob)

    def test_detail_key_alongside_real_data_is_not_treated_as_an_error(self):
        from tooluniverse.restful_tool import _validation_error_detail

        self.assertIsNone(_validation_error_detail({"detail": [], "items": [1]}))
        self.assertIsNone(_validation_error_detail({"items": [], "total": 0}))
        self.assertIsNone(_validation_error_detail("not a dict"))
        self.assertEqual(
            _validation_error_detail({"detail": [{"msg": "bad limit"}]}), "bad limit"
        )


if __name__ == "__main__":
    unittest.main()
