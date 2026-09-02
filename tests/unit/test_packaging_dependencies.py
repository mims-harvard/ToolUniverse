"""
Guards on the declared runtime dependencies and on release version sync.

Background: the PDF backend was declared as ``fitz>=0.0.1.dev2``. ``fitz`` is
the *import* name of PyMuPDF, not its distribution name -- the PyPI project
named ``fitz`` is an unrelated placeholder that has since been deactivated and
now only publishes a 0.0.0 sdist that raises on build:

    ERROR: Package 'fitz' has been deactivated and cannot be installed.
    Please install 'pymupdf' instead.

Once that happened the constraint became permanently unsatisfiable. Resolvers
backtracked to the newest release without it (tooluniverse 0.2.0), which does
not ship the ``tooluniverse`` console script, so the MCP server died at startup
with "An executable named `tooluniverse` is not provided by package
`tooluniverse`". The MCPB bundle re-resolves on every launch, so working
installs broke without any local change.

These tests reject the wrong distribution, keep PyMuPDF behind its explicit
license-sensitive extra, keep the bundle's default dependency list in step with
the root one, and keep every version marker moving together so a fix actually
reaches PyPI.
"""

import json
import re
from importlib.metadata import packages_distributions
from pathlib import Path

import pytest

tomllib = pytest.importorskip(
    "tomllib", reason="TOML parsing requires Python 3.11+ (tomllib)"
)

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT_PYPROJECT = REPO_ROOT / "pyproject.toml"
MCPB_PYPROJECT = REPO_ROOT / "mcpb" / "pyproject.toml"
MCPB_MANIFEST = REPO_ROOT / "mcpb" / "manifest.json"
UV_LOCK = REPO_ROOT / "uv.lock"
SRC_ROOT = REPO_ROOT / "src" / "tooluniverse"

# PyPI projects that must never appear in dependencies, mapped to what to use
# instead. These are names that look like the right dependency but resolve to an
# unrelated or deactivated project.
FORBIDDEN_DISTRIBUTIONS = {
    "fitz": "pymupdf",
}

# Dependencies the bundle declares on purpose that the root list leaves to an
# extra. The bundle is a sealed Claude Desktop runtime: the end user cannot
# install an extra into it, so anything optional upstream must be unconditional
# here or the feature is simply unreachable in Desktop.
KNOWN_MCPB_ADDITIONS = {
    # Optional root extras `openai` / `gemini` (see issue #526). They stay
    # unconditional in the bundle so the OpenAI and Gemini clients keep working.
    "openai",
    "google-genai",
}


def _load_pyproject(pyproject_path):
    with open(pyproject_path, "rb") as fh:
        return tomllib.load(fh)["project"]


def _load_dependencies(pyproject_path):
    return _load_pyproject(pyproject_path)["dependencies"]


def _distribution_name(requirement):
    """Extract the normalized distribution name from a PEP 508 requirement."""
    name = re.split(r"[<>=!~\[;\s]", requirement.strip(), maxsplit=1)[0]
    return name.lower().replace("_", "-")


def _names(pyproject_path):
    return {_distribution_name(r) for r in _load_dependencies(pyproject_path)}


def _requirements_by_name(pyproject_path):
    return {
        _distribution_name(requirement): requirement
        for requirement in _load_dependencies(pyproject_path)
    }


def _project_version(pyproject_path):
    with open(pyproject_path, "rb") as fh:
        return tomllib.load(fh)["project"]["version"]


@pytest.mark.parametrize("pyproject", [ROOT_PYPROJECT, MCPB_PYPROJECT])
def test_no_forbidden_distributions(pyproject):
    """No dependency may name a deactivated or wrong-project distribution."""
    declared = _names(pyproject)
    for forbidden, replacement in FORBIDDEN_DISTRIBUTIONS.items():
        assert forbidden not in declared, (
            f"{pyproject.relative_to(REPO_ROOT)} depends on '{forbidden}', which is "
            f"not installable from PyPI. Use '{replacement}' instead."
        )


