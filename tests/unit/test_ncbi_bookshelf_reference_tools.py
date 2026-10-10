"""NCBI Bookshelf reference tools (StatPearls, LactMed, LiverTox) against an
index built by ``ncbi_bookshelf_index`` from real archive members.

The fixtures under tests/fixtures/ncbi_bookshelf are unmodified members of
the NCBI litarch archives (recorded with their SHA-256 in FIXTURES.tsv): 7
StatPearls chapters, 5 LactMed and 6 LiverTox records and the LiverTox master
list. No test touches the network.
"""

import hashlib
import importlib
import inspect
import json
import re
import shutil
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "ncbi_bookshelf"
SPEC_FILE = ROOT / "src" / "tooluniverse" / "data" / "ncbi_bookshelf_reference_tools.json"
INDEX_ENV = "TOOLUNIVERSE_BOOKSHELF_DIR"
TOOL_NAMES = [
    "StatPearls_search",
    "StatPearls_get_management",
    "StatPearls_get_chapter_section",
    "LactMed_get_drug",
    "LiverTox_get_drug",
]
LIMIT = 8000


def size(result):
    return len(json.dumps(result))


def quiet(*_args):
    pass


@pytest.fixture(scope="module")
def index_mod():
    return importlib.import_module("tooluniverse.ncbi_bookshelf_index")


@pytest.fixture(scope="module")
def tool_mod():
    return importlib.import_module("tooluniverse.ncbi_bookshelf_reference_tool")


@pytest.fixture(scope="module")
def specs():
    return {spec["name"]: spec for spec in json.loads(SPEC_FILE.read_text())}


@pytest.fixture(scope="module")
def fixture_index(tmp_path_factory, index_mod):
    out = tmp_path_factory.mktemp("bookshelf_index")
    index_mod.build(
        {name: str(FIXTURES / name) for name in ("statpearls", "lactmed", "livertox")},
        str(out),
        log=quiet,
    )
    return out


@pytest.fixture
def index_env(monkeypatch, fixture_index):
    monkeypatch.setenv(INDEX_ENV, str(fixture_index))
    return fixture_index


@pytest.fixture
def make_tool(tool_mod, specs):
    """make_tool(tool_name, **fields) -> tool instance built from its JSON spec."""

    def make(name, **fields):
        config = json.loads(json.dumps(specs[name]))
        config.setdefault("fields", {}).update(fields)
        return getattr(tool_mod, config["type"])(config)

    return make


@pytest.fixture
def call(make_tool, index_env):
    """call(tool_name, **arguments) against the fixture index."""

    def run(name, **arguments):
        return make_tool(name).run(arguments)

    return run


# ---------------------------------------------------------------------------
# fixture and index build
# ---------------------------------------------------------------------------


def test_fixture_files_are_the_recorded_archive_members():
    lines = (FIXTURES / "FIXTURES.tsv").read_text().splitlines()[1:]
    assert len(lines) == 22
    for line in lines:
        source, _archive, member, length, digest = line.split("\t")
        data = (FIXTURES / source / member).read_bytes()
        assert len(data) == int(length)
        assert hashlib.sha256(data).hexdigest() == digest


def test_fixture_index_counts(fixture_index, index_mod):
    manifest = json.loads((fixture_index / "manifest.json").read_text())
    counts = {name: entry["counts"] for name, entry in manifest["sources"].items()}
    assert counts["statpearls"]["chapters"] == 7
    assert counts["statpearls"]["archived"] == 1
    assert counts["statpearls"]["nursing"] == 1
    assert counts["lactmed"]["drug_records"] == 4
    assert counts["lactmed"]["other_records"] == 1
    assert counts["livertox"]["records"] == 6
    assert counts["livertox"]["masterlist_rows"] > 1500
    for entry in counts.values():
        assert entry["parse_failures"] == []
    assert manifest["build_script_sha256"] == hashlib.sha256(
        Path(index_mod.__file__).read_bytes()
    ).hexdigest()
    assert not list(fixture_index.glob("*.building"))


def test_tools_normalize_names_with_the_builders_function(index_mod, tool_mod):
    assert tool_mod.normalize_name is index_mod.normalize_name
    assert index_mod.normalize_name("  Caféine® (Toprol-XL) ") == "cafeine toprol xl"


def test_rendered_text_keeps_tables_lists_and_drops_citations(fixture_index):
    import sqlite3

    conn = sqlite3.connect(str(fixture_index / "statpearls.sqlite"))
    text = conn.execute(
        "SELECT text FROM sections WHERE chapter_id = 'article-20545'"
        " AND heading = 'Anatomy and Physiology'"
    ).fetchone()[0]
    assert "A1 | Heart (AV node), CNS |" in text  # table row
    assert not re.search(r"\[\d+(,\s*\d+)*\]", text)  # citation markers gone
    text = conn.execute(
        "SELECT text FROM sections WHERE chapter_id = 'article-20545'"
        " AND heading = 'Indications'"
    ).fetchone()[0]
    assert "\n  - Prior test results" in text  # nested list indented
    headings = [r[0] for r in conn.execute("SELECT heading FROM sections")]
    assert "References" not in headings and "Review Questions" not in headings
    conn.close()


def test_build_skips_appledouble_files(index_mod, tmp_path):
    source = tmp_path / "lactmed"
    source.mkdir()
    shutil.copy(FIXTURES / "lactmed" / "LM416.nxml", source / "LM416.nxml")
    (source / "._LM416.nxml").write_bytes(b"\x00\x05\x16\x07 Mac OS X metadata")
    counts = index_mod.build({"lactmed": str(source)}, str(tmp_path / "out"), log=quiet)[
        "sources"
    ]["lactmed"]["counts"]
    assert counts["files"] == 1 and counts["parse_failures"] == []


def test_failed_build_keeps_the_previous_index(index_mod, tmp_path, monkeypatch):
    out = tmp_path / "out"
    index_mod.build({"lactmed": str(FIXTURES / "lactmed")}, str(out), log=quiet)
    before = (out / "lactmed.sqlite").read_bytes()

    def broken(source, out_path, log=print):
        with open(out_path, "wb") as handle:
            handle.write(b"half an index")
        raise RuntimeError("archive ended early")

    monkeypatch.setitem(index_mod.BUILDERS, "lactmed", broken)
    with pytest.raises(RuntimeError, match="archive ended early"):
        index_mod.build({"lactmed": str(FIXTURES / "lactmed")}, str(out), log=quiet)
    assert (out / "lactmed.sqlite").read_bytes() == before
    assert not list(out.glob("*.building"))


