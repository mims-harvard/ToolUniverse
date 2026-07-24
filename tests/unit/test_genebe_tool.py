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

# Real shape confirmed live: hgvs_c/hgvs_p/effects live nested under
# acmg_by_gene[0], not at the variant's own top level.
_CFTR_G551D = {
    "gene_symbol": "CFTR",
    "transcript": "NM_000492.4",
    "acmg_classification": "Pathogenic",
    "acmg_score": 21,
    "dbsnp": "rs75527207",
    "alphamissense_score": 0.9897,
    "acmg_by_gene": [
        {
            "gene_symbol": "CFTR",
            "transcript": "NM_000492.4",
            "hgvs_c": "c.1652G>A",
            "hgvs_p": "p.Gly551Asp",
            "effects": ["missense_variant"],
        }
    ],
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

    def test_hgvs_and_effects_pulled_from_nested_acmg_by_gene(self):
        """Fix-R22D-2: hgvs_c/hgvs_p/effects were silently dropped because
        the tool looked for them at the variant's own top level, but
        GeneBe's real API only puts them under acmg_by_gene[0] -- confirmed
        live for CFTR G551D (rs75527207)."""
        tool = _make_tool()
        with patch("tooluniverse.genebe_tool.requests.get") as get:
            get.return_value = _resp(200, [_CFTR_G551D])
            result = tool.run(
                {"chr": "7", "pos": 117587806, "ref": "G", "alt": "A", "genome": "hg38"}
            )

        d = result["data"]
        self.assertEqual(d["hgvs_c"], "c.1652G>A")
        self.assertEqual(d["hgvs_p"], "p.Gly551Asp")
        self.assertEqual(d["effects"], ["missense_variant"])
        # top-level fields still extracted as before
        self.assertEqual(d["gene_symbol"], "CFTR")
        self.assertEqual(d["transcript"], "NM_000492.4")

    def test_missing_acmg_by_gene_does_not_crash(self):
        """A variant response without an acmg_by_gene block (e.g. no gene
        overlap) must not raise -- hgvs_c/hgvs_p/effects are simply absent."""
        tool = _make_tool()
        with patch("tooluniverse.genebe_tool.requests.get") as get:
            get.return_value = _resp(200, [_BRAF])  # no acmg_by_gene key
            result = tool.run({"chr": "7", "pos": 140753336, "ref": "A", "alt": "T"})

        self.assertEqual(result["status"], "success")
        self.assertNotIn("hgvs_c", result["data"])
        self.assertNotIn("hgvs_p", result["data"])
        self.assertNotIn("effects", result["data"])


if __name__ == "__main__":
    unittest.main()
