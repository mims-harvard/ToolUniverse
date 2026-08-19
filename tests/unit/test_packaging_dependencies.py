"""Regression tests for install-time dependencies."""

from pathlib import Path


def test_base_dependencies_exclude_unrelated_fitz_distribution() -> None:
    """The optional PyMuPDF import must not install the abandoned PyPI fitz."""
    project_root = Path(__file__).resolve().parents[2]
    pyproject = (project_root / "pyproject.toml").read_text()

    assert '"fitz' not in pyproject
    assert '"scipy>=1.7.0"' in pyproject
