"""Tests for ExecutedNotebookTool, including preprocessing-cell detection."""

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


class TestExecutedNotebookBasic:
    def test_reads_cells(self, tool, tmp_path):
        nb = tmp_path / "analysis_executed.ipynb"
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

    def test_search_filter(self, tool, tmp_path):
        nb = tmp_path / "n_executed.ipynb"
        _write_nb(nb, [("code", "padj < 0.05"), ("code", "unrelated code")])
        result = tool.run({"notebook_path": str(nb), "search": "padj"})
        assert result["data"]["n_matches"] == 1


class TestPreprocessingDetection:
    def test_flags_sample_exclusion_cell(self, tool, tmp_path):
        nb = tmp_path / "deseq_executed.ipynb"
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

    def test_no_preprocessing_when_absent(self, tool, tmp_path):
        nb = tmp_path / "clean_executed.ipynb"
        _write_nb(nb, [("code", "x = 1"), ("code", "print(x)")])
        result = tool.run({"notebook_path": str(nb)})
        assert "preprocessing_cells" not in result["data"]

    def test_detects_outlier_keyword(self, tool, tmp_path):
        nb = tmp_path / "o_executed.ipynb"
        _write_nb(nb, [("code", "# remove outlier samples before modeling\nok = True")])
        result = tool.run({"notebook_path": str(nb)})
        assert result["data"]["n_preprocessing_cells"] == 1

    def test_markdown_cells_not_flagged(self, tool, tmp_path):
        # Only code cells perform exclusions; prose mentioning "outlier"
        # should not be flagged as a preprocessing step.
        nb = tmp_path / "md_executed.ipynb"
        _write_nb(nb, [("markdown", "We will exclude outlier samples here.")])
        result = tool.run({"notebook_path": str(nb)})
        assert "preprocessing_cells" not in result["data"]