def test_pymupdf_is_an_explicit_root_extra_only():
    """Do not impose PyMuPDF's AGPL/commercial terms on default installs."""
    root = _load_pyproject(ROOT_PYPROJECT)
    root_default = {_distribution_name(r) for r in root["dependencies"]}
    mcpb_default = _names(MCPB_PYPROJECT)
    pdf_extra = {
        _distribution_name(r) for r in root["optional-dependencies"].get("pdf", [])
    }
    all_extra = " ".join(root["optional-dependencies"]["all"]).lower()

    assert "pymupdf" not in root_default
    assert "pymupdf" not in mcpb_default
    assert pdf_extra == {"pymupdf"}
    assert "pdf" not in all_extra


def test_mcpb_dependencies_mirror_root():
    """The bundle list is documented as a mirror of the root list."""
    root_requirements = _requirements_by_name(ROOT_PYPROJECT)
    mcpb_requirements = _requirements_by_name(MCPB_PYPROJECT)
    root = set(root_requirements)
    mcpb = set(mcpb_requirements)

    missing = root - mcpb
    assert not missing, (
        f"mcpb/pyproject.toml is missing dependencies present in the root "
        f"pyproject.toml: {sorted(missing)}. Add them to the bundle dependency "
        f"list."
    )

    extra = mcpb - root - KNOWN_MCPB_ADDITIONS
    assert not extra, (
        f"mcpb/pyproject.toml declares dependencies absent from the root "
        f"pyproject.toml: {sorted(extra)}. Add them to the root list, or record "
        f"them in KNOWN_MCPB_ADDITIONS with a reason."
    )

    # A bundle-only dependency must still track the constraint of the root
    # extra it mirrors, so the two cannot drift apart silently.
    root_extra_requirements = {
        _distribution_name(requirement): requirement
        for requirements in _load_pyproject(ROOT_PYPROJECT)[
            "optional-dependencies"
        ].values()
        for requirement in requirements
    }
    drifted = {
        name: (root_extra_requirements[name], mcpb_requirements[name])
        for name in KNOWN_MCPB_ADDITIONS & mcpb
        if name in root_extra_requirements
        and root_extra_requirements[name] != mcpb_requirements[name]
    }
    assert not drifted, (
        "mcpb/pyproject.toml pins a bundle-only dependency differently from the "
        f"root extra that declares it: {drifted}."
    )

    mismatched = {
        name: (root_requirements[name], mcpb_requirements[name])
        for name in root & mcpb
        if root_requirements[name] != mcpb_requirements[name]
    }
    assert not mismatched, (
        "mcpb/pyproject.toml has dependency constraints that differ from the "
        f"root pyproject.toml: {mismatched}."
    )


def _markitdown_requirements():
    """Every declared markitdown requirement, keyed by the file that declares it."""
    found = {}
    for pyproject in (ROOT_PYPROJECT, MCPB_PYPROJECT):
        for requirement in _load_dependencies(pyproject):
            if _distribution_name(requirement) == "markitdown":
                found.setdefault(pyproject, []).append(requirement)
    return found


def test_markitdown_extras_do_not_cap_supported_python():
    """MarkItDown must be requested by converter extra, never through `all`.

    `markitdown[all]` pins ``youtube-transcript-api~=1.0.0``, and every 1.0.x
    release of that project declares ``Requires-Python <3.14``. Because the
    requirement is unconditional, that cap propagated to tooluniverse and made
    it uninstallable on Python 3.14 without a downstream override (issue #527).
    MarkItDown's own ``youtube-transcription`` extra leaves the dependency
    unpinned, so 1.2.3+ (``Requires-Python <3.15``) resolves instead.

    Naming the extras also keeps installs on current MarkItDown: since 0.1.6 the
    `all` extra requires ``azure-ai-contentunderstanding>=1.2.0b1``, which has no
    stable release, so a default resolver silently backtracks `markitdown[all]`
    to 0.1.5.
    """
    declared = _markitdown_requirements()
    assert declared, "no markitdown requirement is declared any more"

    for pyproject, requirements in declared.items():
        location = pyproject.relative_to(REPO_ROOT)
        for requirement in requirements:
            extras = re.search(r"\[([^\]]*)\]", requirement)
            assert extras, (
                f"{location}: markitdown must request converter extras: {requirement}"
            )
            names = {extra.strip() for extra in extras.group(1).split(",")}

            assert "all" not in names, (
                f"{location} requests `markitdown[all]`, which pins "
                f"youtube-transcript-api~=1.0.0 (Requires-Python <3.14) and caps "
                f"the Python versions tooluniverse can be installed on. List the "
                f"converter extras individually instead (issue #527)."
            )
            assert "youtube-transcription" in names, (
                f"{location} drops MarkItDown's `youtube-transcription` extra, so "
                f"YouTube transcription silently stops working. Keep the extra: it "
                f"leaves youtube-transcript-api unpinned, which is what lifts the "
                f"Python cap."
            )
            assert "az-content-understanding" not in names, (
                f"{location} requests `az-content-understanding`, whose "
                f"azure-ai-contentunderstanding>=1.2.0b1 dependency has no stable "
                f"release; the requirement becomes unresolvable. Add it back only "
                f"once that project ships a final version."
            )


