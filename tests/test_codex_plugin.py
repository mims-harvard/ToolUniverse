"""Tests for the Codex plugin packaging."""

import json
import re
import subprocess
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = REPO_ROOT / "plugins" / "tooluniverse"
PLUGIN_JSON = PLUGIN_DIR / ".codex-plugin" / "plugin.json"
MCP_JSON = PLUGIN_DIR / ".mcp.json"
SKILLS_DIR = PLUGIN_DIR / "skills"
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build-codex-plugin.sh"
DIST_DIR = REPO_ROOT / "dist" / "tooluniverse-codex-plugin"


def _parse_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path} missing YAML frontmatter"
    parts = text.split("---", 2)
    assert len(parts) >= 3, f"{path} has malformed YAML frontmatter"
    data = yaml.safe_load(parts[1])
    assert isinstance(data, dict), f"{path} frontmatter is not a mapping"
    return data


class TestCodexPluginManifest:
    def test_manifest_exists_and_is_valid_json(self):
        data = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
        assert data["name"] == "tooluniverse"
        assert re.match(r"^\d+\.\d+\.\d+$", data["version"])
        assert data["skills"] == "./skills/"
        assert data["mcpServers"] == "./.mcp.json"

    def test_manifest_paths_exist(self):
        data = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
        assert (PLUGIN_DIR / data["skills"]).is_dir()
        assert (PLUGIN_DIR / data["mcpServers"]).is_file()

    def test_interface_metadata(self):
        data = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
        interface = data["interface"]
        assert interface["displayName"] == "ToolUniverse"
        assert interface["developerName"]
        assert interface["category"] == "Research"
        assert interface["capabilities"]


class TestCodexPluginMCP:
    def test_mcp_config(self):
        data = json.loads(MCP_JSON.read_text(encoding="utf-8"))
        server = data["mcpServers"]["tooluniverse"]
        assert server["command"] == "uvx"
        assert server["args"] == ["tooluniverse"]
        assert server["env"]["PYTHONIOENCODING"] == "utf-8"


class TestCodexPluginSkills:
    def test_skills_are_generated(self):
        skill_files = sorted(SKILLS_DIR.glob("*/SKILL.md"))
        assert len(skill_files) >= 100
        assert (SKILLS_DIR / "tooluniverse" / "SKILL.md").is_file()
        assert (SKILLS_DIR / "setup-tooluniverse" / "SKILL.md").is_file()
        assert not (SKILLS_DIR / "tooluniverse-claude-code-plugin").exists()

    @pytest.mark.parametrize("skill_file", sorted(SKILLS_DIR.glob("*/SKILL.md")))
    def test_skill_frontmatter_is_codex_loadable(self, skill_file):
        data = _parse_frontmatter(skill_file)
        assert data.get("name"), f"{skill_file} missing name"
        description = data.get("description")
        assert isinstance(description, str), f"{skill_file} missing description"
        assert len(description) <= 1024, f"{skill_file} description exceeds 1024 chars"
        assert data.get("disable-model-invocation") is not True


def test_build_codex_plugin():
    subprocess.run([str(BUILD_SCRIPT)], cwd=REPO_ROOT, check=True)
    assert (DIST_DIR / ".codex-plugin" / "plugin.json").is_file()
    assert (DIST_DIR / ".mcp.json").is_file()
    assert (DIST_DIR / "skills" / "tooluniverse" / "SKILL.md").is_file()