def test_build_from_a_tar_archive_records_its_sha256(index_mod, tmp_path):
    import tarfile

    archive = tmp_path / "lactmed_NBK501922.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(FIXTURES / "lactmed", arcname="lactmed_NBK501922")
    manifest = index_mod.build({"lactmed": str(archive)}, str(tmp_path / "out"), log=quiet)
    entry = manifest["sources"]["lactmed"]
    assert entry["counts"]["drug_records"] == 4
    assert entry["archive"] == archive.name
    assert entry["archive_sha256"] == hashlib.sha256(archive.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# index location, SQLite capability, install / status / CLI
# ---------------------------------------------------------------------------


def test_default_index_dir_follows_env_then_user_cache(index_mod, monkeypatch, tmp_path):
    monkeypatch.setenv(INDEX_ENV, str(tmp_path / "books"))
    assert index_mod.default_index_dir() == str(tmp_path / "books")
    monkeypatch.delenv(INDEX_ENV)
    monkeypatch.setenv("TOOLUNIVERSE_TMPDIR", str(tmp_path / "cache"))
    assert index_mod.default_index_dir() == str(tmp_path / "cache" / "ncbi_bookshelf")


def test_sqlite_problem_names_the_requirement(index_mod, monkeypatch):
    assert index_mod.sqlite_problem() is None  # this SQLite has FTS5 >= 3.27
    monkeypatch.setattr(index_mod, "FTS_TOKENIZER", "no_such_tokenizer")
    problem = index_mod.sqlite_problem()
    assert "3.27.0" in problem and "no_such_tokenizer" in problem


def test_install_refuses_statpearls_on_an_unusable_sqlite(index_mod, monkeypatch, tmp_path):
    monkeypatch.setattr(index_mod, "sqlite_problem", lambda: "SQLite too old")

    def no_network(*_args, **_kwargs):
        raise AssertionError("must refuse before downloading")

    monkeypatch.setattr(index_mod, "file_list", no_network)
    with pytest.raises(RuntimeError, match="SQLite too old"):
        index_mod.install(["statpearls"], str(tmp_path), log=quiet)


def test_install_builds_local_archives_without_downloading(
    index_mod, monkeypatch, tmp_path
):
    def no_network(*_args, **_kwargs):
        raise AssertionError("no download expected")

    monkeypatch.setattr(index_mod, "file_list", no_network)
    index_mod.install(
        None,
        str(tmp_path),
        archives={"lactmed": str(FIXTURES / "lactmed")},
        log=quiet,
    )
    report = index_mod.status(str(tmp_path))
    assert report["books"]["lactmed"]["installed"] is True
    assert report["books"]["lactmed"]["counts"]["drug_records"] == 4
    assert report["books"]["livertox"]["installed"] is False
    assert "--books livertox" in report["books"]["livertox"]["install"]
    assert "does not exist" in report["books"]["livertox"]["problem"]


def test_status_reports_an_index_the_tools_would_refuse(index_mod, tmp_path):
    index_mod.build({"lactmed": str(FIXTURES / "lactmed")}, str(tmp_path), log=quiet)
    shutil.copy(tmp_path / "lactmed.sqlite", tmp_path / "livertox.sqlite")
    (tmp_path / "statpearls.sqlite").write_bytes(b"not a database" * 100)
    books = index_mod.status(str(tmp_path))["books"]
    assert books["lactmed"]["installed"] is True
    assert books["livertox"]["installed"] is False
    assert "is not a LiverTox" in books["livertox"]["problem"]
    assert books["statpearls"]["installed"] is False
    assert "cannot read" in books["statpearls"]["problem"]


def test_install_command_names_a_non_default_directory(index_mod, monkeypatch, tmp_path):
    monkeypatch.setenv(INDEX_ENV, str(tmp_path / "default"))
    assert index_mod.install_command("lactmed") == (
        "python -m tooluniverse.ncbi_bookshelf_index build --books lactmed"
    )
    assert index_mod.install_command("lactmed", str(tmp_path / "default")).endswith(
        "--books lactmed"
    )
    assert index_mod.install_command("lactmed", str(tmp_path / "other")).endswith(
        "--books lactmed --dir %s" % (tmp_path / "other")
    )


def test_install_rejects_unknown_books(index_mod, tmp_path):
    with pytest.raises(ValueError, match="genereviews"):
        index_mod.install(["genereviews"], str(tmp_path), log=quiet)


class _Response:
    def __init__(self, status, body=b"", headers=None, reason="OK"):
        self.status_code = status
        self.body = body
        self.headers = headers or {}
        self.reason = reason
        self.text = body.decode("utf-8", "replace")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def raise_for_status(self):
        if self.status_code >= 400:
            raise OSError("HTTP %d" % self.status_code)

    def iter_content(self, chunk_size=1):
        for i in range(0, len(self.body), 4):
            yield self.body[i : i + 4]


class _Session:
    """Serves queued responses and records the request headers."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def request(self, method, url, headers=None, timeout=None, **_kwargs):
        return self.get(url, headers=headers, timeout=timeout)

    def get(self, url, headers=None, stream=False, timeout=None):
        self.requests.append({"url": url, "headers": dict(headers or {})})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_locate_archive_reads_ncbis_file_list(index_mod):
    listing = (
        "File,Title,Publisher,Publication Year,Accession ID,Last Updated\n"
        '03/56/styleguide_NBK988.tar.gz,The NCBI Style Guide,"NCBI, US",2004,NBK988,2019-06-18\n'
        "90/6c/lactmed_NBK501922.tar.gz,Drugs and Lactation Database (LactMed),"
        "NICHD,2006,NBK501922,2026-09-22 02:43:34\n"
    )
    session = _Session([_Response(200, listing.encode())])
    rows = index_mod.file_list(session)
    assert session.requests[0]["url"] == index_mod.LITARCH_URL + "file_list.csv"
    assert "ToolUniverse" in session.requests[0]["headers"]["User-Agent"]
    assert index_mod.locate_archive("lactmed", rows) == {
        "path": "90/6c/lactmed_NBK501922.tar.gz",
        "url": index_mod.LITARCH_URL + "90/6c/lactmed_NBK501922.tar.gz",
        "last_updated": "2026-09-22 02:43:34",
    }
    with pytest.raises(RuntimeError, match="NBK547852"):
        index_mod.locate_archive("livertox", rows)


def test_download_resumes_a_partial_file(index_mod, tmp_path):
    payload = b"0123456789abcdef"
    dest = tmp_path / "book.tar.gz"
    (tmp_path / "book.tar.gz.part").write_bytes(payload[:6])
    session = _Session(
        [_Response(206, payload[6:], {"Content-Range": "bytes 6-15/16"})]
    )
    result = index_mod.download("https://example.org/b", str(dest), session, log=quiet)
    assert session.requests[0]["headers"] == {"Range": "bytes=6-"}
    assert dest.read_bytes() == payload
    assert result["bytes"] == 16
    assert result["sha256"] == hashlib.sha256(payload).hexdigest()
    assert not (tmp_path / "book.tar.gz.part").exists()


def test_download_restarts_when_the_server_ignores_the_range(index_mod, tmp_path):
    payload = b"0123456789"
    (tmp_path / "b.part").write_bytes(b"stale")
    session = _Session([_Response(200, payload, {"Content-Length": "10"})])
    index_mod.download("https://example.org/b", str(tmp_path / "b"), session, log=quiet)
    assert (tmp_path / "b").read_bytes() == payload


def test_download_retries_a_short_or_interrupted_transfer(index_mod, tmp_path, monkeypatch):
    monkeypatch.setattr(index_mod.time, "sleep", lambda _s: None)
    payload = b"0123456789"
    session = _Session(
        [
            _Response(200, payload[:4], {"Content-Length": "10"}),  # cut short
            OSError("connection reset"),
            _Response(206, payload[4:], {"Content-Range": "bytes 4-9/10"}),
        ]
    )
    index_mod.download("https://example.org/b", str(tmp_path / "b"), session, log=quiet)
    assert (tmp_path / "b").read_bytes() == payload
    assert session.requests[-1]["headers"] == {"Range": "bytes=4-"}


def test_download_does_not_retry_a_missing_file(index_mod, tmp_path, monkeypatch):
    monkeypatch.setattr(index_mod.time, "sleep", lambda _s: None)
    session = _Session([_Response(404, b"", reason="Not Found")])
    with pytest.raises(RuntimeError, match="HTTP 404"):
        index_mod.download("https://example.org/b", str(tmp_path / "b"), session, log=quiet)
    assert len(session.requests) == 1


def test_install_downloads_then_deletes_the_archive(index_mod, monkeypatch, tmp_path):
    import tarfile

    archive = tmp_path / "src.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(FIXTURES / "lactmed", arcname="lactmed_NBK501922")
    data = archive.read_bytes()
    listings = []

    def fake_file_list(session):
        listings.append(session)
        return [["90/6c/lactmed_NBK501922.tar.gz", "LactMed", "NICHD", "2006",
                 "NBK501922", "2026-09-22 02:43:34"]]

    monkeypatch.setattr(index_mod, "file_list", fake_file_list)
    monkeypatch.setattr(
        index_mod,
        "_session",
        lambda: _Session([_Response(200, data, {"Content-Length": str(len(data))})]),
    )
    out = tmp_path / "index"
    manifest = index_mod.install(["lactmed"], str(out), log=quiet)
    entry = manifest["sources"]["lactmed"]
    assert len(listings) == 1
    assert entry["archive_url"] == index_mod.LITARCH_URL + "90/6c/lactmed_NBK501922.tar.gz"
    assert entry["archive_last_updated"] == "2026-09-22 02:43:34"
    assert entry["archive_sha256"] == hashlib.sha256(data).hexdigest()
    assert entry["archive_deleted_after_build"] is True
    assert not list((out / "downloads").iterdir())
    saved = json.loads((out / "manifest.json").read_text())
    assert saved["sources"]["lactmed"]["archive_deleted_after_build"] is True


def test_cli_build_and_status(index_mod, tmp_path, capsys):
    out = tmp_path / "index"
    assert index_mod.main(["build", "--dir", str(out), "--lactmed", str(FIXTURES / "lactmed")]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["books"]["lactmed"]["installed"] is True
    assert index_mod.main(["status", "--dir", str(out)]) == 0
    assert json.loads(capsys.readouterr().out)["books"]["statpearls"]["installed"] is False
    assert index_mod.main(["build", "--dir", str(out), "--books", "lactmed", "--lactmed",
                           str(tmp_path / "missing")]) == 1
    assert "error:" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# StatPearls_search
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "query, title",
    [
        ("amitriptyline", "Amitriptyline"),
        ("beta blockers", "Beta Blockers"),
        ("dog bite antibiotic", "Animal Bites"),
        (
            "tricyclic antidepressant overdose sodium bicarbonate",
            "Tricyclic Antidepressant Toxicity",
        ),
    ],
)
def test_search_ranks_the_named_chapter_first(call, query, title):
    result = call("StatPearls_search", query=query)
    assert result["status"] == "success"
    assert result["data"][0]["title"] == title
    assert result["data"][0]["rank"] == 1
    hit = result["data"][0]
    for key in ("chapter_id", "best_section", "snippet", "last_updated"):
        assert hit[key]
    assert result["source"]["book_id"] == "NBK430685"
    assert "CC BY-NC-ND 4.0" in result["license"]


def test_search_long_question_still_returns_the_chapter(call):
    result = call(
        "StatPearls_search",
        query=(
            "What is the recommended starting dose of amitriptyline for an adult "
            "outpatient with major depressive disorder?"
        ),
    )
    assert result["data"][0]["title"] == "Amitriptyline"
    assert "amitriptyline" in result["metadata"]["query_terms"]
    assert "what" not in result["metadata"]["query_terms"]


def test_search_best_section_points_at_the_matching_section(call):
    result = call(
        "StatPearls_search",
        query="animal bites antibiotic prophylaxis amoxicillin clavulanate",
    )
    hit = result["data"][0]
    assert hit["title"] == "Animal Bites"
    assert hit["best_section"] in (
        "Treatment / Management",
        *hit.get("other_matching_sections", []),
    )


def test_search_excludes_archived_chapters_unless_asked(call):
    default = call("StatPearls_search", query="dipyridamole nuclear stress test")
    assert all(hit["chapter_id"] != "article-20545" for hit in default["data"])
    assert "excluded" in default["metadata"]["archived_chapters"]
    included = call(
        "StatPearls_search", query="dipyridamole nuclear stress test", include_archived=True
    )
    assert included["data"][0]["chapter_id"] == "article-20545"
    assert included["data"][0]["archived"] is True


def test_search_treats_operator_words_and_symbols_literally(call):
    result = call("StatPearls_search", query='NOT amitriptyline AND "NEAR" (overdose*')
    assert result["status"] == "success"
    assert result["data"][0]["title"] in (
        "Amitriptyline",
        "Tricyclic Antidepressant Toxicity",
    )


def test_search_limit_is_clamped(call):
    assert len(call("StatPearls_search", query="amitriptyline", limit=1)["data"]) == 1
    assert (
        len(call("StatPearls_search", query="disease patients treatment", limit=50)["data"])
        <= 10
    )


def test_nursing_edition_follows_its_parent_chapter(tool_mod):
    titles = {
        "a": "Atrial Fibrillation (Nursing)",
        "b": "Paroxysmal Atrial Fibrillation",
        "c": "Atrial Fibrillation",
        "d": "Ketoacidosis (Nursing)",
    }
    assert tool_mod.nursing_after_parent(["a", "b", "c", "d"], titles) == [
        "c",
        "a",
        "b",
        "d",
    ]
    assert tool_mod.nursing_after_parent(["c", "a"], titles) == ["c", "a"]


def test_exact_title_query_ranks_that_chapter_first(call):
    result = call("StatPearls_search", query="Ketoacidosis (Nursing)")
    assert result["data"][0]["title"] == "Ketoacidosis (Nursing)"
    result = call("StatPearls_search", query="tricyclic antidepressant toxicity")
    assert result["data"][0]["title"] == "Tricyclic Antidepressant Toxicity"


def test_search_rejects_empty_or_stopword_queries(call):
    for query in ("", "   ", "what is the of"):
        result = call("StatPearls_search", query=query)
        assert result["status"] == "error"
        assert result["error_type"] == "invalid_argument"


# ---------------------------------------------------------------------------
# StatPearls_get_management
# ---------------------------------------------------------------------------


def test_management_returns_the_treatment_section_of_the_named_condition(call):
    result = call("StatPearls_get_management", condition="animal bites")
    assert result["status"] == "success", result
    first = result["data"][0]
    assert first["title"] == "Animal Bites"
    assert first["section"] == "Treatment / Management"
    assert "amoxicillin" in first["text"].lower()
    assert first["url"] == "https://www.ncbi.nlm.nih.gov/books/n/statpearls/article-18346/"
    assert "Evaluation" in first["other_sections"]
    assert "Treatment / Management" not in first["other_sections"]
    assert len(result["data"]) <= 2
    assert size(result) <= LIMIT


def test_management_falls_back_to_administration_for_a_drug_chapter(call):
    result = call("StatPearls_get_management", condition="amitriptyline", limit=1)
    assert [item["title"] for item in result["data"]] == ["Amitriptyline"]
    assert result["data"][0]["section"] == "Administration"
    assert "75 mg daily" in result["data"][0]["text"]


def test_management_uses_technique_section_of_a_procedure_chapter(call):
    result = call(
        "StatPearls_get_management",
        condition="dipyridamole nuclear stress test",
        include_archived=True,
        limit=1,
    )
    item = result["data"][0]
    assert item["chapter_id"] == "article-20545"
    assert item["section"] == "Technique or Treatment"
    assert item["archived"] is True


def test_management_with_evaluation_shares_the_output_bound(call):
    result = call(
        "StatPearls_get_management",
        condition="tricyclic antidepressant toxicity",
        include_evaluation=True,
        limit=3,
    )
    first = result["data"][0]
    assert first["title"] == "Tricyclic Antidepressant Toxicity"
    assert first["evaluation"]["heading"] == "Evaluation"
    assert first["evaluation"]["text"]
    assert "sodium bicarbonate" in first["text"].lower()
    assert "Evaluation" not in first["other_sections"]
    assert len(result["data"]) <= 3
    assert size(result) <= LIMIT


def test_management_reads_a_nursing_edition_without_a_parent(call):
    result = call("StatPearls_get_management", condition="ketoacidosis", limit=1)
    assert result["data"][0]["title"] == "Ketoacidosis (Nursing)"
    assert result["data"][0]["section"] == "Medical Management"


def test_management_skips_a_nursing_edition_when_its_parent_is_found(
    index_mod, make_tool, monkeypatch, tmp_path
):
    source = tmp_path / "statpearls"
    source.mkdir()
    nursing = (FIXTURES / "statpearls" / "nurse-article-23877.nxml").read_bytes()
    shutil.copy(FIXTURES / "statpearls" / "nurse-article-23877.nxml", source)
    parent = nursing.replace(b"nurse-article-23877", b"article-23877").replace(
        b"Ketoacidosis (Nursing)", b"Ketoacidosis"
    )
    (source / "article-23877.nxml").write_bytes(parent)
    index_mod.build({"statpearls": str(source)}, str(tmp_path / "out"), log=quiet)
    monkeypatch.setenv(INDEX_ENV, str(tmp_path / "out"))
    result = make_tool("StatPearls_get_management").run(
        {"condition": "ketoacidosis", "limit": 3}
    )
    assert [item["title"] for item in result["data"]] == ["Ketoacidosis"]


def test_management_truncates_at_a_word_with_a_pointer_to_the_full_section(
    make_tool, index_env
):
    result = make_tool("StatPearls_get_management", max_output_chars=2500).run(
        {"condition": "animal bites", "limit": 1}
    )
    assert size(result) <= 2500
    item = result["data"][0]
    assert item["truncated"] is True
    assert re.search(
        r" \[\.\.\. \d+ more characters truncated; read the whole section with "
        r"StatPearls_get_chapter_section\(chapter='article-18346', "
        r"section='Treatment / Management'\) \.\.\.\]$",
        item["text"],
    )


def test_management_unknown_condition_is_not_found(call):
    result = call("StatPearls_get_management", condition="zzqx xylophonia")
    assert result["status"] == "error"
    assert result["error_type"] == "not_found"
    assert "hint" in result


@pytest.mark.parametrize(
    "arguments",
    [{}, {"condition": "  "}, {"condition": "what is the of"}, {"condition": 7},
     {"condition": "animal bites", "limit": "many"}],
)
def test_management_invalid_arguments(make_tool, index_env, arguments):
    result = make_tool("StatPearls_get_management").run(arguments)
    assert result["status"] == "error"
    assert result["error_type"] == "invalid_argument"


def test_management_limit_is_clamped(call):
    result = call("StatPearls_get_management", condition="toxicity overdose", limit=10)
    assert 1 <= len(result["data"]) <= 3


def test_first_top_section_prefers_earlier_headings_and_ignores_subsections(tool_mod):
    nodes = [
        {"level": 1, "heading": "Introduction"},
        {"level": 2, "heading": "Treatment / Management"},
        {"level": 1, "heading": "Clinical Significance"},
        {"level": 1, "heading": "Treatment/Management"},
    ]
    assert tool_mod.first_top_section(nodes, tool_mod.MANAGEMENT_HEADINGS) == 3
    assert tool_mod.first_top_section(nodes[:3], tool_mod.MANAGEMENT_HEADINGS) == 2
    assert tool_mod.first_top_section(nodes[:2], tool_mod.MANAGEMENT_HEADINGS) is None


# ---------------------------------------------------------------------------
# StatPearls_get_chapter_section
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "chapter", ["Amitriptyline", "AMITRIPTYLINE", "article-17465", "17465"]
)
def test_chapter_lookup_by_title_or_id_lists_sections(call, chapter):
    result = call("StatPearls_get_chapter_section", chapter=chapter)
    assert result["status"] == "success"
    data = result["data"]
    assert data["chapter_id"] == "article-17465"
    headings = [s["heading"] for s in data["sections"]]
    assert headings[:4] == [
        "Continuing Education Activity",
        "Indications",
        "Mechanism of Action",
        "Administration",
    ]
    assert all(s["chars"] > 0 for s in data["sections"])
    assert result["source"]["chapter_title"] == "Amitriptyline"
    assert result["source"]["last_updated"] == "2026-09-14"


@pytest.mark.parametrize(
    "section, expected",
    [
        ("Administration", "Administration"),
        ("administration", "Administration"),
        ("dosage", "Administration"),
        ("Dosing", "Administration"),
        ("side effects", "Adverse Effects"),
        ("adverse effect", "Adverse Effects"),
        ("Toxicty", "Toxicity"),
    ],
)
def test_section_lookup_by_heading(call, section, expected):
    result = call("StatPearls_get_chapter_section", chapter="Amitriptyline", section=section)
    assert result["status"] == "success"
    assert result["data"]["section"] == expected


def test_administration_section_has_the_depression_starting_dose(call):
    result = call(
        "StatPearls_get_chapter_section", chapter="article-17465", section="Administration"
    )
    text = result["data"]["text"]
    assert (
        "The recommended initial dose for depression is 75 mg daily in divided doses"
        in text
    )
    assert "50 to 100 mg as a single bedtime dose" in text
    assert result["data"]["total_pages"] == 1


def test_treatment_alias_and_fuzzy_chapter_title(call):
    result = call("StatPearls_get_chapter_section", chapter="animal bite", section="treatment")
    assert result["status"] == "success"
    assert result["data"]["title"] == "Animal Bites"
    assert result["data"]["section"] == "Treatment / Management"
    assert "amoxicillin" in result["data"]["text"].lower()


def test_section_not_found_lists_available_sections(call):
    result = call(
        "StatPearls_get_chapter_section",
        chapter="Amitriptyline",
        section="Embryology of the left ventricle",
    )
    assert result["status"] == "error"
    assert result["error_type"] == "section_not_found"
    assert "Administration" in result["available_sections"]


def test_chapter_not_found(call):
    result = call("StatPearls_get_chapter_section", chapter="Quantum chromodynamics")
    assert result["status"] == "error"
    assert result["error_type"] == "not_found"
    assert "StatPearls_search" in result["hint"]
    result = call("StatPearls_get_chapter_section", chapter="article-99999999")
    assert result["error_type"] == "not_found"


def test_chapter_nbk_accession_is_explained(call):
    result = call("StatPearls_get_chapter_section", chapter="NBK537225")
    assert result["status"] == "error"
    assert "chapter_id" in result["error"]


def test_long_section_pages_reassemble_the_full_text(make_tool, index_env):
    tool = make_tool("StatPearls_get_chapter_section", max_output_chars=2500)
    first = tool.run({"chapter": "Amitriptyline", "section": "Adverse Effects"})
    total = first["data"]["total_pages"]
    assert total > 1
    pages = []
    for page in range(1, total + 1):
        result = tool.run(
            {"chapter": "Amitriptyline", "section": "Adverse Effects", "page": page}
        )
        assert size(result) <= 2500
        text = result["data"]["text"]
        if page < total:
            assert text.endswith("call again with page=%d of %d ...]" % (page + 1, total))
            text = text[: text.rindex(" [... section continues")]
        pages.append(text)
    full = make_tool("StatPearls_get_chapter_section").run(
        {"chapter": "Amitriptyline", "section": "Adverse Effects"}
    )["data"]["text"]
    assert " ".join(" ".join(pages).split()) == " ".join(full.split())
    beyond = tool.run(
        {"chapter": "Amitriptyline", "section": "Adverse Effects", "page": 999}
    )
    assert beyond["data"]["page"] == total


# ---------------------------------------------------------------------------
# LactMed_get_drug / LiverTox_get_drug
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name, how",
    [
        ("Metoprolol", "exact name"),
        ("METOPROLOL", "exact name"),
        ("  metoprolol ", "exact name"),
        ("metoprolol tartrate", "name without salt/dosage-form/strength words"),
        (
            "Metoprolol Succinate ER 50 mg tablets",
            "name without salt/dosage-form/strength words",
        ),
        ("Toprol-XL", "via synonym 'Toprol-XL'"),
        ("Toprol XL (metoprolol succinate)", "via synonym 'Toprol-XL'"),
    ],
)
def test_lactmed_name_normalization(call, name, how):
    result = call("LactMed_get_drug", drug_name=name)
    assert result["status"] == "success", result
    assert result["data"]["drug"] == "Metoprolol"
    assert how in result["data"]["matched"]
    assert result["source"]["chapter_id"] == "LM296"
    assert result["source"]["last_updated"] == "2024-11-15"


def test_lactmed_returns_the_lactation_sections_in_order(call):
    result = call("LactMed_get_drug", drug_name="sulfisoxazole")
    headings = [s["heading"] for s in result["data"]["sections"]]
    assert headings == [
        "Summary of Use during Lactation",
        "Drug Levels",
        "Effects in Breastfed Infants",
        "Effects on Lactation and Breastmilk",
        "Alternate Drugs to Consider",
    ]
    summary = result["data"]["sections"][0]["text"]
    assert summary.startswith("With healthy, fullterm infants it appears acceptable")
    assert result["data"]["casrn"] == "127-69-5"
    assert "public domain" in result["license"]


def test_lactmed_single_section(call):
    result = call(
        "LactMed_get_drug", drug_name="amitriptyline", section="effects in breastfed infants"
    )
    assert [s["heading"] for s in result["data"]["sections"]] == [
        "Effects in Breastfed Infants"
    ]


@pytest.mark.parametrize(
    "name, record, how",
    [
        ("nabumetone", "Nabumetone", "exact name"),
        ("Relafen", "Nabumetone", "via trade name 'Relafen'"),
        ("nabumetone 500 mg tablets", "Nabumetone", "without salt/dosage-form/strength words"),
        ("desvenlafaxine", "Venlafaxine", "master-list ingredient 'Desvenlafaxine'"),
        ("Pentobarbital Sodium", "Barbiturates", "master-list ingredient 'Pentobarbital'"),
    ],
)
def test_livertox_name_normalization(call, name, record, how):
    result = call("LiverTox_get_drug", drug_name=name)
    assert result["status"] == "success", result
    assert result["source"]["chapter_id"] == record
    assert how in result["data"]["matched"]


def test_livertox_likelihood_score_and_sections(call):
    result = call("LiverTox_get_drug", drug_name="Nabumetone")
    data = result["data"]
    assert data["likelihood_score"] == "E*"
    assert data["likelihood_score_meaning"].startswith("unproven but suspected")
    assert data["trade_names"] == ["Relafen"]
    headings = [s["heading"] for s in data["sections"]]
    assert headings[:5] == [
        "Introduction",
        "Background",
        "Hepatotoxicity",
        "Mechanism of Injury",
        "Outcome and Management",
    ]
    assert "PRODUCT INFORMATION" not in headings
    assert result["source"]["last_updated"] == "2025-08-10"


def test_livertox_multi_agent_chapter_reports_each_statement(call):
    result = call("LiverTox_get_drug", drug_name="desvenlafaxine")
    data = result["data"]
    assert data["likelihood_score"] is None
    assert any(
        s.startswith("Likelihood score (desvenlafaxine): E*")
        for s in data["likelihood_statements"]
    )
    assert data["master_list_entry"]["likelihood_score"] == "E*"


def test_livertox_case_reports_section_returns_every_case_part(call):
    result = call("LiverTox_get_drug", drug_name="metoprolol", section="case report")
    headings = [s["heading"] for s in result["data"]["sections"]]
    assert headings and all(h.startswith("CASE REPORT > Case 1.") for h in headings)
    assert any(h.endswith("Key Points") for h in headings)


def test_name_variants(tool_mod):
    variants = dict(tool_mod.name_variants("Metoprolol Succinate ER (Toprol XL)"))
    assert "metoprolol succinate er toprol xl" in variants
    assert "toprol xl" in variants
    assert "metoprolol" in variants


def test_drug_not_found_is_an_explicit_error_with_suggestions(call):
    result = call("LactMed_get_drug", drug_name="metoprolo")
    assert result["status"] == "error"
    assert result["error_type"] == "not_found"
    assert "Metoprolol" in result["suggestions"]
    assert "not evidence" in result["error"]
    result = call("LiverTox_get_drug", drug_name="xyzzyquinone")
    assert result["error_type"] == "not_found"
    assert result["suggestions"] == []


def test_combination_name_suggests_its_components(call):
    result = call("LiverTox_get_drug", drug_name="metoprolol/nabumetone")
    assert result["status"] == "error"
    assert set(result["suggestions"][:2]) == {"Metoprolol", "Nabumetone"}


@pytest.mark.parametrize(
    "name, arguments",
    [
        ("LactMed_get_drug", {}),
        ("LactMed_get_drug", {"drug_name": "  "}),
        ("LiverTox_get_drug", {"drug_name": 42}),
        ("StatPearls_get_chapter_section", {}),
        ("StatPearls_search", {"query": "amitriptyline", "limit": "many"}),
    ],
)
def test_invalid_arguments_return_errors(make_tool, index_env, name, arguments):
    result = make_tool(name).run(arguments)
    assert result["status"] == "error"
    assert result["error_type"] == "invalid_argument"


def test_unknown_section_of_a_drug_record(call):
    result = call(
        "LiverTox_get_drug", drug_name="nabumetone", section="pharmacogenomics of zebrafish"
    )
    assert result["error_type"] == "section_not_found"
    assert "Hepatotoxicity" in result["available_sections"]


# ---------------------------------------------------------------------------
# missing / broken index
# ---------------------------------------------------------------------------

EXAMPLE_ARGS = {
    "StatPearls_search": {"query": "amitriptyline"},
    "StatPearls_get_management": {"condition": "animal bites"},
    "StatPearls_get_chapter_section": {"chapter": "Amitriptyline"},
    "LactMed_get_drug": {"drug_name": "metoprolol"},
    "LiverTox_get_drug": {"drug_name": "nabumetone"},
}
BOOK_OF = {
    "StatPearls_search": "statpearls",
    "StatPearls_get_management": "statpearls",
    "StatPearls_get_chapter_section": "statpearls",
    "LactMed_get_drug": "lactmed",
    "LiverTox_get_drug": "livertox",
}


@pytest.mark.parametrize("name", TOOL_NAMES)
def test_missing_index_names_the_build_command(make_tool, monkeypatch, tmp_path, name):
    monkeypatch.delenv(INDEX_ENV, raising=False)
    monkeypatch.setenv("TOOLUNIVERSE_TMPDIR", str(tmp_path))
    result = make_tool(name).run(EXAMPLE_ARGS[name])
    assert result["status"] == "error"
    assert result["error_type"] == "index_unavailable"
    assert "python -m tooluniverse.ncbi_bookshelf_index build --books %s" % BOOK_OF[
        name
    ] in result["error"]
    assert str(tmp_path / "ncbi_bookshelf") in result["error"]
    assert INDEX_ENV in result["error"]


def test_missing_index_in_a_configured_dir_names_that_dir(make_tool, monkeypatch, tmp_path):
    monkeypatch.setenv(INDEX_ENV, str(tmp_path / "default"))
    result = make_tool("LactMed_get_drug", index_dir=str(tmp_path / "mine")).run(
        {"drug_name": "metoprolol"}
    )
    assert result["error_type"] == "index_unavailable"
    assert "build --books lactmed --dir %s" % (tmp_path / "mine") in result["error"]


def test_corrupt_or_wrong_index_is_a_clear_error(make_tool, monkeypatch, tmp_path, fixture_index):
    monkeypatch.setenv(INDEX_ENV, str(tmp_path))
    (tmp_path / "statpearls.sqlite").write_bytes(b"this is not a database" * 100)
    result = make_tool("StatPearls_search").run({"query": "amitriptyline"})
    assert result["error_type"] == "index_unavailable"
    shutil.copy(fixture_index / "lactmed.sqlite", tmp_path / "livertox.sqlite")
    result = make_tool("LiverTox_get_drug").run({"drug_name": "nabumetone"})
    assert result["error_type"] == "index_unavailable"
    assert "is not a LiverTox" in result["error"]


def test_index_dir_from_tool_config_overrides_environment(
    make_tool, monkeypatch, tmp_path, fixture_index
):
    monkeypatch.setenv(INDEX_ENV, str(tmp_path / "empty"))
    result = make_tool("LactMed_get_drug", index_dir=str(fixture_index)).run(
        {"drug_name": "metoprolol"}
    )
    assert result["status"] == "success"


def test_query_failure_on_an_old_sqlite_names_the_requirement(
    make_tool, index_env, tool_mod, monkeypatch
):
    monkeypatch.setattr(tool_mod, "sqlite_problem", lambda: "needs SQLite 3.27.0")

    def failing(self, conn, arguments):
        raise tool_mod.sqlite3.OperationalError("error in tokenizer constructor")

    monkeypatch.setattr(tool_mod.StatPearlsSearchTool, "query", failing)
    result = make_tool("StatPearls_search").run({"query": "amitriptyline"})
    assert result["error_type"] == "index_error"
    assert "error in tokenizer constructor" in result["error"]
    assert "needs SQLite 3.27.0" in result["error"]


# ---------------------------------------------------------------------------
# output bounds
# ---------------------------------------------------------------------------

BOUND_CALLS = [
    ("StatPearls_search", {"query": "amitriptyline", "limit": 10}),
    (
        "StatPearls_search",
        {
            "query": "patients treatment management evaluation therapy",
            "limit": 10,
            "include_archived": True,
        },
    ),
    ("StatPearls_get_management", {"condition": "animal bites", "limit": 3}),
    (
        "StatPearls_get_management",
        {"condition": "toxicity", "limit": 3, "include_evaluation": True},
    ),
    ("StatPearls_get_chapter_section", {"chapter": "Animal Bites"}),
    ("StatPearls_get_chapter_section", {"chapter": "Animal Bites", "section": "Treatment"}),
    (
        "StatPearls_get_chapter_section",
        {"chapter": "Amitriptyline", "section": "Adverse Effects"},
    ),
    ("LactMed_get_drug", {"drug_name": "metoprolol"}),
    ("LactMed_get_drug", {"drug_name": "amitriptyline"}),
    ("LactMed_get_drug", {"drug_name": "amitriptyline", "section": "Drug Levels"}),
    ("LiverTox_get_drug", {"drug_name": "venlafaxine"}),
    ("LiverTox_get_drug", {"drug_name": "barbiturates"}),
    ("LiverTox_get_drug", {"drug_name": "Angiotensin II Receptor Antagonists"}),
    ("LiverTox_get_drug", {"drug_name": "metoprolol", "section": "case report"}),
]


@pytest.mark.parametrize("name, arguments", BOUND_CALLS)
def test_outputs_stay_within_8000_characters(call, name, arguments):
    result = call(name, **arguments)
    assert result["status"] == "success", result
    assert size(result) <= LIMIT


@pytest.mark.parametrize("limit", [2500, 4000])
@pytest.mark.parametrize("name, arguments", BOUND_CALLS)
def test_outputs_respect_a_smaller_configured_bound(
    make_tool, index_env, limit, name, arguments
):
    result = make_tool(name, max_output_chars=limit).run(arguments)
    assert size(result) <= limit
    assert result["status"] == "success"


def test_truncation_happens_at_word_boundaries_with_a_marker(make_tool, index_env):
    full = make_tool("LiverTox_get_drug").run({"drug_name": "venlafaxine"})
    small = make_tool("LiverTox_get_drug", max_output_chars=3000).run(
        {"drug_name": "venlafaxine"}
    )
    originals = {s["heading"]: s["text"] for s in full["data"]["sections"]}
    assert small["data"]["truncated_sections"]
    for section in small["data"]["sections"]:
        if section["heading"] not in small["data"]["truncated_sections"]:
            continue
        text = section["text"]
        assert re.search(
            r" \[\.\.\. \d+ more characters truncated; call again with "
            r"section='[^']+' for this section alone \.\.\.\]$",
            text,
        )
        kept = text[: text.rindex(" [... ")]
        original = originals[section["heading"]]
        assert original.startswith(kept)
        assert original[len(kept)].isspace()


def test_bound_text_unit(tool_mod):
    text = "alpha beta gamma delta " * 400 + 'µg – "quoted"\n' * 50
    for limit in (60, 100, 1000, 5000):
        cut, omitted = tool_mod.bound_text(text, limit, "hint")
        assert len(json.dumps(cut)) - 2 <= limit
        assert omitted > 0 and cut.endswith("; hint ...]")
        kept = cut[: cut.rindex(" [... ")]
        assert text.startswith(kept)
        assert kept == "" or text[len(kept)].isspace()
    assert tool_mod.bound_text("short", 100) == ("short", 0)
    giant = "x" * 500
    cut, omitted = tool_mod.bound_text(giant, 100)
    assert len(cut) <= 100 and "more characters truncated" in cut
    assert tool_mod.bound_text(giant, 10) == ("", 500)  # not even a marker fits
    cut, _ = tool_mod.bound_text(text, 45, "a long hint that does not fit")
    assert cut.endswith(" more characters truncated ...]") and len(cut) <= 45


def test_allocate_keeps_short_sections_whole(tool_mod):
    shares = tool_mod.allocate([100, 5000, 300, 8000], 2000, priority=[0])
    assert shares[0] == 100 and shares[2] == 300
    assert sum(shares) <= 2000 and shares[1] == shares[3]


# ---------------------------------------------------------------------------
# JSON specs and registration
# ---------------------------------------------------------------------------


def test_specs_load_and_are_complete(specs):
    assert sorted(specs) == sorted(TOOL_NAMES)
    for spec in specs.values():
        for key in ("name", "description", "parameter", "type", "return_schema"):
            assert spec[key]
        assert spec["requires_local_input"] is True
        assert spec["parameter"]["type"] == "object"
        assert set(spec["parameter"]["required"]) <= set(spec["parameter"]["properties"])
        assert "python -m tooluniverse.ncbi_bookshelf_index build" in spec["description"]


def test_spec_parameters_match_what_each_tool_reads(tool_mod, specs):
    for spec in specs.values():
        cls = getattr(tool_mod, spec["type"])
        read = set(re.findall(r'arguments\.get\("(\w+)"', inspect.getsource(cls.query)))
        assert read == set(spec["parameter"]["properties"]), spec["name"]


def test_spec_types_are_registered_tool_classes(tool_mod, specs):
    from tooluniverse._lazy_registry_static import STATIC_LAZY_REGISTRY
    from tooluniverse.tool_registry import get_tool_registry

    registry = get_tool_registry()
    for spec in specs.values():
        assert registry[spec["type"]] is getattr(tool_mod, spec["type"])
        assert STATIC_LAZY_REGISTRY[spec["type"]] == "ncbi_bookshelf_reference_tool"


def test_category_is_in_the_default_config():
    from tooluniverse.default_config import default_tool_files

    assert Path(default_tool_files["ncbi_bookshelf_reference"]) == SPEC_FILE


def test_spec_test_examples_validate_and_run(call, specs):
    jsonschema = pytest.importorskip("jsonschema")
    for spec in specs.values():
        assert spec["test_examples"]
        for example in spec["test_examples"]:
            jsonschema.validate(example, spec["parameter"])
            result = call(spec["name"], **example)
            assert result["status"] == "success", (spec["name"], example, result)
            jsonschema.validate(result, spec["return_schema"])


def test_tools_load_and_run_through_tooluniverse(index_env):
    from tooluniverse import ToolUniverse

    tu = ToolUniverse()
    tu.load_tools(tool_type=["ncbi_bookshelf_reference"])
    loaded = {t["name"] for t in tu.return_all_loaded_tools()}
    assert set(TOOL_NAMES) <= loaded
    for name, arguments in EXAMPLE_ARGS.items():
        result = tu.run_one_function({"name": name, "arguments": arguments})
        if isinstance(result, str):
            result = json.loads(result)
        assert result["status"] == "success", (name, result)
    bad = tu.run_one_function({"name": "LactMed_get_drug", "arguments": {}})
    if isinstance(bad, str):
        bad = json.loads(bad)
    assert "error" in bad


# ---------------------------------------------------------------------------
# treatment-section fallback in StatPearls_get_chapter_section
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "chapter, section, returned",
    [
        ("article-20545", "Treatment / Management", "Technique or Treatment"),
        ("Amitriptyline", "treatment", "Administration"),
        ("Amitriptyline", "surgical management", "Administration"),
    ],
)
def test_treatment_request_falls_back_to_the_chapters_treatment_section(
    call, chapter, section, returned
):
    result = call("StatPearls_get_chapter_section", chapter=chapter, section=section)
    assert result["status"] == "success", result
    assert result["data"]["section"] == returned
    note = result["data"]["section_note"]
    assert "no section matching '%s'" % section in note and returned in note
    assert size(result) <= LIMIT


def test_a_matching_treatment_section_carries_no_fallback_note(call):
    result = call(
        "StatPearls_get_chapter_section",
        chapter="Animal Bites",
        section="Treatment / Management",
    )
    assert result["data"]["section"] == "Treatment / Management"
    assert "section_note" not in result["data"]


@pytest.mark.parametrize(
    "chapter, section, returned",
    [
        ("Animal Bites", "treatment options", "Treatment / Management"),
        ("Animal Bites", "antibiotic therapy", "Treatment / Management"),
        ("Animal Bites", "diagnostic workup", "Evaluation"),
        ("Amitriptyline", "management of overdose", "Toxicity"),
        ("Amitriptyline", "dose adjustment", "Administration"),
    ],
)
def test_one_word_of_a_longer_request_finds_its_heading(call, chapter, section, returned):
    result = call("StatPearls_get_chapter_section", chapter=chapter, section=section)
    assert result["data"]["section"] == returned
    assert "section_note" not in result["data"]


def test_fallback_headings(tool_mod):
    assert tool_mod.fallback_headings("Treatment / Management") == tool_mod.MANAGEMENT_HEADINGS
    assert tool_mod.fallback_headings("medical therapy") == tool_mod.MANAGEMENT_HEADINGS
    assert tool_mod.fallback_headings("diagnostic work up") == tool_mod.EVALUATION_HEADINGS
    assert tool_mod.fallback_headings("workup") == tool_mod.EVALUATION_HEADINGS
    assert tool_mod.fallback_headings("Embryology of the left ventricle") == ()
    assert tool_mod.fallback_headings("") == ()


def test_install_hashes_a_downloaded_archive_once(index_mod, monkeypatch, tmp_path):
    import tarfile

    archive = tmp_path / "src.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(FIXTURES / "lactmed", arcname="lactmed_NBK501922")
    data = archive.read_bytes()
    monkeypatch.setattr(
        index_mod,
        "file_list",
        lambda session: [["90/6c/lactmed_NBK501922.tar.gz", "", "", "", "NBK501922", ""]],
    )
    monkeypatch.setattr(
        index_mod,
        "_session",
        lambda: _Session([_Response(200, data, {"Content-Length": str(len(data))})]),
    )
    hashed = []
    real = index_mod.sha256_file
    monkeypatch.setattr(
        index_mod, "sha256_file", lambda path: hashed.append(Path(path).name) or real(path)
    )
    index_mod.install(["lactmed"], str(tmp_path / "index"), keep_archives=True, log=quiet)
    assert hashed.count("lactmed_NBK501922.tar.gz") == 1


def test_management_drops_low_ranked_chapters_under_a_tiny_bound(make_tool, index_env):
    result = make_tool("StatPearls_get_management", max_output_chars=2500).run(
        {"condition": "toxicity", "limit": 3, "include_evaluation": True}
    )
    assert size(result) <= 2500
    assert result["metadata"]["dropped_to_fit_output_bound"] is True
    assert result["metadata"]["returned"] == len(result["data"]) < 3
    assert all(len(item["text"]) > 100 for item in result["data"])
