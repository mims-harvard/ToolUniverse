"""PubMLST tools: database and scheme lists, sequence-type profiles and
sequence typing. HTTP is faked with responses recorded from
rest.pubmlst.org on 2026-11-18 (tests/fixtures/pubmlst/README.md)."""

import json
from pathlib import Path

import pytest
import requests

from tooluniverse import pubmlst_tool as P

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "pubmlst"
CONFIGS = {
    c["name"]: c
    for c in json.loads(
        (ROOT / "src" / "tooluniverse" / "data" / "pubmlst_tools.json").read_text()
    )
}


def _load(name):
    return json.loads((FIXTURES / name).read_text())


class _Response:
    def __init__(self, body, status=200):
        self.body, self.status_code = body, status

    def json(self):
        if isinstance(self.body, Exception):
            raise self.body
        return self.body


@pytest.fixture
def http(monkeypatch):
    """Serve recorded bodies by URL suffix; record every call."""
    routes = {}
    calls = []

    def fake(method):
        def call(url, json=None, timeout=None):
            calls.append((method, url, json))
            path = url.replace(P.PUBMLST_BASE_URL + "/", "")
            if (method, path) not in routes:
                raise AssertionError(f"unexpected {method} {path}")
            body, status = routes[(method, path)]
            return _Response(body, status)

        return call

    monkeypatch.setattr(P.requests, "get", fake("GET"))
    monkeypatch.setattr(P.requests, "post", fake("POST"))

    def route(method, path, body, status=200):
        routes[(method, path)] = (body, status)

    route.calls = calls
    return route


def _run(name, arguments):
    return P.PubMLSTTool(CONFIGS[name]).run(arguments)


def test_every_tool_names_its_operation():
    assert set(CONFIGS) == {
        "PubMLST_list_databases",
        "PubMLST_list_schemes",
        "PubMLST_get_profile",
        "PubMLST_type_sequence",
    }
    for config in CONFIGS.values():
        assert config["type"] == "PubMLSTTool"
        assert config["name"].endswith(config["fields"]["operation"])


def test_list_databases_filters_and_names_the_seqdef_database(http):
    http("GET", "db", _load("db_list.json"))
    result = _run("PubMLST_list_databases", {"query": "Neisseria"})
    assert result["status"] == "success"
    assert [row["group"] for row in result["data"]] == ["neisseria"]
    row = result["data"][0]
    assert row["seqdef_database"] == "pubmlst_neisseria_seqdef"
    assert row["isolates_database"] == "pubmlst_neisseria_isolates"
    assert result["metadata"]["total_groups"] == 4


def test_list_databases_skips_kiosk_copies_and_keeps_the_login_note(http):
    http("GET", "db", _load("db_list.json"))
    result = _run("PubMLST_list_databases", {"query": "ribosomal"})
    row = result["data"][0]
    assert row["seqdef_database"] == "pubmlst_rmlst_seqdef"
    assert "Authenticated access only" in row["long_description"]
    assert len(row["databases"]) == 3


def test_list_databases_without_query_returns_every_group(http):
    http("GET", "db", _load("db_list.json"))
    assert len(_run("PubMLST_list_databases", {})["data"]) == 4


def test_list_schemes_resolves_a_group_name(http):
    http("GET", "db", _load("db_list.json"))
    http("GET", "db/pubmlst_neisseria_seqdef/schemes", _load("neisseria_schemes.json"))
    result = _run("PubMLST_list_schemes", {"database": "neisseria"})
    assert result["status"] == "success"
    assert {"scheme_id": 1, "description": "MLST"} in result["data"]
    assert all(isinstance(row["scheme_id"], int) for row in result["data"])
    assert result["metadata"]["database"] == "pubmlst_neisseria_seqdef"
    assert result["metadata"]["total_schemes"] == 93


