"""Messages name the real file a key is saved in, not "~/.tooluniverse/.env".

On Windows "~" means nothing to Notepad or cmd; anywhere, the real path is the one a person can
paste.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tooluniverse.execute_function import explain_remote_load_failure
from tooluniverse.platform_remote_tool import PlatformRemoteTool


@pytest.fixture
def home(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.delenv("TU_API_KEY", raising=False)
    monkeypatch.delenv("TOOLUNIVERSE_SERVICE_KEY", raising=False)
    return str(tmp_path / ".tooluniverse" / ".env")


def test_a_missing_key_names_the_real_file(home):
    config = {"connection_name": "alice-gpu", "auth_env": "TU_API_KEY",
              "server_url": "https://api.example/relay/abc/mcp"}

    message, _ = explain_remote_load_failure(config, "Client error '401'", {})

    assert home in message and "~/" not in message


def test_a_published_tool_names_the_real_file(home):
    tool = PlatformRemoteTool({"name": "x", "type": "PlatformRemoteTool",
                               "resource_id": "8faedc52-c800-4072-ab29-e0999cf29f74"})

    message = tool.run({})["error"]

    assert home in message and "~/" not in message
