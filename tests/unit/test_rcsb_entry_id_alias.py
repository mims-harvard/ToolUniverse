"""Round 026: RCSBData_get_entry accepts the RCSB-native 'entry_id' alias.

Regression for Feature-026B-002: callers reaching for the RCSB-native term
'entry_id' (the endpoint is /core/entry/{id}) previously hit a hard schema
validation failure because only 'pdb_id' was accepted. The tool now aliases
entry_id/id -> pdb_id in _query() and the schema accepts either.
"""

from unittest.mock import patch

from tooluniverse.rcsb_data_tool import RCSBDataTool


def _cfg():
    return {
        "name": "RCSBData_get_entry",
        "type": "RCSBDataTool",
        "fields": {"endpoint": "entry"},
        "parameter": {"type": "object", "properties": {}},
    }


def test_entry_id_is_aliased_to_pdb_id():
    captured = {}

    def fake_get_entry(args):
        captured.update(args)
        return {"status": "success", "data": {"pdb_id": args.get("pdb_id")}}

    tool = RCSBDataTool(_cfg())
    with patch.object(tool, "_get_entry", side_effect=fake_get_entry):
        out = tool.run({"entry_id": "8fmi"})
    assert out["status"] == "success"
    assert captured["pdb_id"] == "8fmi"


def test_explicit_pdb_id_not_clobbered_by_alias():
    captured = {}

    def fake_get_entry(args):
        captured.update(args)
        return {"status": "success", "data": {}}

    tool = RCSBDataTool(_cfg())
    with patch.object(tool, "_get_entry", side_effect=fake_get_entry):
        tool.run({"pdb_id": "4HHB", "entry_id": "9ZZZ"})
    assert captured["pdb_id"] == "4HHB"


def test_plain_id_alias_also_accepted():
    captured = {}

    def fake_get_entry(args):
        captured.update(args)
        return {"status": "success", "data": {}}

    tool = RCSBDataTool(_cfg())
    with patch.object(tool, "_get_entry", side_effect=fake_get_entry):
        tool.run({"id": "6LU7"})
    assert captured["pdb_id"] == "6LU7"


def test_no_identifier_returns_clear_error():
    tool = RCSBDataTool(_cfg())
    out = tool.run({})
    assert out["status"] == "error"
    assert "pdb_id" in out["error"]
