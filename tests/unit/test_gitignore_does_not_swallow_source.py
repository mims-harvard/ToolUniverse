"""`.gitignore` must hide credentials without hiding source files.

The secrets section carries `*_api_key*` and `*_token*`, which match any path
segment. That silently made `git add` refuse
`src/tooluniverse/tools/ReactomeAnalysis_token_result.py` -- a generated tool
wrapper. Had it ever been cleaned and rebuilt it would not have come back,
and the tool would have vanished from `tooluniverse.tools`, which is exactly
how 119 tools went missing before.

There is no secret-scanning hook in this repo, so the broad patterns stay as
the safety net and only code and prose extensions are re-included.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parents[2]

MUST_BE_TRACKABLE = [
    "src/tooluniverse/tools/ReactomeAnalysis_token_result.py",
    "src/tooluniverse/token_helper.py",
    "tests/unit/test_some_token_behaviour.py",
    "docs/api_token.md",
    "docs/guide/api_key_setup.rst",
    "scripts/gen_api_key_catalog.py",
]

MUST_STAY_IGNORED = [
    ".env",
    "credentials.json",
    "my_token.txt",
    "gh_token.json",
    "secrets_token.yaml",
    "foo_api_key.json",
    "config_api_key.env",
    "access_token",
]


def _is_ignored(path: str) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "-q", path],
        cwd=REPO,
        capture_output=True,
    )
    return result.returncode == 0


@pytest.fixture(autouse=True)
def _require_git():
    if shutil.which("git") is None or not (REPO / ".git").exists():
        pytest.skip("git or the working tree is unavailable")


@pytest.mark.parametrize("path", MUST_BE_TRACKABLE)
def test_source_and_docs_are_not_ignored(path):
    assert not _is_ignored(path), (
        f"{path} is ignored, so `git add` would refuse it silently. "
        "Re-include its extension in the secrets section of .gitignore."
    )


@pytest.mark.parametrize("path", MUST_STAY_IGNORED)
def test_credential_shaped_files_stay_ignored(path):
    assert _is_ignored(path), (
        f"{path} is no longer ignored; the secrets guard has been weakened."
    )
