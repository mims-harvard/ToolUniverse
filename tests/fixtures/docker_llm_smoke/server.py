"""Dependency-free OpenAI-compatible server used only by the Docker smoke test."""

from __future__ import annotations

import hashlib
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SERVICE_ID = "tooluniverse-docker-llm-smoke"
MODEL = "fixture-evidence-synthesizer"
MAX_REQUEST_BYTES = 65_536


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path != "/health":
            self._json(404, {"error": "not found"})
            return
        self._json(200, {"status": "ok", "service_id": SERVICE_ID, "model": MODEL})

    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions":
            self._json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._json(400, {"error": "invalid content length"})
            return
        if not 1 <= length <= MAX_REQUEST_BYTES:
            self._json(413, {"error": "request too large"})
            return
        try:
            payload = json.loads(self.rfile.read(length))
            messages = payload["messages"]
            prompt = messages[0]["content"]
            if payload["model"] != MODEL or not isinstance(prompt, str):
                raise ValueError
        except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError):
            self._json(400, {"error": "invalid inference request"})
            return
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        words = len(re.findall(r"\b[\w'-]+\b", prompt))
        sections = len(re.findall(r"(?m)^## ", prompt))
        content = (
            f"service_id={SERVICE_ID}; prompt_sha256={prompt_hash}; "
            f"word_count={words}; evidence_sections={sections}; "
            "contract=openai-chat-completions"
        )
        self._json(
            200,
            {
                "id": f"smoke-{prompt_hash[:12]}",
                "object": "chat.completion",
                "model": MODEL,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": words,
                    "completion_tokens": len(content.split()),
                    "total_tokens": words + len(content.split()),
                },
            },
        )

    def log_message(self, format: str, *args) -> None:
        return


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
