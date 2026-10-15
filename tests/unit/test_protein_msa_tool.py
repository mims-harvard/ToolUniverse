"""Synthetic format, query and depth controls; no invented homology claims."""

import json
from pathlib import Path

import jsonschema
import pytest

from tooluniverse import ToolUniverse
from tooluniverse.protein_msa_tool import ProteinMSAInventoryTool

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads(
    (ROOT / "src/tooluniverse/data/protein_msa_tools.json").read_text()
)[0]
FIXTURE = ROOT / "tests/fixtures/protein_msa/insertion_duplicate.a3m"


def run(text=None, **kwargs):
    args = kwargs if text is None else dict(kwargs, alignment_content=text)
    result = ProteinMSAInventoryTool(CONFIG).run(args)
    jsonschema.validate(result, CONFIG["return_schema"])
    return result


def data(text=None, **kwargs):
    r = run(text, **kwargs)
    assert r["status"] == "success", r
    return r["data"]


def test_query_only_is_separate_from_repeated_depth():
    one = data(">private_query\nACDE\n", expected_query_sequence="ACDE")
    assert one["query_only"] and not one["has_distinct_nonquery_sequence"]
    repeated = data(">q\nACDE\n>a\nACDE\n>b\nACDE\n")
    assert not repeated["query_only"]
    assert repeated["row_count"] == 3 and repeated["unique_aligned_row_count"] == 1
    assert repeated["duplicate_aligned_row_count"] == 2
    assert not repeated["has_distinct_nonquery_sequence"]
    assert not repeated["homology_verified"] and not repeated["folding_verified"]
    assert "private_query" not in json.dumps(one) and "ACDE" not in json.dumps(one)


def test_insertions_do_not_inflate_aligned_unique_depth():
    d = data(alignment_path=str(FIXTURE), expected_query_sequence="ACDE")
    assert d["row_count"] == 4 and d["unique_aligned_row_count"] == 3
    assert d["duplicate_aligned_row_count"] == 1
    assert d["unique_nonempty_nonquery_row_count"] == 1
    assert d["nonempty_nonquery_row_count"] == 2 and d["all_gap_row_count"] == 1
    assert d["insertion_residue_count"] == 4
    assert d["mean_query_site_coverage"] == 0.625
    assert d["mean_query_site_identity"] == 0.625
    assert d["expected_query_matches"] is True


def test_a3m_dots_are_insertion_gaps_and_multiline_is_supported():
    d = data("# comment\n>q\nAC\nDE\n>a\nACa..D-\n")
    assert d["aligned_column_count"] == 4
    assert d["insertion_residue_count"] == 1 and d["insertion_gap_count"] == 2


def test_aligned_fasta_lowercase_is_not_an_insertion():
    d = data(">q\nacde\n>a\na.d-\n", format="aligned_fasta")
    assert d["query_residue_count"] == 4 and d["insertion_residue_count"] == 0
    assert d["mean_query_site_coverage"] == 0.75
    assert d["mean_query_site_identity"] == 0.75


def test_gapped_query_denominator_and_expected_match():
    d = data(">q\nA-C\n>a\nADC\n", expected_query_sequence="ac")
    assert d["query_residue_count"] == 2 and d["query_gap_count"] == 1
    assert d["mean_query_site_coverage"] == 1 and d["mean_query_site_identity"] == 1
    assert d["expected_query_matches"]
    mismatch = data(">q\nAC\n", expected_query_sequence="AD")
    assert mismatch["expected_query_matches"] is False and mismatch["warnings"]


def test_truncation_keeps_all_counts_and_digest_is_identical(tmp_path):
    text = FIXTURE.read_text()
    p = tmp_path / "input.a3m"
    p.write_text(text)
    full = data(text)
    bounded = data(alignment_path=str(p), max_row_details=1)
    assert len(bounded["row_details"]) == 1 and bounded["row_details_truncated"]
    for key in ["row_count", "unique_aligned_row_count", "input_sha256"]:
        assert bounded[key] == full[key]
    assert data(text, max_row_details=0)["row_details"] == []


