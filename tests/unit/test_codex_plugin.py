"""Tests for the Codex plugin packaging."""

import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_DIR = REPO_ROOT / "plugins" / "tooluniverse"
PLUGIN_JSON = PLUGIN_DIR / ".codex-plugin" / "plugin.json"
MCP_JSON = PLUGIN_DIR / ".mcp.json"
SKILLS_DIR = PLUGIN_DIR / "skills"
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build-codex-plugin.sh"
COMPACT_SCRIPT = REPO_ROOT / "scripts" / "compact_codex_skill_description.py"
DIST_DIR = REPO_ROOT / "dist" / "tooluniverse-codex-plugin"


def _load_compact_module():
    spec = importlib.util.spec_from_file_location(
        "compact_codex_skill_description", COMPACT_SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Load the compaction module once and reuse it. Sourcing BLOCK_SCALAR_INDICATORS
# from the module (rather than re-declaring it) keeps the test's placeholder
# check tied to the exact set the script's guard enforces. A generated
# description equal to one of these tokens is the signature of the YAML-roundtrip
# corruption: a sync without PyYAML captured the indicator instead of the folded
# text on the lines below it.
COMPACT_MODULE = _load_compact_module()
BLOCK_SCALAR_INDICATORS = COMPACT_MODULE.BLOCK_SCALAR_INDICATORS


def _parse_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path} missing YAML frontmatter"
    parts = text.split("---", 2)
    assert len(parts) >= 3, f"{path} has malformed YAML frontmatter"
    data = yaml.safe_load(parts[1])
    assert isinstance(data, dict), f"{path} frontmatter is not a mapping"
    return data


@pytest.mark.unit
class TestCodexPluginManifest:
    def test_manifest_exists_and_is_valid_json(self):
        """plugin.json is valid and carries the expected core fields."""
        data = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
        assert data["name"] == "tooluniverse"
        assert re.match(r"^\d+\.\d+\.\d+$", data["version"])
        assert data["skills"] == "./skills/"
        assert data["mcpServers"] == "./.mcp.json"

    def test_manifest_paths_exist(self):
        """The skills dir and MCP config the manifest points at exist."""
        data = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
        assert (PLUGIN_DIR / data["skills"]).is_dir()
        assert (PLUGIN_DIR / data["mcpServers"]).is_file()

    def test_interface_metadata(self):
        """The Codex interface block has the display/marketplace metadata."""
        data = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
        interface = data["interface"]
        assert interface["displayName"] == "ToolUniverse"
        assert interface["developerName"]
        assert interface["category"] == "Research"
        assert interface["capabilities"]


@pytest.mark.unit
class TestCodexPluginMCP:
    def test_mcp_config(self):
        """The MCP server is wired to `uvx tooluniverse` with UTF-8 IO."""
        data = json.loads(MCP_JSON.read_text(encoding="utf-8"))
        server = data["mcpServers"]["tooluniverse"]
        assert server["command"] == "uvx"
        assert server["args"] == ["tooluniverse"]
        assert server["env"]["PYTHONIOENCODING"] == "utf-8"


@pytest.mark.unit
class TestCodexPluginSkills:
    def test_skills_are_generated(self):
        """The bundled skills are present and the Claude-only skill is excluded."""
        skill_files = sorted(SKILLS_DIR.glob("*/SKILL.md"))
        assert len(skill_files) >= 100
        assert (SKILLS_DIR / "tooluniverse" / "SKILL.md").is_file()
        assert (SKILLS_DIR / "setup-tooluniverse" / "SKILL.md").is_file()
        assert not (SKILLS_DIR / "tooluniverse-claude-code-plugin").exists()

    @pytest.mark.parametrize("skill_file", sorted(SKILLS_DIR.glob("*/SKILL.md")))
    def test_skill_frontmatter_is_codex_loadable(self, skill_file):
        """Every bundled skill satisfies Codex's frontmatter constraints."""
        data = _parse_frontmatter(skill_file)
        assert data.get("name"), f"{skill_file} missing name"
        description = data.get("description")
        assert isinstance(description, str), f"{skill_file} missing description"
        assert len(description) <= 1024, f"{skill_file} description exceeds 1024 chars"
        assert data.get("disable-model-invocation") is not True

    @pytest.mark.parametrize("skill_file", sorted(SKILLS_DIR.glob("*/SKILL.md")))
    def test_synced_description_is_not_placeholder(self, skill_file):
        """No generated description is empty or a bare YAML block-scalar indicator.

        This is the invariant the YAML-roundtrip bug violated: a sync run under
        an interpreter without PyYAML rewrote folded ``description: >-`` blocks
        down to the literal ``">-"`` token and deleted the real text.
        """
        data = _parse_frontmatter(skill_file)
        description = data.get("description")
        assert isinstance(description, str) and description.strip(), (
            f"{skill_file} has an empty or missing description"
        )
        assert description.strip() not in BLOCK_SCALAR_INDICATORS, (
            f"{skill_file} description is a bare YAML block-scalar indicator "
            f"({description!r}); the sync ran without PyYAML and corrupted it"
        )


