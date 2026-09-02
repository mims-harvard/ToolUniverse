"""Regression: batch long_branch_score must actually produce values.

`phykit lb_score <tree>` prints a labelled summary block
("mean: -25.0\\nmedian: -30.4551\\n...") unless -v/--verbose is passed, while the
batch aggregator parses `line.split("\\t")[-1]` expecting `taxon<TAB>score`.
Without -v every line failed to parse, `taxon_values` stayed empty, and each
tree was silently skipped -- the batch returned
"No values computed from 249 files (0 errors)", which reads like an empty
directory rather than a parse failure. That made the whole function unusable
while looking like a user error.
"""

import shutil

import pytest

from tooluniverse.phykit_tool import _run_phykit

pytestmark = pytest.mark.skipif(
    shutil.which("phykit") is None, reason="phykit not installed"
)

# 4 taxa, deliberately unbalanced so mean != median and a silent fallback to
# the wrong statistic cannot pass.
NEWICK = "(((A:0.01,B:0.01):0.02,C:0.05):0.03,D:0.9);"


@pytest.fixture()
def tree(tmp_path):
    p = tmp_path / "t.treefile"
    p.write_text(NEWICK + "\n")
    return str(p)


def test_batch_invocation_yields_parseable_per_taxon_rows(tree):
    """The batch path's -v output must parse the way the aggregator expects."""
    out, reason = _run_phykit("long_branch_score", tree, ["-v"])
    assert out, f"phykit failed: {reason}"

    values = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        values.append(float(parts[-1]))

    # One row per taxon -- this is what was empty before the fix.
    assert len(values) == 4, f"expected 4 per-taxon rows, got {len(values)}: {out!r}"


def test_summary_block_is_not_parseable_as_rows(tree):
    """Without -v the output is a summary block, so the aggregator gets nothing.

    Pins the root cause: if phykit ever changes to emit rows by default this
    test fails loudly rather than the fix quietly becoming a no-op.
    """
    out, reason = _run_phykit("long_branch_score", tree, None)
    assert out, f"phykit failed: {reason}"
    assert "median:" in out

    parsed = []
    for line in out.splitlines():
        if not line.strip():
            continue
        try:
            parsed.append(float(line.split("\t")[-1]))
        except ValueError:
            pass
    assert parsed == [], f"summary block unexpectedly parsed as rows: {parsed}"
