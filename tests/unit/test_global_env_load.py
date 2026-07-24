import os
from pathlib import Path
from tooluniverse.execute_function import _load_global_dotenv


def test_global_env_loaded_when_present(tmp_path, monkeypatch):
    monkeypatch.delenv("ZZ_GLOBAL_TEST", raising=False)
    home = tmp_path / "home"
    (home / ".tooluniverse").mkdir(parents=True)
    (home / ".tooluniverse" / ".env").write_text("ZZ_GLOBAL_TEST=from_global\n")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    _load_global_dotenv(workspace_dotenv=tmp_path / "ws" / ".env")
    assert os.environ["ZZ_GLOBAL_TEST"] == "from_global"


def test_existing_env_wins(tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / ".tooluniverse").mkdir(parents=True)
    (home / ".tooluniverse" / ".env").write_text("ZZ_GLOBAL_TEST=from_global\n")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.setenv("ZZ_GLOBAL_TEST", "from_shell")
    _load_global_dotenv(workspace_dotenv=tmp_path / "ws" / ".env")
    assert os.environ["ZZ_GLOBAL_TEST"] == "from_shell"


def test_skipped_when_workspace_is_global(tmp_path, monkeypatch):
    monkeypatch.delenv("ZZ_GLOBAL_TEST", raising=False)
    home = tmp_path / "home"
    global_env = home / ".tooluniverse" / ".env"
    global_env.parent.mkdir(parents=True)
    global_env.write_text("ZZ_GLOBAL_TEST=from_global\n")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    # workspace .env IS the global file -> helper must not double-load it here
    _load_global_dotenv(workspace_dotenv=global_env)
    assert "ZZ_GLOBAL_TEST" not in os.environ
