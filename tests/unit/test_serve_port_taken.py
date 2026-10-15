"""`tu serve my_tool.py --share` must not share whatever else listens on its port.

Its startup check only connects to the port, and a connection succeeds against any program
there. Measured with an unrelated MCP service on 8080: this server failed to bind in its
thread, the check passed against the other service, and the relay shared that service's tool
-- under the scientist's server name -- to the platform.
"""

from __future__ import annotations

import socket
import textwrap
from types import SimpleNamespace

import pytest

from tooluniverse import cli


@pytest.fixture
def held_port():
    holder = socket.socket()
    holder.bind(("127.0.0.1", 0))
    holder.listen()
    yield holder.getsockname()[1]
    holder.close()


def test_a_held_port_is_refused_with_a_free_one_offered(held_port):
    with pytest.raises(RuntimeError) as caught:
        cli._require_free_port("127.0.0.1", held_port)

    message = str(caught.value)
    assert f"already using port {held_port}" in message
    assert "--port" in message


def test_a_free_port_passes():
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()

    cli._require_free_port("127.0.0.1", port)


def test_serving_a_file_stops_before_starting_anything(held_port, tmp_path, monkeypatch):
    """Drives the real entry point: nothing may start, and the relay is never reached."""
    from tooluniverse import mcp_tool_registry as registry

    tool_file = tmp_path / "my_tool.py"
    tool_file.write_text(textwrap.dedent('''
        # The registry's own name: the package-level one is shadowed in a test process
        # until the RemoteTool module rename lands (see test_remote_tool_name_clash).
        from tooluniverse.mcp_tool_registry import remote_tool

        @remote_tool
        def predict(sequence: str) -> dict:
            """Score one sequence."""
            return {}
    '''))
    started = []
    monkeypatch.setattr(registry, "_start_server_for_port", lambda port: started.append(port))
    saved = dict(registry._mcp_tool_registry)
    args = SimpleNamespace(files=[str(tool_file)], port=held_port, host="127.0.0.1", name=None,
                           workers=1, share=True, service="http://127.0.0.1:9", no_browser=True)
    try:
        with pytest.raises(RuntimeError, match="already using port"):
            cli._start_remote_tool_server(args)
    finally:
        registry._mcp_tool_registry.clear()
        registry._mcp_tool_registry.update(saved)

    assert started == []