@pytest.mark.unit
class TestCodexSkillDescriptionCompaction:
    """Direct tests for the description-compaction step of the skills sync."""

    FOLDED = (
        "---\n"
        "name: sample\n"
        "description: >-\n"
        "  First line of the description. Second clause continues here and\n"
        "  wraps onto a third physical line for good measure.\n"
        "disable-model-invocation: true\n"
        "---\n\n"
        "# Body\n"
    )

    def test_folded_scalar_description_is_preserved(self, tmp_path):
        """A folded block scalar is normalized to a single line, text intact."""
        skill = tmp_path / "SKILL.md"
        skill.write_text(self.FOLDED, encoding="utf-8")

        COMPACT_MODULE.compact(skill)

        description = _parse_frontmatter(skill)["description"]
        assert description.strip() not in BLOCK_SCALAR_INDICATORS
        assert "First line of the description" in description
        assert "wraps onto a third physical line" in description

    def test_long_description_is_truncated(self, tmp_path):
        """A description over 1024 chars is truncated to fit, with an ellipsis."""
        long_text = "word " * 400  # ~2000 chars, well over the 1024 limit
        skill = tmp_path / "SKILL.md"
        skill.write_text(
            f"---\nname: sample\ndescription: >-\n  {long_text}\n---\n\n# Body\n",
            encoding="utf-8",
        )

        COMPACT_MODULE.compact(skill)

        description = _parse_frontmatter(skill)["description"]
        assert len(description) <= 1024
        assert description.endswith("...")

    def test_extract_aborts_on_block_scalar_indicator(self, tmp_path):
        """The regex fallback must abort rather than emit an indicator token."""
        # Frontmatter that fails YAML parsing (unterminated flow sequence) yet
        # still carries a clean ``description: >-`` line for the regex to see.
        frontmatter = (
            "\nname: sample\ndescription: >-\n  real text\nbad: [unterminated\n"
        )
        with pytest.raises(SystemExit) as exc:
            COMPACT_MODULE.extract_description(frontmatter, tmp_path / "SKILL.md")
        assert exc.value.code == 1

    def test_sync_without_pyyaml_aborts_and_preserves_file(self, tmp_path):
        """No PyYAML -> loud abort with the file untouched (the crux regression).

        Against the OLD inline logic this exact path silently rewrote the file
        to ``description: ">-"`` and deleted the folded text, exiting 0. The
        fixed script imports yaml unguarded, so a missing PyYAML aborts loudly
        and never touches the file.
        """
        skill = tmp_path / "SKILL.md"
        skill.write_text(self.FOLDED, encoding="utf-8")

        # Shadow PyYAML with a module that raises ImportError, simulating a bare
        # ``python3`` on PATH that lacks the declared PyYAML dependency.
        fake_mods = tmp_path / "fakemods"
        fake_mods.mkdir()
        (fake_mods / "yaml.py").write_text(
            'raise ImportError("simulated missing PyYAML")\n', encoding="utf-8"
        )
        env = dict(os.environ)
        env["PYTHONPATH"] = str(fake_mods) + os.pathsep + env.get("PYTHONPATH", "")

        result = subprocess.run(
            [sys.executable, str(COMPACT_SCRIPT), str(skill)],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0, (
            "sync must fail loudly when PyYAML is unavailable, but it exited 0"
        )
        after = skill.read_text(encoding="utf-8")
        assert 'description: ">-"' not in after, "description was corrupted"
        assert after == self.FOLDED, "file was modified despite the abort"


@pytest.mark.unit
def test_build_codex_plugin(tmp_path):
    """The build script assembles a complete plugin bundle.

    It builds into a temp destination via the ``CODEX_PLUGIN_*`` overrides so the
    test never regenerates tracked files in place -- which is what let the
    YAML-roundtrip bug corrupt committed skills when tests ran under the wrong
    interpreter.
    """
    skills_dest = tmp_path / "skills"
    dist_dir = tmp_path / "dist"
    env = dict(os.environ)
    env["CODEX_PLUGIN_SKILLS_DEST"] = str(skills_dest)
    env["CODEX_PLUGIN_DIST"] = str(dist_dir)

    subprocess.run([str(BUILD_SCRIPT)], cwd=REPO_ROOT, check=True, env=env)

    assert (dist_dir / ".codex-plugin" / "plugin.json").is_file()
    assert (dist_dir / ".mcp.json").is_file()
    assert (dist_dir / "skills" / "tooluniverse" / "SKILL.md").is_file()
