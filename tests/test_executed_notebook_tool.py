"""Tests for ExecutedNotebookTool (read_executed_notebook).

The tool reads a notebook the user names for review. It takes an explicit
notebook_path only and never searches a data folder for a pre-run notebook to
take answers from.
"""

import json

import pytest


@pytest.fixture
def tool():
    from tooluniverse.executed_notebook_tool import ExecutedNotebookTool

    return ExecutedNotebookTool({"name": "read_executed_notebook"})


def _write_nb(path, cells):
    """Write a minimal .ipynb with the given list of (cell_type, source) tuples."""
    nb = {
        "cells": [
            {"cell_type": ct, "source": src, "outputs": [], "metadata": {}}
            for ct, src in cells
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    path.write_text(json.dumps(nb))


class TestNotebookBasic:
    def test_reads_cells(self, tool, tmp_path):
        nb = tmp_path / "analysis.ipynb"
        _write_nb(nb, [("code", "import pandas as pd"), ("code", "df.head()")])
        result = tool.run({"notebook_path": str(nb)})
        assert result["status"] == "success"
        assert result["data"]["total_cells"] == 2
        assert len(result["data"]["cells"]) == 2

    def test_missing_notebook_errors(self, tool):
        result = tool.run({"notebook_path": "/nonexistent/path.ipynb"})
        assert result["status"] == "error"

    def test_requires_an_argument(self, tool):
        result = tool.run({})
        assert result["status"] == "error"

    def test_does_not_search_a_data_folder(self, tool, tmp_path):
        # A folder argument is not an entry point: the tool must not go looking
        # for a pre-run notebook next to an analysis's data.
        _write_nb(tmp_path / "analysis.ipynb", [("code", "x = 1")])
        result = tool.run({"data_folder": str(tmp_path)})
        assert result["status"] == "error"
        assert "notebook_path" in result["error"]

    def test_search_filter(self, tool, tmp_path):
        nb = tmp_path / "n.ipynb"
        _write_nb(nb, [("code", "padj < 0.05"), ("code", "unrelated code")])
        result = tool.run({"notebook_path": str(nb), "search": "padj"})
        assert result["data"]["n_matches"] == 1


class TestPreprocessingDetection:
    def test_flags_sample_exclusion_cell(self, tool, tmp_path):
        nb = tmp_path / "deseq.ipynb"
        _write_nb(nb, [
            ("code", "counts <- read_csv('raw_counts.csv')"),
            ("code", "# Filter out samples that don't correlate well\n"
                     "counts <- select(counts, -resub5, -resub10)"),
            ("code", "dds <- DESeq(dds)"),
        ])
        result = tool.run({"notebook_path": str(nb)})
        data = result["data"]
        assert data["n_preprocessing_cells"] == 1
        assert data["preprocessing_cells"][0]["idx"] == 1
        assert "preprocessing_note" in data
        assert "reference answer" not in data["preprocessing_note"]

    def test_no_preprocessing_when_absent(self, tool, tmp_path):
        nb = tmp_path / "clean.ipynb"
        _write_nb(nb, [("code", "x = 1"), ("code", "print(x)")])
        result = tool.run({"notebook_path": str(nb)})
        assert "preprocessing_cells" not in result["data"]

    def test_detects_outlier_keyword(self, tool, tmp_path):
        nb = tmp_path / "o.ipynb"
        _write_nb(nb, [("code", "# remove outlier samples before modeling\nok = True")])
        result = tool.run({"notebook_path": str(nb)})
        assert result["data"]["n_preprocessing_cells"] == 1

    def test_markdown_cells_not_flagged(self, tool, tmp_path):
        # Only code cells perform exclusions; prose mentioning "outlier"
        # should not be flagged as a preprocessing step.
        nb = tmp_path / "md.ipynb"
        _write_nb(nb, [("markdown", "We will exclude outlier samples here.")])
        result = tool.run({"notebook_path": str(nb)})
        assert "preprocessing_cells" not in result["data"]
