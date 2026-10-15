"""The R-backed tools must treat their arguments as data, not as R code.

``DESeq2Tool`` and ``EdgeRLimmaTool`` build an R script as text. A value pasted
into that text bare -- a path, a design formula, a factor name, a threshold --
is R code, and tool arguments come from a model or an upstream request. These
tests run without R: they capture the script the tool would have run and assert
that a payload crafted to break out of its literal either never reaches the
script or reaches it as a quoted string.

The payloads all try to run ``system(...)``, because that is the step from "R
code runs" to "a shell command runs as the server user".
"""

import json
import re

import pytest

from tooluniverse.deseq2_tool import DESeq2Tool
from tooluniverse.edger_limma_tool import EdgeRLimmaTool
from tooluniverse.r_literals import r_formula, r_identifier, r_number, r_string

pytestmark = pytest.mark.unit


@pytest.fixture
def dataset(tmp_path):
    """A counts/metadata pair small enough that only the script matters."""
    counts = tmp_path / "counts.csv"
    counts.write_text("gene,t1,t2,c1,c2\nG1,10,12,3,4\nG2,5,6,7,8\n")
    meta = tmp_path / "meta.csv"
    meta.write_text(
        "sample,condition\nt1,treated\nt2,treated\nc1,control\nc2,control\n"
    )
    return str(counts), str(meta)


@pytest.fixture
def captured(monkeypatch):
    """Capture the R script instead of running it; nothing needs R installed."""
    scripts = []

    class _Result:
        returncode = 1
        stdout = ""
        stderr = "captured"

    def fake_deseq2(r_script, timeout=300):
        scripts.append(r_script)
        return _Result()

    def fake_run(argv, **kwargs):
        scripts.append(argv[-1])
        return _Result()

    monkeypatch.setattr(DESeq2Tool, "_run_rscript", staticmethod(fake_deseq2))
    monkeypatch.setattr("tooluniverse.edger_limma_tool.subprocess.run", fake_run)
    return scripts


def _deseq2():
    return DESeq2Tool({"name": "run_deseq2_analysis", "parameter": {}})


def _edger():
    return EdgeRLimmaTool({"name": "de", "parameter": {}})


_R_STRING = re.compile(r'"(?:[^"\\]|\\.)*"')


def _code_only(script):
    """The script with every string literal removed -- what R will execute.

    A payload is harmless exactly when it survives only inside a literal, so
    whatever is left here is the part that could run.
    """
    return _R_STRING.sub('""', script)


def _assert_inert(scripts, payload):
    """A payload that reached the script must sit inside a string literal."""
    for script in scripts:
        code = _code_only(script)
        assert payload not in code, "payload reached the R script as code:\n" + code
        assert "system(" not in code, "a call the tool never writes is in:\n" + code
        if payload in script:
            assert json.dumps(payload) in script, (
                "payload is in the script but not as the literal the tool "
                "would have written:\n" + script
            )


# --- the design formula, which is R code in both tools -----------------------

DESIGN_PAYLOADS = [
    "~ condition\"; system('touch /tmp/pwned'); x <- \"",
    "~ condition); system('touch /tmp/pwned'); y <- (",
    "~ condition; system('touch /tmp/pwned')",
]


@pytest.mark.parametrize("payload", DESIGN_PAYLOADS)
def test_deseq2_refuses_a_design_that_is_not_a_formula(payload, dataset, captured):
    counts, meta = dataset
    out = _deseq2().run(
        {"counts_file": counts, "metadata_file": meta, "design": payload}
    )
    assert out["status"] == "error"
    assert "design" in out["error"]
    _assert_inert(captured, payload)


@pytest.mark.parametrize("payload", DESIGN_PAYLOADS)
def test_edger_refuses_a_design_that_is_not_a_formula(payload, dataset, captured):
    counts, meta = dataset
    out = _edger().run(
        {
            "counts_file": counts,
            "metadata_file": meta,
            "design": payload,
            "contrast": "condition,treated,control",
            "method": "edger",
        }
    )
    assert out["status"] == "error"
    assert "design" in out["error"]
    _assert_inert(captured, payload)


def test_a_backquoted_column_name_reaches_r_only_as_a_literal(dataset, captured):
    """R needs backticks for a column whose name has a space in it.

    Refusing them would break a legitimate design, so these pass the shape
    check -- what keeps them harmless is that the formula is quoted.
    """
    payload = "~ condition + `a\"; system('x'); b <- \"`"
    counts, meta = dataset
    _deseq2().run({"counts_file": counts, "metadata_file": meta, "design": payload})
    _edger().run(
        {
            "counts_file": counts,
            "metadata_file": meta,
            "design": payload,
            "contrast": "condition,treated,control",
            "method": "edger",
        }
    )
    assert len(captured) == 2, "the design should have reached both tools"
    _assert_inert(captured, payload)