def test_list_schemes_query_and_full_name_skip_the_lookup(http):
    http("GET", "db/pubmlst_neisseria_seqdef/schemes", _load("neisseria_schemes.json"))
    result = _run(
        "PubMLST_list_schemes",
        {"database": "pubmlst_neisseria_seqdef", "query": "cgmlst"},
    )
    assert [row["description"] for row in result["data"]] == [
        "N. meningitidis cgMLST v3"
    ]
    assert [c[1].rsplit("/", 1)[-1] for c in http.calls] == ["schemes"]


def test_unknown_group_is_an_error_that_points_to_list_databases(http):
    http("GET", "db", _load("db_list.json"))
    result = _run("PubMLST_list_schemes", {"database": "nope"})
    assert result["status"] == "error"
    assert "PubMLST_list_databases" in result["error"]


def test_unknown_database_reports_pubmlst_message(http):
    http("GET", "db/nope_seqdef/schemes", _load("database_404.json"), 404)
    result = _run("PubMLST_list_schemes", {"database": "nope_seqdef"})
    assert result == {
        "status": "error",
        "error": "PubMLST returned HTTP 404: Database nope_seqdef has not been defined",
    }


def test_get_profile_turns_allele_links_into_numbers(http):
    http(
        "GET",
        "db/pubmlst_neisseria_seqdef/schemes/1/profiles/11",
        _load("neisseria_st11_profile.json"),
    )
    result = _run(
        "PubMLST_get_profile",
        {"database": "pubmlst_neisseria_seqdef", "scheme_id": 1, "st": "ST-11"},
    )
    assert result["status"] == "success"
    data = result["data"]
    assert data["ST"] == 11
    assert data["clonal_complex"] == "ST-11 complex"
    assert data["alleles"] == {
        "abcZ": "2",
        "adk": "3",
        "aroE": "4",
        "fumC": "3",
        "gdh": "8",
        "pdhC": "4",
        "pgm": "6",
    }
    assert "curator" not in data and "sender" not in data
    assert result["metadata"]["locus_count"] == 7


def test_get_profile_unknown_st_is_a_404_error(http):
    http(
        "GET",
        "db/pubmlst_neisseria_seqdef/schemes/1/profiles/999999",
        _load("profile_404.json"),
        404,
    )
    result = _run(
        "PubMLST_get_profile",
        {"database": "pubmlst_neisseria_seqdef", "st": 999999},
    )
    assert result == {
        "status": "error",
        "error": "PubMLST returned HTTP 404: Profile ST-999999 does not exist.",
    }


def test_get_profile_after_the_public_cutoff_quotes_the_notice(http):
    """Records newer than the anonymous cutoff answer 403, not 404."""
    http(
        "GET",
        "db/pubmlst_neisseria_seqdef/schemes/1/profiles/20000",
        _load("profile_403_after_cutoff.json"),
        403,
    )
    result = _run(
        "PubMLST_get_profile",
        {"database": "pubmlst_neisseria_seqdef", "st": 20000},
    )
    assert result["status"] == "error"
    assert result["error"].startswith("PubMLST returned HTTP 403: ")
    assert "2024-12-31" in result["error"]


@pytest.mark.parametrize("st", [None, "", "ST"])
def test_get_profile_requires_st(http, st):
    result = _run(
        "PubMLST_get_profile", {"database": "pubmlst_neisseria_seqdef", "st": st}
    )
    assert result["status"] == "error"
    assert "st is required" in result["error"]
    assert http.calls == []


@pytest.mark.parametrize("st", ["11/../12", "abc", -3, 1.5])
def test_get_profile_rejects_a_non_numeric_st(http, st):
    result = _run(
        "PubMLST_get_profile", {"database": "pubmlst_neisseria_seqdef", "st": st}
    )
    assert result["status"] == "error"
    assert "st must be" in result["error"]
    assert http.calls == []


@pytest.mark.parametrize("scheme_id", ["mlst", 0, -1, True])
def test_bad_scheme_id_is_an_error(http, scheme_id):
    result = _run(
        "PubMLST_get_profile",
        {"database": "pubmlst_neisseria_seqdef", "scheme_id": scheme_id, "st": 11},
    )
    assert result["status"] == "error"
    assert "scheme_id" in result["error"]
    assert http.calls == []


