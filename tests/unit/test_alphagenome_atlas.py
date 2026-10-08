"""Unit tests for AlphaGenomeTool's ``atlas_lookup_variant`` operation.

AlphaGenome Atlas (released Sep 2026) is a precomputed database, queried via
a distinct SDK module (``alphagenome.atlas.atlas``) from the live
``score_variant``/``predict_interval`` operations, so it gets its own
lazy-import and client-construction path in ``alphagenome_tool.py``.

The ``alphagenome`` package is not installed in this environment (nor in CI),
so these tests stub the minimal pieces of it in ``sys.modules`` -- following
the same pattern used in ``test_remote_ml_tools.py`` for un-installable
model packages -- and never exercise the real network call.
"""

import sys
import types

import numpy as np
import pytest

from tooluniverse.alphagenome_tool import AlphaGenomeTool

pytestmark = pytest.mark.unit


class _FakeVariant:
    def __init__(self, chromosome, position, reference_bases, alternate_bases):
        self.chromosome = chromosome
        self.position = position
        self.reference_bases = reference_bases
        self.alternate_bases = alternate_bases


class _FakeAnnData:
    def __init__(self, values, var_names):
        self.X = values
        self.var_names = var_names


class _FakeColumnTable:
    """Minimal stand-in for the pandas.DataFrame the real AnnData uses."""

    def __init__(self, **columns):
        self.columns = list(columns.keys())
        self._columns = columns

    def __getitem__(self, key):
        return self._columns[key]


class _FakeMultiGeneAnnData:
    """Mirrors the real AlphaGenome AnnData shape verified against the live
    API: X is (n_genes, n_tracks), var_names is a meaningless numeric index,
    the real track label is in var["name"], and the gene is in
    obs["gene_name"] -- not derivable from var_names/X alone."""

    def __init__(self, x, track_names, gene_names):
        self.X = np.array(x)
        self.var_names = [str(i) for i in range(len(track_names))]
        self.var = _FakeColumnTable(name=track_names)
        self.obs = _FakeColumnTable(gene_name=gene_names)


class _FakeAtlasClient:
    def __init__(self, query_result=None, api_key=None):
        self.query_result = query_result or {}
        self.api_key = api_key
        self.calls = []

    def query_variant(self, variant, *, requested_scorers):
        self.calls.append((variant, list(requested_scorers)))
        return self.query_result


def _stub_alphagenome_modules(monkeypatch, atlas_client):
    """Install a minimal fake ``alphagenome`` package tree into sys.modules."""
    alphagenome_pkg = types.ModuleType("alphagenome")
    data_pkg = types.ModuleType("alphagenome.data")
    genome_mod = types.ModuleType("alphagenome.data.genome")
    genome_mod.Variant = _FakeVariant
    data_pkg.genome = genome_mod

    atlas_pkg = types.ModuleType("alphagenome.atlas")
    atlas_mod = types.ModuleType("alphagenome.atlas.atlas")
    atlas_mod.create = lambda api_key: (
        atlas_client.__setattr__("api_key", api_key) or atlas_client
    )
    atlas_pkg.atlas = atlas_mod

    for name, mod in {
        "alphagenome": alphagenome_pkg,
        "alphagenome.data": data_pkg,
        "alphagenome.data.genome": genome_mod,
        "alphagenome.atlas": atlas_pkg,
        "alphagenome.atlas.atlas": atlas_mod,
    }.items():
        monkeypatch.setitem(sys.modules, name, mod)


def _tool():
    return AlphaGenomeTool({"fields": {"operation": "atlas_lookup_variant"}})


VARIANT_ARGS = {
    "chromosome": "chr22",
    "position": 36201698,
    "reference_bases": "A",
    "alternate_bases": "C",
}


def test_missing_package_returns_clean_error(monkeypatch):
    # Real environment: 'alphagenome' genuinely isn't installed, so this
    # exercises the actual ImportError path with no stubbing at all.
    monkeypatch.delitem(sys.modules, "alphagenome", raising=False)
    result = _tool().run(dict(VARIANT_ARGS))
    assert result["status"] == "error"
    assert "pip install alphagenome" in result["error"]


def test_missing_api_key_returns_clean_error(monkeypatch):
    _stub_alphagenome_modules(monkeypatch, _FakeAtlasClient())
    monkeypatch.delenv("ALPHA_GENOME_API_KEY", raising=False)
    result = _tool().run(dict(VARIANT_ARGS))
    assert result["status"] == "error"
    assert "ALPHA_GENOME_API_KEY" in result["error"]


def test_missing_required_parameters(monkeypatch):
    _stub_alphagenome_modules(monkeypatch, _FakeAtlasClient())
    monkeypatch.setenv("ALPHA_GENOME_API_KEY", "test-key")
    result = _tool().run({"chromosome": "chr22"})
    assert result["status"] == "error"
    assert "Missing required parameter" in result["error"]


