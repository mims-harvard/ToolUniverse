import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from tooluniverse.database_setup import cli


pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clean_embedding_environment(monkeypatch):
    monkeypatch.delenv("EMBED_PROVIDER", raising=False)
    monkeypatch.delenv("EMBED_MODEL", raising=False)


def _run(monkeypatch, *arguments):
    monkeypatch.setattr(sys, "argv", ["tu-datastore", *arguments])
    cli.main()


def test_build_validates_and_normalizes_document_rows(monkeypatch, tmp_path):
    docs_path = tmp_path / "docs.json"
    docs_path.write_text(
        json.dumps(
            [
                {"doc_key": "a", "text": "Alpha", "metadata": {"kind": "A"}},
                ["b", "Beta", {"kind": "B"}],
            ]
        ),
        encoding="utf-8",
    )
    db_path = tmp_path / "test.db"

    with patch.object(cli, "build_collection") as build:
        _run(
            monkeypatch,
            "build",
            "--collection",
            "study",
            "--docs-json",
            str(docs_path),
            "--db",
            str(db_path),
            "--provider",
            "local",
            "--model",
            "model-name",
            "--overwrite",
        )

    build.assert_called_once_with(
        db_path=str(db_path),
        collection="study",
        docs=[
            ("a", "Alpha", {"kind": "A"}, None),
            ("b", "Beta", {"kind": "B"}, None),
        ],
        embed_provider="local",
        embed_model="model-name",
        overwrite=True,
    )


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"doc_key": "a", "text": "Alpha"}, "must contain a list"),
        ([{"text": "Alpha"}], "requires a non-empty doc_key"),
        ([{"doc_key": "a", "text": 3}], "requires string text"),
        ([{"doc_key": "a", "text": "Alpha", "metadata": []}], "metadata must be"),
        ([["a", "Alpha"]], "3/4-item array"),
        ([{"doc_key": "a", "text": "Alpha", "text_hash": 4}], "text_hash must"),
    ],
)
def test_document_json_validation_fails_before_build(tmp_path, payload, message):
    docs_path = tmp_path / "docs.json"
    docs_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(SystemExit, match=message):
        cli.load_docs_json(docs_path)


def test_invalid_json_has_a_concise_error(tmp_path):
    docs_path = tmp_path / "docs.json"
    docs_path.write_text("{", encoding="utf-8")

    with pytest.raises(SystemExit, match="Could not read document JSON"):
        cli.load_docs_json(docs_path)


def test_quickbuild_dispatches_packaged_documents(monkeypatch, tmp_path):
    docs = [("paper.md", "Evidence", {"source": "file"}, "hash")]
    db_path = tmp_path / "quick.db"

    with (
        patch.object(cli, "pack_folder", return_value=docs) as pack,
        patch.object(cli, "resolve_db_path", return_value=str(db_path)),
        patch.object(cli, "build_collection") as build,
    ):
        _run(
            monkeypatch,
            "quickbuild",
            "--name",
            "papers",
            "--from-folder",
            str(tmp_path),
            "--provider",
            "local",
            "--model",
            "model-name",
        )

    pack.assert_called_once_with(str(tmp_path))
    assert build.call_args.kwargs["docs"] == docs
    assert build.call_args.kwargs["collection"] == "papers"


def test_quickbuild_rejects_a_folder_without_supported_files(monkeypatch, tmp_path):
    with (
        patch.object(cli, "pack_folder", return_value=[]),
        pytest.raises(SystemExit, match="No supported files found"),
    ):
        _run(
            monkeypatch,
            "quickbuild",
            "--name",
            "papers",
            "--from-folder",
            str(tmp_path),
        )


def test_keyword_search_never_requires_embedding_configuration(
    monkeypatch, tmp_path, capsys
):
    db_path = tmp_path / "study.db"
    result = [{"doc_key": "a", "score": 1.0}]

    with patch.object(cli, "search", return_value=result) as search:
        _run(
            monkeypatch,
            "search",
            "--collection",
            "study",
            "--query",
            "TP53",
            "--db",
            str(db_path),
            "--method",
            "keyword",
        )

    assert search.call_args.kwargs["embed_provider"] is None
    assert search.call_args.kwargs["embed_model"] is None
    assert json.loads(capsys.readouterr().out) == result


