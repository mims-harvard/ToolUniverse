"""PathwayCommons_get_pathway conflated "this secondary field's traverse
request failed" with "this pathway genuinely has no such data" -- `_traverse`
returns None on a failed request but [] on a genuinely-empty-but-successful
one, yet `_get_pathway` used `x[0] if x else None` / `x or []` for comment,
organism, data_source, sub_pathways, and participants, collapsing both cases
to the same None/[] output with zero indication anything failed (flagged as
a deferred lead in round 75, fixed in round 88). The primary `name` field
was already handled correctly (`if name is None: return error`) -- these
tests cover the secondary fields getting the same distinction via a new
`metadata.fetch_failures` list.
"""

import unittest
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


def _make_tool():
    from tooluniverse.pathwaycommons_tool import PathwayCommonsTool

    return PathwayCommonsTool(
        {
            "name": "PathwayCommons_get_pathway",
            "type": "PathwayCommonsTool",
            "fields": {"operation": "get_pathway"},
            "parameter": {"type": "object", "properties": {}, "required": ["uri"]},
        }
    )


def _resp(status_code, traverse_entry=None):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = {"traverseEntry": traverse_entry or []}
    return r


PATH_TO_FIELD = {
    "Pathway/displayName": "name",
    "Pathway/comment": "comment",
    "Pathway/organism/displayName": "organism",
    "Pathway/dataSource/displayName": "data_source",
    "Pathway/pathwayComponent:Pathway/displayName": "sub_pathways",
    "Pathway/pathwayComponent/participant/displayName": "participants",
}


def _side_effect_factory(failing_fields, values):
    def _get(url, params=None, timeout=None):
        path = params["path"]
        field = PATH_TO_FIELD[path]
        if field in failing_fields:
            return _resp(500)
        value = values.get(field, [])
        return _resp(200, [{"value": value}] if value else [])

    return _get


class TestFetchFailureDistinction(unittest.TestCase):
    def test_all_succeed_no_fetch_failures_key(self):
        tool = _make_tool()
        tool.session.get = MagicMock(
            side_effect=_side_effect_factory(
                failing_fields=set(),
                values={"name": ["Apoptosis"], "comment": ["A pathway."]},
            )
        )

        result = tool._get_pathway({"uri": "http://example.org/p1"})

        self.assertEqual(result["status"], "success")
        self.assertNotIn("fetch_failures", result["metadata"])
        self.assertEqual(result["data"]["pathway"]["description"], "A pathway.")

    def test_genuinely_empty_field_not_flagged_as_failure(self):
        """A request that succeeds with no data must NOT appear in fetch_failures."""
        tool = _make_tool()
        tool.session.get = MagicMock(
            side_effect=_side_effect_factory(
                failing_fields=set(), values={"name": ["Apoptosis"]}
            )
        )

        result = tool._get_pathway({"uri": "http://example.org/p1"})

        self.assertEqual(result["status"], "success")
        self.assertNotIn("fetch_failures", result["metadata"])
        self.assertIsNone(result["data"]["pathway"]["description"])
        self.assertEqual(result["data"]["sub_pathways"], [])

    def test_failed_secondary_field_flagged_distinctly_from_empty(self):
        tool = _make_tool()
        tool.session.get = MagicMock(
            side_effect=_side_effect_factory(
                failing_fields={"comment"}, values={"name": ["Apoptosis"]}
            )
        )

        result = tool._get_pathway({"uri": "http://example.org/p1"})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metadata"]["fetch_failures"], ["comment"])
        # Still None -- callers reading only `description` can't tell the
        # difference, but `fetch_failures` now makes it discoverable.
        self.assertIsNone(result["data"]["pathway"]["description"])

    def test_multiple_failed_fields_all_listed(self):
        tool = _make_tool()
        tool.session.get = MagicMock(
            side_effect=_side_effect_factory(
                failing_fields={"sub_pathways", "participants"},
                values={"name": ["Apoptosis"]},
            )
        )

        result = tool._get_pathway({"uri": "http://example.org/p1"})

        self.assertEqual(
            set(result["metadata"]["fetch_failures"]),
            {"sub_pathways", "participants"},
        )
        self.assertEqual(result["data"]["sub_pathways"], [])
        self.assertEqual(result["metadata"]["sub_pathway_count"], 0)

    def test_primary_name_failure_still_hard_errors(self):
        """Unchanged existing behavior: a failed `name` fetch is a full error."""
        tool = _make_tool()
        tool.session.get = MagicMock(
            side_effect=_side_effect_factory(failing_fields={"name"}, values={})
        )

        result = tool._get_pathway({"uri": "http://example.org/p1"})

        self.assertEqual(result["status"], "error")