def test_successful_lookup_defaults_to_avi_scorer_and_sorts_top_n(monkeypatch):
    # Field names/shape verified against the real Atlas API: scorer_metadata()
    # lists "AVI_SCORE" (not "AVI"), and query_variant's AnnData carries the
    # human-readable track label in var["name"], not in var_names.
    adata = _FakeAnnData(
        values=[0.9, -0.95, 0.1], var_names=["track_a", "track_b", "track_c"]
    )
    client = _FakeAtlasClient(query_result={"AVI_SCORE": adata})
    _stub_alphagenome_modules(monkeypatch, client)
    monkeypatch.setenv("ALPHA_GENOME_API_KEY", "test-key")

    result = _tool().run({**VARIANT_ARGS, "top_n": 2})

    assert result["status"] == "success"
    assert result["data"]["variant"] == "chr22:36201698A>C"
    assert result["data"]["scorers"] == ["AVI_SCORE"]
    top = result["data"]["scores"]["AVI_SCORE"]
    assert [row["track"] for row in top] == ["track_b", "track_a"]
    assert top[0]["score"] == pytest.approx(-0.95)

    # requested_scorers defaulted to ["AVI_SCORE"] and the variant was built correctly
    (called_variant, called_scorers) = client.calls[0]
    assert called_scorers == ["AVI_SCORE"]
    assert called_variant.chromosome == "chr22"
    assert called_variant.position == 36201698


def test_explicit_scorers_are_passed_through(monkeypatch):
    adata = _FakeAnnData(values=[0.2], var_names=["track_a"])
    client = _FakeAtlasClient(query_result={"RNA_SEQ": adata})
    _stub_alphagenome_modules(monkeypatch, client)
    monkeypatch.setenv("ALPHA_GENOME_API_KEY", "test-key")

    result = _tool().run({**VARIANT_ARGS, "scorers": ["RNA_SEQ"]})

    assert result["status"] == "success"
    assert result["data"]["scorers"] == ["RNA_SEQ"]
    assert "RNA_SEQ" in result["data"]["scores"]
    assert client.calls[0][1] == ["RNA_SEQ"]


def test_lowercase_scorer_names_are_normalized_to_match_response_keys(monkeypatch):
    """Regression: found live -- the real Atlas API normalizes scorer names
    to uppercase in its response regardless of request casing, but the tool
    used to echo back `scorers` verbatim (e.g. "avi_score"). A caller doing
    `scores[s] for s in scorers` would then KeyError, since the actual dict
    key came back as "AVI_SCORE". Requested names must be uppercased before
    the call so the echoed `scorers` list matches the `scores` dict keys."""
    adata = _FakeAnnData(values=[1.5], var_names=["AVI_SCORE"])
    client = _FakeAtlasClient(query_result={"AVI_SCORE": adata})
    _stub_alphagenome_modules(monkeypatch, client)
    monkeypatch.setenv("ALPHA_GENOME_API_KEY", "test-key")

    result = _tool().run({**VARIANT_ARGS, "scorers": ["avi_score"]})

    assert result["status"] == "success"
    assert result["data"]["scorers"] == ["AVI_SCORE"]
    assert result["data"]["scorers"] == list(result["data"]["scores"].keys())
    assert client.calls[0][1] == ["AVI_SCORE"]  # request itself was normalized too


def test_multi_gene_matrix_uses_real_track_and_gene_names(monkeypatch):
    """Regression test for a real bug found via live-API testing: a naive
    ravel()+zip(var_names) flattening of a (n_genes, n_tracks) AnnData
    silently dropped every gene past the first and mislabeled scores with
    meaningless numeric var_names ("0", "1", ...) instead of the real track
    name (in var["name"]) and gene (in obs["gene_name"])."""
    adata = _FakeMultiGeneAnnData(
        x=[
            [0.1, 0.2, 0.3],  # gene A
            [5.0, -9.0, 0.4],  # gene B -- must not be dropped
        ],
        track_names=["ATAC:liver", "ATAC:lung", "ATAC:heart"],
        gene_names=["GENE_A", "GENE_B"],
    )
    client = _FakeAtlasClient(query_result={"ATAC": adata})
    _stub_alphagenome_modules(monkeypatch, client)
    monkeypatch.setenv("ALPHA_GENOME_API_KEY", "test-key")

    result = _tool().run({**VARIANT_ARGS, "scorers": ["ATAC"], "top_n": 2})

    top = result["data"]["scores"]["ATAC"]
    assert len(top) == 2
    assert top[0] == {"track": "ATAC:lung", "score": -9.0, "gene": "GENE_B"}
    assert top[1] == {"track": "ATAC:liver", "score": 5.0, "gene": "GENE_B"}


@pytest.mark.parametrize("bad_top_n", [-3, 0, "not-a-number"])
def test_non_positive_or_invalid_top_n_falls_back_to_default(monkeypatch, bad_top_n):
    """Regression: found live -- top_n=-3 against a real ~13,700-row result
    returned 13,724 rows via plain `list[:top_n]` (Python's negative-index
    slicing means "all but the last N", not "top N"), instead of a small
    top-N summary or a clamp/error."""
    adata = _FakeMultiGeneAnnData(
        x=[[0.1, 0.2, 0.3], [5.0, -9.0, 0.4], [1.0, 1.0, 1.0]],
        track_names=["a", "b", "c"],
        gene_names=["GENE_A", "GENE_B", "GENE_C"],
    )
    client = _FakeAtlasClient(query_result={"ATAC": adata})
    _stub_alphagenome_modules(monkeypatch, client)
    monkeypatch.setenv("ALPHA_GENOME_API_KEY", "test-key")

    result = _tool().run({**VARIANT_ARGS, "scorers": ["ATAC"], "top_n": bad_top_n})

    assert result["status"] == "success"
    assert len(result["data"]["scores"]["ATAC"]) == 9  # falls back to default (20), capped by data size
