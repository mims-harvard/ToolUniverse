import json
import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "gen_api_key_catalog", REPO / "scripts" / "gen_api_key_catalog.py"
)
gen = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gen)

_INFO = {
    "domain": "Genomics", "type": "secret", "register_url": "u",
    "purpose": "p", "without": "w",
}


def test_scan_configs_collects_keys_and_inline_info(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    (data / "a_tools.json").write_text(json.dumps([{
        "required_api_keys": ["K1"],
        "api_key_info": {"K1": _INFO},
    }]))
    (data / "b_tools.json").write_text(json.dumps([{"optional_api_keys": ["K1", "K2"]}]))
    monkeypatch.setattr(gen, "DATA", data)
    found, info, conflicts = gen.scan_configs()
    assert found["K1"]["requirement"] == "required"   # required wins over optional
    assert found["K2"]["requirement"] == "optional"
    assert found["K1"]["used_by"] == {"a_tools.json", "b_tools.json"}
    assert info["K1"] == _INFO
    assert conflicts == []


def test_scan_configs_flags_conflicting_inline_info(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    (data / "a_tools.json").write_text(json.dumps([{"required_api_keys": ["K1"], "api_key_info": {"K1": _INFO}}]))
    other = dict(_INFO, purpose="DIFFERENT")
    (data / "b_tools.json").write_text(json.dumps([{"required_api_keys": ["K1"], "api_key_info": {"K1": other}}]))
    monkeypatch.setattr(gen, "DATA", data)
    found, info, conflicts = gen.scan_configs()
    assert ("K1", "b_tools.json") in conflicts
    assert info["K1"] == _INFO  # first seen kept


def test_build_catalog_reports_missing_and_unused():
    found = {"K1": {"requirement": "required", "used_by": {"a.json"}}}
    info = {"K2": dict(_INFO)}
    catalog, missing, unused = gen.build_catalog(found, info)
    assert catalog == []
    assert missing == ["K1"]   # declared but no api_key_info
    assert unused == ["K2"]    # api_key_info but never declared


def test_build_catalog_emits_entry():
    found = {"K1": {"requirement": "optional", "used_by": {"b.json", "a.json"}}}
    info = {"K1": dict(_INFO, domain="Genomics")}
    catalog, missing, unused = gen.build_catalog(found, info)
    assert missing == [] and unused == []
    assert catalog == [{
        "name": "K1", "requirement": "optional", "type": "secret", "domain": "Genomics",
        "register_url": "u", "purpose": "p", "without": "w",
        "used_by": ["a.json", "b.json"],
    }]


def test_render_env_template_groups_by_domain():
    catalog = [
        {"name": "A_KEY", "requirement": "required", "type": "secret",
         "domain": "Drugs & Chemistry", "register_url": "u", "purpose": "p", "without": "w", "used_by": []},
        {"name": "B_KEY", "requirement": "optional", "type": "secret",
         "domain": "Genomics & Variants", "register_url": "u2", "purpose": "p2", "without": "w2", "used_by": []},
    ]
    text = gen.render_env_template(catalog)
    assert text.index("=== Genomics & Variants ===") < text.index("=== Drugs & Chemistry ===")
    assert "B_KEY (optional) — p2" in text
    assert "Without: w" in text
    assert "AUTO-GENERATED" in text