@pytest.mark.parametrize(
    "text",
    [
        "ACDE",
        ">\nACDE",
        ">q\n",
        ">q\nACDE\n>a\nACD",
        ">q\nA1CD",
        ">q\nAC*D",
        ">q\nAC/DE",
        ">q\n----",
        "#53\t1\n>q\nACDE",
        "#2,2\t1,1\n>q\nACDE",
        ">q\nacde",
        "",
    ],
)
def test_malformed_or_unsupported_alignment(text):
    assert run(text)["status"] == "error"


@pytest.mark.parametrize(
    "args",
    [
        {},
        {"alignment_content": ">q\nAC", "alignment_path": "nope"},
        {"alignment_content": 1},
        {"alignment_path": "/this/path/does/not/exist"},
        {"alignment_content": ">q\nAC", "format": "stockholm"},
        {"alignment_content": ">q\nAC", "expected_query_sequence": "A-C"},
        {"alignment_content": ">q\nAC", "expected_query_sequence": ""},
        {"alignment_content": ">q\nAC", "max_row_details": True},
        {"alignment_content": ">q\nAC", "max_row_details": 101},
    ],
)
def test_invalid_arguments_have_error_envelope(args):
    assert run(**args)["status"] == "error"


def test_explicit_null_alternative_and_default_options():
    args = {
        "alignment_content": ">q\nAC",
        "alignment_path": None,
        "format": None,
        "max_row_details": None,
        "expected_query_sequence": None,
    }
    jsonschema.validate(args, CONFIG["parameter"])
    assert run(**args)["status"] == "success"


def test_input_bounds_apply_to_path_and_inline(monkeypatch, tmp_path):
    import tooluniverse.protein_msa_tool as module

    monkeypatch.setattr(module, "MAX_BYTES", 10)
    text = ">q\n" + "A" * 10
    p = tmp_path / "oversized.a3m"
    p.write_text(text)
    assert run(text)["status"] == "error"
    assert run(alignment_path=str(p))["status"] == "error"


def test_row_and_column_limits(monkeypatch):
    import tooluniverse.protein_msa_tool as module

    monkeypatch.setattr(module, "MAX_ROWS", 2)
    assert run(">q\nAC\n>a\nAC\n>b\nAC")["status"] == "error"
    monkeypatch.setattr(module, "MAX_COLUMNS", 2)
    assert run(">q\nACD")["status"] == "error"


def test_registered_tool_is_lazily_discovered_and_callable():
    tu = ToolUniverse()
    tu.load_tools(tool_type=["protein_msa"])
    result = tu.run_one_function(
        {"name": CONFIG["name"], "arguments": {"alignment_path": str(FIXTURE)}}
    )
    jsonschema.validate(result, CONFIG["return_schema"])
    assert result["status"] == "success" and result["data"]["row_count"] == 4


def test_schemas_are_valid():
    jsonschema.Draft7Validator.check_schema(CONFIG["parameter"])
    jsonschema.Draft7Validator.check_schema(CONFIG["return_schema"])
    for example in CONFIG["test_examples"]:
        jsonschema.validate(example, CONFIG["parameter"])


def test_generated_wrapper_uses_registered_tool_with_nullable_sources(monkeypatch):
    import importlib

    module = importlib.import_module("tooluniverse.tools.Protein_MSA_inspect")
    tu = ToolUniverse()
    tu.load_tools(tool_type=["protein_msa"])
    monkeypatch.setattr(module, "get_shared_client", lambda: tu)
    r = module.Protein_MSA_inspect(
        alignment_content=">q\nACDE\n", expected_query_sequence="ACDE"
    )
    jsonschema.validate(r, CONFIG["return_schema"])
    assert r["data"]["expected_query_matches"]


def test_empty_format_is_not_silently_treated_as_a3m():
    assert run(">q\nACDE", format="")["status"] == "error"
