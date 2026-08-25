"""`execute_query()` (shared by every GraphQLTool subclass, including
OpenTargets and OpenNeuro) printed the raw GraphQL `errors` array straight to
stdout on failure. Some APIs embed a full stack trace with internal server
file paths in `extensions.stacktrace` (confirmed live via
OpenNeuro_get_dataset with a nonexistent dataset ID, which surfaced
'/srv/packages/openneuro-server/dist/graphql/permissions.js:92:15' etc. in
the CLI output) -- an internal-implementation leak, not a useful diagnostic,
and it happened even though the tool's actual returned `error` field stayed
clean ("No data returned from API"). Fixed by logging only the sanitized
`message` text via `logging.debug` (invisible by default) instead of
`print()`-ing the raw error objects.
"""

import logging

import pytest

from tooluniverse.graphql_tool import execute_query

pytestmark = pytest.mark.unit


class _Resp:
    ok = True

    def __init__(self, body):
        self._body = body

    def json(self):
        return self._body


def test_graphql_errors_do_not_leak_to_stdout(monkeypatch, capsys, caplog):
    body = {
        "errors": [
            {
                "message": "Dataset ds999999 does not exist.",
                "extensions": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "stacktrace": [
                        "Error: Dataset ds999999 does not exist.",
                        "    at checkDatasetExists "
                        "(/srv/packages/openneuro-server/dist/graphql/permissions.js:92:15)",
                    ],
                },
            }
        ]
    }
    monkeypatch.setattr(
        "tooluniverse.graphql_tool.requests.post", lambda *a, **k: _Resp(body)
    )

    with caplog.at_level(logging.DEBUG, logger="tooluniverse.graphql_tool"):
        result = execute_query("https://example.org/graphql", "query { x }")

    assert result is None
    captured = capsys.readouterr()
    # The internal server file path must not appear anywhere in stdout/stderr.
    assert "openneuro-server" not in captured.out
    assert "openneuro-server" not in captured.err
    assert "stacktrace" not in captured.out
    # The sanitized message is still available for debugging, just not printed.
    assert any("Dataset ds999999 does not exist." in r.message for r in caplog.records)
