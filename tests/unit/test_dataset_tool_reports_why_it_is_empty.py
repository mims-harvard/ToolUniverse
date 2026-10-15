"""A dataset that would not load should say why, not "or is empty".

drugbank_full_search reads a parquet file, and pandas needs pyarrow or
fastparquet for that -- neither is a ToolUniverse dependency. The ImportError
was caught into an empty DataFrame, and run() then reported "Dataset not loaded
or is empty", which reads as an upstream or data problem. The HF repo and the
file are both fine: agenticx/DrugbankRawParquet lists drugbank_raw.parquet.

The same sentence also covered an unsupported extension, which fell through
every branch without assigning self.dataset at all.
"""

import pytest

from tooluniverse.dataset_tool import DatasetTool

pytestmark = pytest.mark.unit


def _config(path, tmp_path):
    return {
        "name": "fixture_tool",
        "description": "test",
        "type": "DatasetTool",
        "local_dataset_path": str(path),
        "query_schema": {"search_fields": ["name"], "limit": 5},
        "parameter": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
        },
    }


def test_a_missing_parquet_engine_is_named(tmp_path, monkeypatch):
    import pandas as pd

    path = tmp_path / "drugbank_raw.parquet"
    path.write_bytes(b"PAR1 not really a parquet file")

    def no_engine(*args, **kwargs):
        raise ImportError("Unable to find a usable engine to read parquet")

    monkeypatch.setattr(pd, "read_parquet", no_engine)

    tool = DatasetTool(_config(path, tmp_path))
    result = tool.run({"query": "DB00945"})

    assert result["status"] == "error"
    assert "pyarrow" in result["error"]
    assert "drugbank_raw.parquet" in result["error"]
    assert "or is empty" not in result["error"]


def test_an_unsupported_extension_is_named(tmp_path):
    path = tmp_path / "data.sqlite3"
    path.write_bytes(b"SQLite format 3\x00")

    tool = DatasetTool(_config(path, tmp_path))
    result = tool.run({"query": "anything"})

    assert result["status"] == "error"
    assert "Unsupported dataset format" in result["error"]
    assert "data.sqlite3" in result["error"]
    assert ".parquet" in result["error"], "the message should list what works"


def test_a_dataset_that_loads_still_works(tmp_path):
    path = tmp_path / "rows.csv"
    path.write_text("name,id\naspirin,DB00945\nibuprofen,DB01050\n", encoding="utf-8")

    tool = DatasetTool(_config(path, tmp_path))
    result = tool.run({"query": "aspirin"})

    # A successful search returns the payload itself, with no status key.
    assert "error" not in result
    assert result["total_results"] == 1
    assert result["results"][0]["id"] == "DB00945"


def test_a_genuinely_empty_dataset_still_says_empty(tmp_path):
    path = tmp_path / "rows.csv"
    path.write_text("name,id\n", encoding="utf-8")

    tool = DatasetTool(_config(path, tmp_path))
    result = tool.run({"query": "aspirin"})

    assert result["status"] == "error"
    assert "empty" in result["error"]