def test_markitdown_requirement_is_unconditional():
    """One requirement, no environment markers, in both dependency lists.

    The Python-version split that worked around issue #527 left the bundle with
    a dead branch (it caps itself at Python <3.14) and hid a real drift risk:
    `test_mcpb_dependencies_mirror_root` keys requirements by distribution name,
    so only the last of two `markitdown` lines was ever compared.
    """
    for pyproject, requirements in _markitdown_requirements().items():
        location = pyproject.relative_to(REPO_ROOT)
        assert len(requirements) == 1, (
            f"{location} declares markitdown {len(requirements)} times: "
            f"{requirements}. A single unconditional requirement now covers every "
            f"supported Python version."
        )
        assert ";" not in requirements[0], (
            f"{location} still guards markitdown with an environment marker: "
            f"{requirements[0]}."
        )


def test_release_versions_move_together():
    """A release must bump the package, the bundle, the manifest, and the lock.

    publish-pypi.yml gates on the root pyproject version being newer than the
    latest release on PyPI, so a fix that lands without a bump never ships. The
    lockfile records the project's own version too; leaving it behind breaks
    `uv sync --locked`.
    """
    root_version = _project_version(ROOT_PYPROJECT)
    mcpb_version = _project_version(MCPB_PYPROJECT)
    manifest_version = json.loads(MCPB_MANIFEST.read_text())["version"]

    assert root_version == mcpb_version == manifest_version, (
        f"Version drift: pyproject.toml={root_version}, "
        f"mcpb/pyproject.toml={mcpb_version}, mcpb/manifest.json={manifest_version}"
    )

    lock_match = re.search(
        r'\[\[package\]\]\nname = "tooluniverse"\nversion = "([^"]+)"',
        UV_LOCK.read_text(),
    )
    assert lock_match, "Could not find the tooluniverse package entry in uv.lock"
    assert lock_match.group(1) == root_version, (
        f"uv.lock records tooluniverse {lock_match.group(1)} but pyproject.toml "
        f"declares {root_version}; run `uv lock` after bumping the version."
    )


def test_pymupdf_module_is_provided_by_pymupdf():
    """Confirm the `pymupdf` module comes from the PyMuPDF distribution."""
    pymupdf = pytest.importorskip("pymupdf", reason="PyMuPDF is not installed")
    assert hasattr(pymupdf, "open"), "`import pymupdf` did not provide PyMuPDF's API."

    providers = packages_distributions().get("pymupdf", [])
    assert [p.lower() for p in providers] == ["pymupdf"], (
        f"The `pymupdf` module is provided by {providers or 'an unknown distribution'}, "
        "expected ['pymupdf']."
    )


def test_sources_use_canonical_pymupdf_import():
    """PDF consumers must import `pymupdf`, not PyMuPDF's deprecated `fitz` shim.

    PyMuPDF still ships a `fitz` alias, but importing it emits a deprecation
    warning and it is slated for removal. A bare `import fitz` would also start
    resolving against the placeholder distribution again if it ever returns.
    """
    offenders = []
    for path in SRC_ROOT.rglob("*.py"):
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1
        ):
            stripped = line.strip()
            if re.match(r"^(import fitz\b|from fitz\b)", stripped):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{lineno}: {stripped}")

    assert not offenders, (
        "Use `import pymupdf as fitz` instead of the deprecated `fitz` alias:\n"
        + "\n".join(offenders)
    )
