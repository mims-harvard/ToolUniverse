"""A published tool may run as long as its owner allowed; the caller must wait that long.

Measured with `tu connect <published tool>` and `tu run`: a tool its owner configured for 300
seconds failed for the caller at 121 with "Error: timed out" -- the client's default of 120,
and a second 120-second cap on every request.
"""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from tooluniverse.platform_remote_tool import PlatformRemoteTool

KEY = "tu-sk-" + "f" * 60


def tool(base_url="https://tooluniverse-backend.onrender.com", **config):
    return PlatformRemoteTool({"name": "remote_slow", "type": "PlatformRemoteTool",
                               "resource_id": "8faedc52-c800-4072-ab29-e0999cf29f74",
                               "base_url": base_url, **config})


def test_the_default_outlasts_the_platforms_own_cap():
    assert tool().timeout > 15 * 60


def test_a_long_call_gets_the_whole_deadline(monkeypatch):
    seen = {}

    class Opener:
        def open(self, request, timeout):
            seen["timeout"] = timeout
            raise TimeoutError("timed out")

    t = tool(timeout=300)
    monkeypatch.setattr(t, "_opener", Opener())
    monkeypatch.setenv("TU_API_KEY", KEY)

    t.run({"seconds": 150})

    assert seen["timeout"] > 290


@pytest.fixture
def slow_platform():
    class Platform(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            time.sleep(3)
            body = json.dumps({"result": "late"}).encode()
            try:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except OSError:
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Platform)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def test_a_timeout_says_the_call_may_still_be_running(slow_platform, monkeypatch):
    monkeypatch.setenv("TU_API_KEY", KEY)

    result = tool(base_url=slow_platform, timeout=1).run({})

    assert result["status"] == "error"
    assert "may still be running" in result["error"]