def test_isolates_database_is_rejected_with_the_seqdef_name(http):
    result = _run("PubMLST_list_schemes", {"database": "pubmlst_neisseria_isolates"})
    assert result["status"] == "error"
    assert "pubmlst_neisseria_seqdef" in result["error"]
    assert http.calls == []


def test_database_name_is_quoted_in_the_url(http):
    http("GET", "db/a%2Fb_seqdef/schemes", {"records": 0, "schemes": []})
    result = _run("PubMLST_list_schemes", {"database": "a/b_seqdef"})
    assert result["status"] == "success" and result["data"] == []


def test_type_sequence_assigns_st11_from_seven_loci(http):
    fasta = (FIXTURES / "neisseria_st11_mlst_loci.fasta").read_text()
    http(
        "POST",
        "db/pubmlst_neisseria_seqdef/schemes/1/sequence",
        _load("type_st11.json"),
    )
    result = _run(
        "PubMLST_type_sequence",
        {"database": "pubmlst_neisseria_seqdef", "scheme_id": 1, "sequence": fasta},
    )
    assert result["status"] == "success"
    assert result["data"]["fields"] == {"ST": "11", "clonal_complex": "ST-11 complex"}
    assert result["data"]["exact_matches"]["abcZ"] == ["2"]
    assert result["metadata"]["loci_matched"] == 7
    assert "partial_matches" not in result["data"]
    method, _, body = http.calls[0]
    assert method == "POST" and body == {"sequence": fasta.strip()}


def test_type_sequence_says_why_an_empty_answer_is_empty(http):
    """PubMLST answers {} for a novel allele; that is not a failed call."""
    http(
        "POST",
        "db/pubmlst_neisseria_seqdef/schemes/1/sequence",
        _load("type_abcz_1snp_exact.json"),
    )
    result = _run(
        "PubMLST_type_sequence",
        {"database": "pubmlst_neisseria_seqdef", "sequence": "ACGT" * 40},
    )
    assert result["status"] == "success"
    assert result["data"] == {"exact_matches": {}, "fields": {}}
    assert "partial_matches=true" in result["metadata"]["note"]


def test_type_sequence_partial_matches_keep_only_hits_and_drop_sequences(http):
    http(
        "POST",
        "db/pubmlst_neisseria_seqdef/schemes/1/sequence",
        _load("type_abcz_1snp_partial.json"),
    )
    result = _run(
        "PubMLST_type_sequence",
        {
            "database": "pubmlst_neisseria_seqdef",
            "sequence": "ACGT" * 40,
            "partial_matches": True,
        },
    )
    partial = result["data"]["partial_matches"]
    assert list(partial) == ["abcZ"]  # the other six loci come back as {}
    assert partial["abcZ"]["allele"] == "2"
    assert partial["abcZ"]["mismatches"] == "1"
    assert "sequence" not in partial["abcZ"]
    assert "flanking_sequence" not in partial["abcZ"]
    assert "No sequence type assigned" in result["metadata"]["note"]
    assert http.calls[0][2]["partial_matches"] == 1


def test_type_sequence_requires_a_sequence(http):
    result = _run("PubMLST_type_sequence", {"database": "pubmlst_neisseria_seqdef"})
    assert result["status"] == "error"
    assert http.calls == []


def test_network_failures_are_errors_not_exceptions(monkeypatch):
    def boom(*args, **kwargs):
        raise requests.exceptions.Timeout()

    monkeypatch.setattr(P.requests, "get", boom)
    result = _run("PubMLST_list_databases", {})
    assert result["status"] == "error"
    assert "timed out" in result["error"]


def test_non_json_body_is_an_error(http):
    http("GET", "db", ValueError("not json"))
    result = _run("PubMLST_list_databases", {})
    assert result == {
        "status": "error",
        "error": "PubMLST returned a non-JSON response",
    }
