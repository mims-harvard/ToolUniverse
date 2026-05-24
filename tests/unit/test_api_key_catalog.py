import json
import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "gen_api_key_catalog", REPO / "scripts" / "gen_api_key_catalog.py"
)
gen = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gen)


def test_discover_keys_marks_required_over_optional(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    (data / "a_tools.json").write_text(json.dumps([{"required_api_keys": ["K1"]}]))
    (data / "b_tools.json").write_text(json.dumps([{"optional_api_keys": ["K1", "K2"]}]))
    monkeypatch.setattr(gen, "DATA", data)
    found = gen.discover_keys()
    assert found["K1"]["requirement"] == "required"
    assert found["K2"]["requirement"] == "optional"
    assert found["K1"]["used_by"] == {"a_tools.json", "b_tools.json"}


def test_build_catalog_reports_missing_and_unused():
    found = {"K1": {"requirement": "required", "used_by": {"a.json"}}}
    metadata = {"K2": {"type": "secret", "register_url": "u", "description": "d"}}
    catalog, missing, unused = gen.build_catalog(found, metadata)
    assert catalog == []
    assert missing == ["K1"]
    assert unused == ["K2"]


def test_build_catalog_emits_entry():
    found = {"K1": {"requirement": "optional", "used_by": {"b.json", "a.json"}}}
    metadata = {"K1": {"type": "secret", "register_url": "u", "description": "d"}}
    catalog, missing, unused = gen.build_catalog(found, metadata)
    assert missing == [] and unused == []
    assert catalog == [{
        "name": "K1", "requirement": "optional", "type": "secret",
        "register_url": "u", "description": "d", "used_by": ["a.json", "b.json"],
    }]