def test_embedding_search_can_use_collection_metadata_without_cli_model(
    monkeypatch, tmp_path
):
    db_path = tmp_path / "study.db"

    with patch.object(cli, "search", return_value=[]) as search:
        _run(
            monkeypatch,
            "search",
            "--collection",
            "study",
            "--query",
            "BRCA1",
            "--db",
            str(db_path),
            "--method",
            "embedding",
        )

    assert search.call_args.kwargs["embed_provider"] is None
    assert search.call_args.kwargs["embed_model"] is None


def test_search_uses_optional_embedding_environment_overrides(monkeypatch, tmp_path):
    monkeypatch.setenv("EMBED_PROVIDER", "local")
    monkeypatch.setenv("EMBED_MODEL", "environment-model")

    with patch.object(cli, "search", return_value=[]) as search:
        _run(
            monkeypatch,
            "search",
            "--collection",
            "study",
            "--query",
            "EGFR",
            "--db",
            str(tmp_path / "study.db"),
        )

    assert search.call_args.kwargs["embed_provider"] == "local"
    assert search.call_args.kwargs["embed_model"] == "environment-model"


@pytest.mark.parametrize(
    "arguments",
    [
        (),
        ("search", "--collection", "study", "--query", "q", "--top-k", "0"),
        ("search", "--collection", "study", "--query", "q", "--alpha", "-0.1"),
        ("search", "--collection", "study", "--query", "q", "--alpha", "1.1"),
        ("search", "--collection", "../escape", "--query", "q"),
        ("build", "--collection", "a/b", "--docs-json", "docs.json"),
    ],
)
def test_invalid_cli_inputs_exit_with_usage_error(monkeypatch, arguments):
    monkeypatch.setattr(sys, "argv", ["tu-datastore", *arguments])

    with pytest.raises(SystemExit) as exc_info:
        cli.main()

    assert exc_info.value.code == 2


def test_sync_upload_dispatches_all_options(monkeypatch):
    with patch.object(cli, "sync_upload") as upload:
        _run(
            monkeypatch,
            "sync-hf",
            "upload",
            "--collection",
            "study",
            "--repo",
            "lab/study",
            "--no-private",
            "--tool-json",
            "a.json",
            "b.json",
        )

    upload.assert_called_once_with(
        collection="study",
        repo="lab/study",
        private=False,
        tool_json=["a.json", "b.json"],
    )


def test_sync_download_dispatches_all_options(monkeypatch):
    with patch.object(cli, "sync_download") as download:
        _run(
            monkeypatch,
            "sync-hf",
            "download",
            "--repo",
            "lab/study",
            "--collection",
            "study",
            "--overwrite",
            "--include-tools",
        )

    download.assert_called_once_with(
        repo="lab/study",
        collection="study",
        overwrite=True,
        include_tools=True,
    )


def test_add_tool_copies_to_the_user_directory_and_requires_overwrite(
    monkeypatch, tmp_path
):
    source = tmp_path / "source.json"
    source.write_text('{"name": "Example"}', encoding="utf-8")
    destination_dir = tmp_path / "user-tools"
    monkeypatch.setattr(cli, "USER_TOOLS_DIR", str(destination_dir))

    cli.add_tool(str(source), name="example")
    destination = destination_dir / "example.json"
    assert destination.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")

    with pytest.raises(SystemExit, match="already exists"):
        cli.add_tool(str(source), name="example")

    source.write_text('{"name": "Updated"}', encoding="utf-8")
    cli.add_tool(str(source), name="example", overwrite=True)
    assert json.loads(destination.read_text(encoding="utf-8"))["name"] == "Updated"


@pytest.mark.parametrize("name", ["../escape", "folder/tool", "folder\\tool"])
def test_add_tool_rejects_destination_path_traversal(monkeypatch, tmp_path, name):
    source = tmp_path / "source.json"
    source.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(cli, "USER_TOOLS_DIR", str(tmp_path / "user-tools"))

    with pytest.raises(SystemExit, match="must not contain path separators"):
        cli.add_tool(str(source), name=name)


def test_provider_and_model_resolve_from_cli_or_environment(monkeypatch):
    monkeypatch.setenv("EMBED_PROVIDER", "local")
    monkeypatch.setenv("EMBED_MODEL", "environment-model")

    assert cli.resolve_provider_model(None, None) == ("local", "environment-model")
    assert cli.resolve_provider_model("openai", "explicit-model") == (
        "openai",
        "explicit-model",
    )


def test_default_database_path_uses_the_embeddings_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "get_user_cache_dir", lambda: str(tmp_path))

    path = cli.resolve_db_path(None, "study")

    assert path == str(tmp_path / "embeddings" / "study.db")
    assert (tmp_path / "embeddings").is_dir()
