"""Four leftovers from the 2026-10-03 sweep triage, each a different thing.

  mpd                a search with no hits reported as an API error
  expression_anova   examples that need a file the caller supplies
  the skip label     one sentence covering two different reasons
  encori             an HTML fragment echoed as the upstream's complaint

Also records STITCH's retired interaction endpoints, where the apparent
replacement is worse than the failure.
"""

import importlib.util
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "src" / "tooluniverse" / "data"


def _sweep():
    spec = importlib.util.spec_from_file_location(
        "test_all_tools_labels", ROOT / "scripts" / "test_all_tools.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Resp:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise AssertionError("raise_for_status should not be reached on a 404")


def test_an_encode_search_with_no_hits_is_a_result_not_an_error(monkeypatch):
    """DBA/2J has no ENCODE data and ENCODE says so with a 404.

    The tool's own comment names that strain as having none, and Ex 3 of its
    examples uses it, so the example could never pass.
    """
    from tooluniverse.mpd_tool import MPDRESTTool

    tool = MPDRESTTool(
        {"name": "MPD_get_phenotype_data", "description": "t", "parameter": {}}
    )
    empty = {
        "@context": "/terms/",
        "@graph": [],
        "total": 0,
        "notification": "No results found",
    }
    monkeypatch.setattr(tool.session, "get", lambda *a, **k: _Resp(404, empty))

    result = tool.run({"strain": "DBA/2J", "limit": 5})

    assert result["status"] == "success"
    # ENCODE's own body is handed back, so it stays inside the declared schema.
    assert result["data"]["@context"] == "/terms/"
    assert result["data"]["@graph"] == []
    assert "no experiment mentioning" in result["query_info"]["note"]


def test_a_404_without_a_json_body_still_succeeds(monkeypatch):
    from tooluniverse.mpd_tool import MPDRESTTool

    tool = MPDRESTTool(
        {"name": "MPD_get_phenotype_data", "description": "t", "parameter": {}}
    )
    monkeypatch.setattr(tool.session, "get", lambda *a, **k: _Resp(404, None))

    result = tool.run({"strain": "DBA/2J"})

    assert result["status"] == "success"
    assert result["data"]["@graph"] == []


def test_expression_anova_declares_that_it_needs_a_local_file():
    """Its examples point at /tmp/expr_anova_counts.csv, which no run ships."""
    tools = json.loads((DATA / "expression_anova_tools.json").read_text("utf-8"))

    for tool in tools:
        assert tool.get("requires_local_input") is True, tool["name"]
        joined = json.dumps(tool.get("test_examples"))
        assert "_file" in joined, "if the examples stop needing a file, undeclare it"


def test_the_skip_label_says_which_reason_applies():
    """One sentence used to cover both, and it named the wrong one."""
    sweep = _sweep()

    local = sweep.normalize_result(
        {"skipped": 1, "skipped_local_input": 1, "tests_run": 0}
    )
    credential = sweep.normalize_result({"skipped": 2, "tests_run": 0})
    both = sweep.normalize_result(
        {"skipped": 3, "skipped_local_input": 1, "tests_run": 0}
    )

    assert "input file the caller supplies" in sweep._format_result_status(local)
    assert "credential" not in sweep._format_result_status(local)
    assert "credential" in sweep._format_result_status(credential)

    mixed = sweep._format_result_status(both)
    assert "1 need an input file" in mixed
    assert "2 need a credential" in mixed


def test_the_runner_reports_the_local_input_count():
    source = (ROOT / "scripts" / "test_new_tools.py").read_text("utf-8")

    assert "skipped_local_input" in source
    assert "Skipped local input:" in source


def _encori_body(monkeypatch, body):
    import tooluniverse.encori_tool as encori

    class _TextResp:
        status_code = 200
        text = body

    tool = encori.ENCORITool(
        {"name": "ENCORI_get_RBP_targets", "description": "t", "parameter": {}}
    )
    monkeypatch.setattr(encori.requests, "get", lambda *a, **k: _TextResp())
    return tool._fetch_tsv("RBPTarget/", {})


def test_encori_describes_an_html_response_rather_than_echoing_it(monkeypatch):
    """"ENCORI rejected the query: <br />" told a caller nothing."""
    parsed = _encori_body(
        monkeypatch, "<br />\n<b>Warning</b>: something went wrong on our side\n"
    )

    assert "error" in parsed
    assert "HTML page" in parsed["error"]
    assert "<br />" not in parsed["error"]
    assert "something went wrong" in parsed["error"]


def test_a_genuine_encori_message_is_still_passed_through(monkeypatch):
    """Their real complaints are plain sentences and should survive verbatim."""
    parsed = _encori_body(
        monkeypatch, 'The "RNA" parameter haven\'t been set correctly!\n'
    )

    assert parsed["error"] == (
        'ENCORI rejected the query: The "RNA" parameter haven\'t been set correctly!'
    )


def test_stitch_is_recorded_with_why_string_is_not_a_substitute():
    entry = json.loads(
        (DATA / "broken_apis" / "stitch_interactions.json").read_text("utf-8")
    )

    assert entry["retry_count"] >= 3
    assert entry["retry_after"]
    # The point of the entry: the obvious replacement answers a different
    # question. STRING has no chemicals and matched aspirin to a gene.
    assert "SLC17A4" in entry["workaround"]
    assert "STITCH_resolve_identifier" in entry["retry_notes"]
    assert entry["affected_tools"] == [
        "STITCH_get_chemical_protein_interactions",
        "STITCH_get_interaction_partners",
    ]


def test_the_stitch_tools_stay_registered():
    """A clear error about a dead upstream beats the tool vanishing."""
    names = {
        t["name"] for t in json.loads((DATA / "stitch_tools.json").read_text("utf-8"))
    }

    assert "STITCH_resolve_identifier" in names
    assert "STITCH_get_chemical_protein_interactions" in names
