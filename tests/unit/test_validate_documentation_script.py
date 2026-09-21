"""scripts/validate_documentation.py is Phase A of the devtu-docs-quality skill.

The skill (SKILL.md, SUMMARY.md, EXAMPLES.md) told users to run it, but the script did
not exist. It now does; these tests pin what it flags, what it skips, and that the
repository's own docs pass.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).parent.parent.parent
SCRIPT = ROOT / "scripts" / "validate_documentation.py"


@pytest.fixture(scope="module")
def validator():
    spec = importlib.util.spec_from_file_location("validate_documentation", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _tree(tmp_path, files):
    for rel, text in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return tmp_path


def test_each_deprecated_phrase_is_reported_with_its_replacement(validator):
    text = "Run python -m tooluniverse.server now.\nOver 600+ tools and 750 tools.\n"
    assert validator.check_text(text) == [
        (1, "python -m tooluniverse.server", "tooluniverse-server"),
        (2, "600+ tools", "1000+ tools"),
        (2, "750 tools", "1000+ tools"),
    ]


def test_current_wording_and_larger_counts_are_not_flagged(validator):
    assert validator.check_text("1000+ tools, 6000 tools, tooluniverse-server\n") == []


def test_a_line_with_the_suppression_marker_is_ignored(validator):
    assert validator.check_text("old: 600+ tools  <!-- noqa: docs-validate -->\n") == []


def test_main_scans_docs_readme_and_skills_and_skips_the_describing_files(
    validator, tmp_path, capsys
):
    root = _tree(
        tmp_path,
        {
            "docs/guide.rst": "We support 600+ tools.\n",
            "README.md": "Start with python -m tooluniverse.server\n",
            "skills/some-skill/SKILL.md": "750+ tools\n",
            "docs/dev_docs/GUIDE.md": "600+ tools (quoted on purpose)\n",
            "skills/devtu-docs-quality/EXAMPLES.md": "Found: 600+ tools\n",
            "src/module.md": "600+ tools\n",
        },
    )
    assert validator.main(root) == 1
    output = capsys.readouterr().out
    assert "docs/guide.rst:1" in output
    assert "README.md:1" in output
    assert "skills/some-skill/SKILL.md:1" in output
    assert "dev_docs" not in output and "devtu-docs-quality" not in output
    assert "src/module.md" not in output
    assert "3 problem(s)" in output


def test_a_clean_tree_exits_zero(validator, tmp_path):
    root = _tree(tmp_path, {"docs/a.rst": "1000+ tools\n", "README.md": "ok\n"})
    assert validator.main(root) == 0


def test_the_repository_docs_pass(validator, capsys):
    assert validator.main(ROOT) == 0, capsys.readouterr().out
