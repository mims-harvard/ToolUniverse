import importlib.util
import os
import stat
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "keys_env", REPO / "plugin" / "scripts" / "keys_env.py"
)
ke = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ke)


def test_read_env_ignores_comments(tmp_path):
    p = tmp_path / ".env"
    p.write_text("# comment\nA=1\nB = two \n\n")
    assert ke.read_env(p) == {"A": "1", "B": "two"}


def test_read_env_missing_file(tmp_path):
    assert ke.read_env(tmp_path / "nope.env") == {}


def test_mask():
    assert ke.mask("") == ""
    assert ke.mask("abcd") == "****"
    assert ke.mask("sk-12345678") == "*******5678"


def test_merge_sets_overwrites_keeps_and_removes(tmp_path):
    p = tmp_path / "sub" / ".env"
    p.parent.mkdir()
    p.write_text("# header\nOLD=keep\nA=old\nB=bye\n")
    ke.merge_env(p, {"A": "new", "B": "", "C": "fresh"})
    result = ke.read_env(p)
    assert result == {"OLD": "keep", "A": "new", "C": "fresh"}  # B removed
    assert "# header" in p.read_text()  # comment preserved
    assert stat.S_IMODE(os.stat(p).st_mode) == 0o600


def test_merge_creates_file(tmp_path):
    p = tmp_path / "a" / "b" / ".env"
    ke.merge_env(p, {"X": "1"})
    assert ke.read_env(p) == {"X": "1"}
