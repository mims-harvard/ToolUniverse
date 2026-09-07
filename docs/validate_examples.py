#!/usr/bin/env python3
"""Validate Python examples embedded in the ToolUniverse documentation."""

import argparse
import ast
import json
import re
import sys
import textwrap
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


PYTHON_LANGUAGES = {"py", "python", "python3"}
DOCUMENT_SUFFIXES = {".md", ".rst"}
EXCLUDED_DIRECTORIES = {".git", ".venv", "_build", "locale"}


@dataclass(frozen=True)
class CodeBlock:
    path: str
    line: int
    code: str


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    line: int
    kind: str
    message: str


@dataclass(frozen=True)
class ValidationSummary:
    files_checked: int
    blocks_checked: int
    issues: tuple[ValidationIssue, ...]

    @property
    def valid(self) -> bool:
        return self.blocks_checked > 0 and not self.issues


def _dedent(lines: list[str]) -> str:
    return textwrap.dedent("\n".join(lines)).strip()


def extract_rst_code_blocks(text: str, path: str) -> list[CodeBlock]:
    """Extract Python ``code`` and ``code-block`` directives from RST text."""
    lines = text.splitlines()
    blocks: list[CodeBlock] = []
    directive = re.compile(
        r"^(?P<indent>\s*)\.\.\s+(?:code|code-block)::\s*"
        r"(?P<language>\S+)\s*$"
    )
    index = 0

    while index < len(lines):
        match = directive.match(lines[index])
        if not match or match.group("language").lower() not in PYTHON_LANGUAGES:
            index += 1
            continue

        base_indent = len(match.group("indent"))
        cursor = index + 1
        while cursor < len(lines):
            stripped = lines[cursor].strip()
            indent = len(lines[cursor]) - len(lines[cursor].lstrip())
            if not stripped or (indent > base_indent and stripped.startswith(":")):
                cursor += 1
                continue
            break

        code_start = cursor
        code_indent = (
            len(lines[cursor]) - len(lines[cursor].lstrip())
            if cursor < len(lines)
            else base_indent + 1
        )
        code_lines: list[str] = []
        while cursor < len(lines):
            line = lines[cursor]
            if not line.strip():
                code_lines.append("")
                cursor += 1
                continue
            indent = len(line) - len(line.lstrip())
            if indent < code_indent:
                break
            code_lines.append(line)
            cursor += 1

        code = _dedent(code_lines)
        if code:
            blocks.append(CodeBlock(path=path, line=code_start + 1, code=code))
        index = max(cursor, index + 1)

    return blocks


def extract_markdown_code_blocks(text: str, path: str) -> list[CodeBlock]:
    """Extract Python fenced blocks from Markdown and MyST documents."""
    lines = text.splitlines()
    blocks: list[CodeBlock] = []
    opener = re.compile(
        r"^\s*(?P<fence>`{3,}|~{3,})\s*"
        r"(?:\{code-block\}\s*)?(?P<language>[A-Za-z0-9_+-]+)\s*$"
    )
    index = 0

    while index < len(lines):
        match = opener.match(lines[index])
        if not match or match.group("language").lower() not in PYTHON_LANGUAGES:
            index += 1
            continue

        fence = match.group("fence")
        fence_char = re.escape(fence[0])
        closer = re.compile(rf"^\s*{fence_char}{{{len(fence)},}}\s*$")
        code_start = index + 1
        cursor = code_start
        code_lines: list[str] = []
        while cursor < len(lines) and not closer.match(lines[cursor]):
            code_lines.append(lines[cursor])
            cursor += 1

        code = _dedent(code_lines)
        if code:
            blocks.append(CodeBlock(path=path, line=code_start + 1, code=code))
        index = cursor + 1 if cursor < len(lines) else cursor

    return blocks


