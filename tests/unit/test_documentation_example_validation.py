import importlib.util
import json
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[2] / "docs" / "validate_examples.py"
SPEC = importlib.util.spec_from_file_location("validate_examples", SCRIPT)
validate_examples = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = validate_examples
SPEC.loader.exec_module(validate_examples)


def test_extracts_rst_python_blocks_with_directive_options():
    heading_underline = "=" * len("Heading")
    text = f"""
Heading
{heading_underline}

.. code-block:: python
   :caption: Example

   from tooluniverse import ToolUniverse
   value = 1

Following text.
"""

    blocks = validate_examples.extract_rst_code_blocks(text, "guide/example.rst")

    assert len(blocks) == 1
    assert blocks[0].path == "guide/example.rst"
    assert blocks[0].line == 8
    assert blocks[0].code == "from tooluniverse import ToolUniverse\nvalue = 1"


@pytest.mark.parametrize(
    "opening",
    ["```python", "~~~py", "```{code-block} python"],
)
def test_extracts_markdown_and_myst_python_fences(opening):
    fence = "~~~" if opening.startswith("~") else "```"
    text = f"# Example\n\n{opening}\nanswer = 42\n{fence}\n"

    blocks = validate_examples.extract_markdown_code_blocks(text, "guide/example.md")

    assert len(blocks) == 1
    assert blocks[0].line == 4
    assert blocks[0].code == "answer = 42"


def test_recursive_discovery_excludes_build_and_translation_outputs(tmp_path):
    (tmp_path / "guide").mkdir()
    (tmp_path / "guide" / "page.rst").write_text("Page\n====\n", encoding="utf-8")
    (tmp_path / "_build").mkdir()
    (tmp_path / "_build" / "generated.rst").write_text("Generated", encoding="utf-8")
    (tmp_path / "locale").mkdir()
    (tmp_path / "locale" / "translated.md").write_text("Translated", encoding="utf-8")

    files = list(validate_examples.iter_document_files(tmp_path))

    assert [path.relative_to(tmp_path).as_posix() for path in files] == [
        "guide/page.rst"
    ]


def test_reports_exact_syntax_error_location():
    block = validate_examples.CodeBlock(
        path="guide/broken.md", line=12, code="value = 1\nif True print(value)"
    )

    issues = validate_examples.validate_block(block, check_imports=False)

    assert issues == [
        validate_examples.ValidationIssue(
            path="guide/broken.md",
            line=13,
            kind="syntax",
            message="invalid syntax",
        )
    ]


def test_checks_modules_without_executing_documentation_code(tmp_path):
    package_root = tmp_path / "tooluniverse"
    package_root.mkdir()
    (package_root / "__init__.py").write_text("raise RuntimeError('not imported')")
    block = validate_examples.CodeBlock(
        path="guide/imports.rst",
        line=4,
        code="from tooluniverse.missing import Example\nraise RuntimeError('not executed')",
    )

    issues = validate_examples.validate_block(block, package_root=package_root)

    assert issues[0].kind == "import"


def test_validation_fails_when_no_python_examples_exist(tmp_path):
    (tmp_path / "index.rst").write_text("Title\n=====\n", encoding="utf-8")

    summary = validate_examples.validate_documentation(tmp_path)

    assert not summary.valid
    assert summary.blocks_checked == 0
    assert summary.issues[0].kind == "coverage"


def test_validation_scans_nested_rst_and_markdown(tmp_path):
    guide = tmp_path / "guide"
    guide.mkdir()
    (guide / "one.rst").write_text(
        ".. code:: python\n\n   first = 1\n", encoding="utf-8"
    )
    (guide / "two.md").write_text("```python\nsecond = 2\n```\n", encoding="utf-8")

    summary = validate_examples.validate_documentation(tmp_path, check_imports=False)

    assert summary.valid
    assert summary.files_checked == 2
    assert summary.blocks_checked == 2
    assert summary.issues == ()


def test_json_output_is_machine_readable(tmp_path, capsys):
    (tmp_path / "example.md").write_text(
        "```python\nvalue = 1\n```\n", encoding="utf-8"
    )

    result = validate_examples.main(
        [
            "--docs-dir",
            str(tmp_path),
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert result == 0
    assert payload == {
        "blocks_checked": 1,
        "files_checked": 1,
        "issue_count": 0,
        "issues": [],
        "valid": True,
    }