def test_an_ordinary_design_is_still_accepted(dataset, captured):
    """The check must not reject the formulas the tools document."""
    counts, meta = dataset
    for design in ("~ condition", "~ batch + condition", "~condition", "~ a*b"):
        out = _edger().run(
            {
                "counts_file": counts,
                "metadata_file": meta,
                "design": design,
                "contrast": "condition,treated,control",
                "method": "edger",
            }
        )
        # Reaches R (and fails there, since R is stubbed out) rather than being
        # refused by the formula check.
        assert "must be a formula" not in out.get("error", ""), design
    assert captured, "no script was built for a valid design"


# --- the other arguments -----------------------------------------------------


def test_a_factor_name_is_looked_up_by_string_not_spelled_into_the_source(
    dataset, captured
):
    """``ref_level``'s factor used to be written as ``meta$<name>``."""
    counts, meta = dataset
    payload = "condition; system('touch /tmp/pwned'); meta$condition"
    out = _deseq2().run(
        {
            "counts_file": counts,
            "metadata_file": meta,
            "design": "~ condition",
            "ref_level": f"{payload},control",
        }
    )
    assert out["status"] == "error"  # R is stubbed, so every run ends in error
    _assert_inert(captured, payload)
    assert "meta$condition;" not in "".join(captured)


def test_a_threshold_must_be_a_number(dataset, captured):
    """Numbers are written unquoted, so a string there is also code."""
    counts, meta = dataset
    payload = "0.05); system('touch /tmp/pwned'); ("
    for tool, args in (
        (_deseq2(), {"alpha": payload}),
        (_edger(), {"lfc_threshold": payload, "contrast": "condition,treated,control"}),
        (_edger(), {"fdr_threshold": payload, "contrast": "condition,treated,control"}),
    ):
        out = tool.run(
            {
                "counts_file": counts,
                "metadata_file": meta,
                "design": "~ condition",
                "method": "edger",
                **args,
            }
        )
        assert out["status"] == "error"
        assert "must be a number" in out["error"]
    _assert_inert(captured, payload)


def test_enrichgo_refuses_an_organism_that_is_not_a_package_name(tmp_path, captured):
    """``organism`` is the one argument that stays R code, so it is checked."""
    genes = tmp_path / "genes.txt"
    genes.write_text("ENSG00000141510\n")
    payload = "org.Hs.eg.db); system('touch /tmp/pwned'); library(stats"
    out = _deseq2().run(
        {
            "operation": "enrichgo",
            "gene_list_file": str(genes),
            "organism": payload,
        }
    )
    assert out["status"] == "error"
    assert "organism" in out["error"]
    _assert_inert(captured, payload)


def test_a_quote_in_a_file_path_cannot_close_the_literal(monkeypatch, captured):
    """A path is data too, and a quote in one used to end the R string.

    The paths are not created: a name like this is refused outright by some
    filesystems, and what is under test is how the path is written into R.
    """
    counts = "/data/c\"; system('touch /tmp/pwned'); x.csv"
    meta = "/data/m\"; system('touch /tmp/pwned'); y.csv"
    monkeypatch.setattr("tooluniverse.deseq2_tool.os.path.exists", lambda p: True)
    monkeypatch.setattr("tooluniverse.edger_limma_tool.os.path.exists", lambda p: True)
    _deseq2().run(
        {"counts_file": counts, "metadata_file": meta, "design": "~ condition"}
    )
    _edger().run(
        {
            "counts_file": counts,
            "metadata_file": meta,
            "design": "~ condition",
            "contrast": "condition,treated,control",
            "method": "edger",
        }
    )
    assert len(captured) == 2, "both tools should have built a script"
    for script in captured:
        assert json.dumps(counts) in script
        assert "system(" not in _code_only(script)


# --- the helpers themselves --------------------------------------------------


def test_r_string_escapes_what_r_would_otherwise_read_as_syntax():
    assert r_string('a"b') == '"a\\"b"'
    assert r_string("a\\b") == '"a\\\\b"'
    assert r_string("a\nb") == '"a\\nb"'
    assert r_string(None) == '""'


def test_r_number_accepts_numeric_strings_and_refuses_the_rest():
    assert float(r_number("0.5", "x")) == 0.5
    assert float(r_number(2, "x")) == 2.0
    for bad in ("nan", "inf", "1; system('x')", None, [1]):
        with pytest.raises(ValueError, match="x must be"):
            r_number(bad, "x")


def test_r_identifier_accepts_a_package_name_and_refuses_code():
    assert r_identifier("org.Hs.eg.db", "organism") == "org.Hs.eg.db"
    for bad in ("org.Hs.eg.db)", "1org", "", "a b", None):
        with pytest.raises(ValueError, match="organism must be"):
            r_identifier(bad, "organism")


def test_r_formula_requires_a_tilde():
    assert r_formula("~ condition", "design") == '"~ condition"'
    for bad in ("condition", "", "~ condition; q()", '~ "x"'):
        with pytest.raises(ValueError, match="design must be"):
            r_formula(bad, "design")


def test_r_formula_keeps_the_backticks_r_needs_for_an_awkward_column_name():
    """A metadata column with a space in it is only reachable backquoted."""
    assert r_formula("~ `cell type` + condition", "design") == (
        '"~ `cell type` + condition"'
    )
    # Still a quoted string, so the contents of the backticks stay data.
    assert r_formula('~ `a"b`', "design") == '"~ `a\\"b`"'