def iter_document_files(docs_dir: Path) -> Iterable[Path]:
    for path in sorted(docs_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in DOCUMENT_SUFFIXES:
            continue
        if any(
            part in EXCLUDED_DIRECTORIES for part in path.relative_to(docs_dir).parts
        ):
            continue
        yield path


def extract_code_blocks(path: Path, docs_dir: Path) -> list[CodeBlock]:
    relative = path.relative_to(docs_dir).as_posix()
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".rst":
        return extract_rst_code_blocks(text, relative)
    return extract_markdown_code_blocks(text, relative)


def _tooluniverse_imports(tree: ast.AST) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return {module for module in modules if module.split(".", 1)[0] == "tooluniverse"}


def _module_exists(module: str, package_root: Path) -> bool:
    parts = module.split(".")
    if not parts or parts[0] != "tooluniverse":
        return True
    if len(parts) == 1:
        return package_root.is_dir()
    target = package_root.joinpath(*parts[1:])
    return target.with_suffix(".py").is_file() or (
        target.is_dir() and (target / "__init__.py").is_file()
    )


def validate_block(
    block: CodeBlock,
    check_imports: bool = True,
    package_root: Path | None = None,
) -> list[ValidationIssue]:
    try:
        tree = ast.parse(block.code, filename=f"{block.path}:{block.line}")
    except SyntaxError as exc:
        relative_line = exc.lineno or 1
        return [
            ValidationIssue(
                path=block.path,
                line=block.line + relative_line - 1,
                kind="syntax",
                message=exc.msg,
            )
        ]

    if not check_imports:
        return []

    issues: list[ValidationIssue] = []
    package_root = (
        package_root or Path(__file__).resolve().parents[1] / "src" / "tooluniverse"
    )
    for module in sorted(_tooluniverse_imports(tree)):
        if not _module_exists(module, package_root):
            issues.append(
                ValidationIssue(
                    path=block.path,
                    line=block.line,
                    kind="import",
                    message=f"module is unavailable: {module}",
                )
            )
    return issues


def validate_documentation(
    docs_dir: Path, check_imports: bool = False
) -> ValidationSummary:
    files = list(iter_document_files(docs_dir))
    blocks: list[CodeBlock] = []
    issues: list[ValidationIssue] = []

    for path in files:
        try:
            blocks.extend(extract_code_blocks(path, docs_dir))
        except UnicodeDecodeError as exc:
            issues.append(
                ValidationIssue(
                    path=path.relative_to(docs_dir).as_posix(),
                    line=1,
                    kind="encoding",
                    message=str(exc),
                )
            )

    for block in blocks:
        issues.extend(
            validate_block(
                block,
                check_imports=check_imports,
                package_root=docs_dir.parent / "src" / "tooluniverse",
            )
        )

    if not blocks:
        issues.append(
            ValidationIssue(
                path=".",
                line=1,
                kind="coverage",
                message="no Python documentation examples were discovered",
            )
        )

    return ValidationSummary(
        files_checked=len(files),
        blocks_checked=len(blocks),
        issues=tuple(issues),
    )


def _summary_dict(summary: ValidationSummary) -> dict:
    return {
        "valid": summary.valid,
        "files_checked": summary.files_checked,
        "blocks_checked": summary.blocks_checked,
        "issue_count": len(summary.issues),
        "issues": [asdict(issue) for issue in summary.issues],
    }


def _print_text(summary: ValidationSummary) -> None:
    print("ToolUniverse documentation example validation")
    print(f"Files checked: {summary.files_checked}")
    print(f"Python blocks checked: {summary.blocks_checked}")
    print(f"Issues: {len(summary.issues)}")
    for issue in summary.issues:
        rendered = f"{issue.path}:{issue.line}: {issue.kind}: {issue.message}"
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        rendered = rendered.encode(encoding, errors="backslashreplace").decode(encoding)
        print(rendered)
    print("Result: PASS" if summary.valid else "Result: FAIL")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate Python examples in RST and MyST documentation."
    )
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Documentation root to scan recursively.",
    )
    parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="text",
        dest="output_format",
    )
    parser.add_argument(
        "--check-imports",
        action="store_true",
        help="Also check ToolUniverse module paths without importing package code.",
    )
    args = parser.parse_args(argv)

    docs_dir = args.docs_dir.resolve()
    if not docs_dir.is_dir():
        parser.error(f"documentation directory does not exist: {docs_dir}")

    summary = validate_documentation(docs_dir, check_imports=args.check_imports)
    if args.output_format == "json":
        print(json.dumps(_summary_dict(summary), indent=2, sort_keys=True))
    else:
        _print_text(summary)
    return 0 if summary.valid else 1


if __name__ == "__main__":
    sys.exit(main())
