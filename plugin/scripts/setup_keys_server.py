#!/usr/bin/env python3
"""Localhost form for entering ToolUniverse API keys, saved to a .env file.

Usage: python setup_keys_server.py --target <path-to-.env> [--catalog <path>]
Binds 127.0.0.1 on a random port, opens the browser, writes on submit, exits.
"""
from __future__ import annotations

import argparse
import html
import json
import secrets
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import keys_env  # noqa: E402


def find_catalog(explicit) -> Path:
    """Locate api_keys_catalog.json: --catalog, then sibling, then repo."""
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    candidates.append(Path(__file__).resolve().parent / "api_keys_catalog.json")
    candidates.append(
        Path(__file__).resolve().parents[2]
        / "src" / "tooluniverse" / "data" / "api_keys_catalog.json"
    )
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError("api_keys_catalog.json not found; pass --catalog")


def check_token(expected, given) -> bool:
    return bool(given) and secrets.compare_digest(str(expected), str(given))


def compute_updates(form: dict, names: list) -> dict:
    """Build the .env update dict from a parsed POST form.

    Non-empty value -> set. clear__<NAME> present -> remove (""). Blank -> skip.
    """
    updates: dict = {}
    for name in names:
        if f"clear__{name}" in form:
            updates[name] = ""
            continue
        val = (form.get(name, [""])[0] or "").strip()
        if val:
            updates[name] = val
    return updates


def _row(entry: dict, existing: dict) -> str:
    name = entry["name"]
    cur = existing.get(name, "")
    placeholder = keys_env.mask(cur) if cur else "not set"
    clear = (
        f'<label class="clr"><input type="checkbox" name="clear__{name}"> clear</label>'
        if cur else ""
    )
    return f"""
      <div class="row">
        <div class="meta">
          <code>{html.escape(name)}</code>
          <a href="{html.escape(entry['register_url'])}" target="_blank">register</a>
          <p>{html.escape(entry['description'])}</p>
        </div>
        <div class="inp">
          <input type="password" name="{name}" placeholder="{html.escape(placeholder)}" autocomplete="off">
          {clear}
        </div>
      </div>"""


def render_form(catalog: list, existing: dict, token: str) -> str:
    def section(title, items):
        if not items:
            return ""
        return f"<h2>{html.escape(title)}</h2>" + "".join(_row(e, existing) for e in items)

    secrets_ = [e for e in catalog if e["type"] == "secret"]
    required = [e for e in secrets_ if e["requirement"] == "required"]
    optional = [e for e in secrets_ if e["requirement"] == "optional"]
    endpoints = [e for e in catalog if e["type"] == "endpoint"]
    body = (
        section("Required keys", required)
        + section("Optional keys", optional)
        + section("Service Endpoints (advanced)", endpoints)
    )
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>ToolUniverse API Keys</title><style>
body{{font:15px/1.5 system-ui,sans-serif;max-width:760px;margin:2rem auto;padding:0 1rem;color:#1a1a1a}}
h1{{font-size:1.4rem}} h2{{margin-top:2rem;border-bottom:1px solid #ddd;padding-bottom:.3rem}}
.row{{display:flex;gap:1rem;padding:.7rem 0;border-bottom:1px solid #f0f0f0}}
.meta{{flex:1}} .meta p{{margin:.2rem 0 0;color:#666;font-size:.85rem}}
.meta a{{font-size:.8rem;margin-left:.5rem}} .inp{{flex:1}}
input[type=password]{{width:100%;padding:.45rem;border:1px solid #ccc;border-radius:6px}}
.clr{{font-size:.8rem;color:#a00}} button{{margin-top:1.5rem;padding:.6rem 1.4rem;
font-size:1rem;background:#0b6;color:#fff;border:0;border-radius:8px;cursor:pointer}}
.note{{color:#666;font-size:.85rem}}</style></head><body>
<h1>ToolUniverse API Keys</h1>
<p class="note">Leave a field blank to keep its current value. Values are saved to your .env and never shown again.</p>
<form method="post">
<input type="hidden" name="token" value="{html.escape(token)}">
{body}
<button type="submit">Save keys</button>
</form></body></html>"""


def _success_page(count: int, target: Path) -> str:
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Saved</title>
<style>body{{font:16px system-ui,sans-serif;max-width:600px;margin:4rem auto;text-align:center}}</style>
</head><body><h1>Saved {count} key(s)</h1>
<p>Written to <code>{html.escape(str(target))}</code>. You can close this tab.</p>
<p>Restart the ToolUniverse MCP server / CLI to pick up the new keys.</p>
</body></html>"""


def build_server(catalog: list, target: Path, token: str):
    names = [e["name"] for e in catalog]
    state = {"saved": 0}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # silence
            pass

        def _send(self, code, body):
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

        def do_GET(self):
            q = parse_qs(urlparse(self.path).query)
            if not check_token(token, (q.get("token") or [None])[0]):
                self._send(403, "<h1>Forbidden</h1>")
                return
            existing = keys_env.read_env(target)
            self._send(200, render_form(catalog, existing, token))

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            form = parse_qs(self.rfile.read(length).decode("utf-8"))
            if not check_token(token, (form.get("token") or [None])[0]):
                self._send(403, "<h1>Forbidden</h1>")
                return
            updates = compute_updates(form, names)
            keys_env.merge_env(target, updates)
            state["saved"] = len([v for v in updates.values() if v != ""])
            self._send(200, _success_page(state["saved"], target))
            threading.Thread(target=self.server.shutdown, daemon=True).start()

    return HTTPServer(("127.0.0.1", 0), Handler), state


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, help="Path to the .env file to write")
    ap.add_argument("--catalog", default=None, help="Path to api_keys_catalog.json")
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args(argv)

    catalog = json.loads(find_catalog(args.catalog).read_text())
    token = secrets.token_urlsafe(16)
    target = Path(args.target).expanduser()
    server, state = build_server(catalog, target, token)
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}/?token={token}"
    print(f"Open this URL to enter your API keys:\n  {url}", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    server.serve_forever()
    print(f"Saved {state['saved']} key(s) to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
