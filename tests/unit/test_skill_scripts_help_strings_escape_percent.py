"""`--help` crashed on two skill scripts because their help text contained a bare ``%``.

argparse formats help strings with ``%``, so "convert raw signal to % of control" or
"%MT ceiling" raise ``TypeError: %o format: an integer is required`` /
``ValueError: unsupported format character`` the moment a user asks for ``--help``
(fit_dose_response.py, scrna_qc.py). A literal percent sign must be written ``%%``.
This scans every skill script statically, so it needs no optional dependency.
"""

import ast
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

SKILLS = Path(__file__).parent.parent.parent / "skills"
FORMATTED = ("help", "description", "epilog")
# %(prog)s, %(default)s ... are argparse's own substitutions.
SUBSTITUTION = re.compile(
    r"%\((prog|default|type|choices|metavar|dest|const|nargs|required)\)"
)


def _unescaped_percent(text):
    stripped = SUBSTITUTION.sub("", text.replace("%%", ""))
    return "%" in stripped


def _offending_calls(path):
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if getattr(node.func, "attr", getattr(node.func, "id", None)) not in (
            "add_argument",
            "ArgumentParser",
            "add_parser",
        ):
            continue
        for keyword in node.keywords:
            value = keyword.value
            if (
                keyword.arg in FORMATTED
                and isinstance(value, ast.Constant)
                and isinstance(value.value, str)
                and _unescaped_percent(value.value)
            ):
                yield node.lineno, value.value


def test_no_skill_script_has_an_unescaped_percent_in_argparse_text():
    problems = [
        f"{path.relative_to(SKILLS)}:{line}: {text!r}"
        for path in sorted(SKILLS.rglob("*.py"))
        for line, text in _offending_calls(path)
    ]
    assert not problems, "write '%%' for a literal percent sign:\n" + "\n".join(
        problems
    )


def test_the_checker_flags_a_bare_percent_and_accepts_escapes(tmp_path):
    bad = tmp_path / "bad.py"
    bad.write_text(
        'import argparse\nargparse.ArgumentParser().add_argument("--x", help="100% pure")\n'
    )
    good = tmp_path / "good.py"
    good.write_text(
        'import argparse\nargparse.ArgumentParser().add_argument("--x", help="100%% pure, default %(default)s")\n'
    )
    assert list(_offending_calls(bad)) and not list(_offending_calls(good))
