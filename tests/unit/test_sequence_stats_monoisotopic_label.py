"""Regression guard for Fix-R26E-4: Sequence_stats's molecular-weight field
was named "estimated_mw_da" with no indication it's monoisotopic mass, not
the conventional average mass ExPASy ProtParam/UniProt report by default.
Confirmed live: for ACDEFGHIK it returned 1018.45 (monoisotopic), matching
PepCalc's `molecularWeight` monoisotopic field exactly, while
ProtParam_calculate's average mass for the same sequence is 1019.14 --
a silent, unlabeled mismatch. Renamed to "estimated_mw_monoisotopic_da"
so the value is self-documenting; the underlying computation is unchanged.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.sequence_analyze_tool import SequenceAnalyzeTool

pytestmark = pytest.mark.unit


def _tool():
    return SequenceAnalyzeTool({"name": "sequence_stats_test", "fields": {}})


class TestMonoisotopicLabel:
    def test_field_is_labeled_monoisotopic(self):
        tool = _tool()
        result = tool.run({"operation": "stats", "sequence": "ACDEFGHIK"})

        assert result["status"] == "success"
        assert "estimated_mw_monoisotopic_da" in result["data"]
        assert "estimated_mw_da" not in result["data"]
        assert result["data"]["estimated_mw_monoisotopic_da"] == pytest.approx(
            1018.45, abs=0.01
        )
