"""GeneBe ACMG-classification tool.

Covers param validation, build-alias normalization, chr-prefix stripping,
field trimming, and error paths with mocks (no live GeneBe calls).
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _make_tool():
    from tooluniverse.genebe_tool import GeneBeTool

    return GeneBeTool({"name": "GeneBe_classify_variant", "type": "GeneBeTool", "fields": {}})


def _resp(status_code, variants=None):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = {"variants": variants if variants is not None else []}
    r.text = ""
    return r


_BRAF = {
    "gene_symbol": "BRAF",
    "acmg_classification": "Pathogenic",
    "acmg_score": 14,
    "acmg_criteria": "PS3,PM1,PM2,PM5",
    "dbsnp": "rs113488022",
    "alphamissense_score": 0.9927,
    "curate_time": "internal",  # not in _USEFUL_FIELDS -> trimmed away
}


class TestGeneBe(unittest.TestCase):
    def test_missing_params_rejected(self):
        result = _make_tool().run({"chr": "7", "pos": 140753336})
        self.assertEqual(result["status"], "error")
        self.assertIn("ref", result["error"])

    def test_classification_and_trimming(self):
        tool = _make_tool()
        with patch("tooluniverse.genebe_tool.requests.get") as get:
            get.return_value = _resp(200, [_BRAF])
            result = tool.run({"chr": "7", "pos": 140753336, "ref": "A", "alt": "T"})

        d = result["data"]
        self.assertEqual(d["acmg_classification"], "Pathogenic")
        self.assertEqual(d["variant"], "7-140753336-A-T")
        self.assertNotIn("curate_time", d)  # trimmed
        self.assertEqual(get.call_args.kwargs["params"]["genome"], "hg38")  # default

    def test_build_alias_and_chr_prefix_normalized(self):
        tool = _make_tool()
        with patch("tooluniverse.genebe_tool.requests.get") as get:
            get.return_value = _resp(200, [_BRAF])
            tool.run({"chr": "chr17", "pos": 43093464, "ref": "A", "alt": "G", "genome": "GRCh38"})
        p = get.call_args.kwargs["params"]
        self.assertEqual(p["genome"], "hg38")  # GRCh38 -> hg38
        self.assertEqual(p["chr"], "17")  # chr prefix stripped

    def test_unsupported_build_rejected(self):
        result = _make_tool().run({"chr": "7", "pos": 1, "ref": "A", "alt": "T", "genome": "t2t"})
        self.assertEqual(result["status"], "error")
        self.assertIn("genome build", result["error"])

    def test_empty_variants_is_error(self):
        tool = _make_tool()
        with patch("tooluniverse.genebe_tool.requests.get") as get:
            get.return_value = _resp(200, [])
            result = tool.run({"chr": "7", "pos": 1, "ref": "A", "alt": "T"})
        self.assertEqual(result["status"], "error")
        self.assertIn("no result", result["error"])

    def test_rate_limit_message(self):
        tool = _make_tool()
        with patch("tooluniverse.genebe_tool.requests.get") as get:
            get.return_value = _resp(429)
            result = tool.run({"chr": "7", "pos": 1, "ref": "A", "alt": "T"})
        self.assertEqual(result["status"], "error")
        self.assertIn("rate limit", result["error"].lower())


if __name__ == "__main__":
    unittest.main()
