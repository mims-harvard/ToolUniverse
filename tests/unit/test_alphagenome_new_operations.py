"""Unit tests for the 7 AlphaGenomeTool operations added after live-API
verification against a real key: predict_variant, predict_sequence,
score_interval, score_ism_variants, output_metadata, atlas_scan_interval,
and atlas_list_scorers.

Several tests here are regressions for bugs a real API key actually
surfaced (not hypothetical): Atlas's obs["variant"] holds real Variant
objects (not strings), and ScorerMetadata.track_metadata is a
pandas.DataFrame, so ``x or []`` on it raises "truth value of a DataFrame
is ambiguous" instead of falling back to ``[]``.

Follows the sys.modules stubbing pattern used in test_alphagenome_atlas.py
and test_remote_ml_tools.py -- the real ``alphagenome`` package is not
installed in this environment (nor in CI).
"""

import sys
import types

import numpy as np
import pytest

from tooluniverse.alphagenome_tool import AlphaGenomeTool

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------- fakes
class _FakeVariant:
    def __init__(self, chromosome, position, reference_bases, alternate_bases):
        self.chromosome = chromosome
        self.position = position
        self.reference_bases = reference_bases
        self.alternate_bases = alternate_bases
        self.reference_interval = _FakeInterval(chromosome, position - 1, position)


class _FakeInterval:
    def __init__(self, chromosome, start, end):
        self.chromosome = chromosome
        self.start = start
        self.end = end

    def resize(self, length):
        return self


class _FakeColumnTable:
    """Minimal stand-in for the pandas.DataFrame the real AnnData/OutputMetadata use."""

    def __init__(self, n=None, **columns):
        self.columns = list(columns.keys())
        self._columns = columns
        self._n = n if n is not None else (len(next(iter(columns.values()))) if columns else 0)

    def __getitem__(self, key):
        return _FakeSeries(self._columns[key])

    def __len__(self):
        return self._n


class _FakeSeries(list):
    def dropna(self):
        return _FakeSeries(v for v in self if v is not None)

    def tolist(self):
        return list(self)


class _FakeAnnData:
    def __init__(self, x, track_names, gene_names, uns=None):
        self.X = np.array(x)
        self.var_names = [str(i) for i in range(len(track_names))]
        self.var = _FakeColumnTable(name=track_names)
        self.obs = _FakeColumnTable(gene_name=gene_names)
        self.uns = uns or {}


class _FakeAnnDataWithVariantObs:
    """Like _FakeAnnData but obs holds a "variant" column, matching
    Atlas's query_interval shape rather than query_variant's gene_name."""

    def __init__(self, x, track_names, variants):
        self.X = np.array(x)
        self.var_names = [str(i) for i in range(len(track_names))]
        self.var = _FakeColumnTable(name=track_names)
        self.obs = _FakeColumnTable(variant=variants)


class _FakeTrackData:
    def __init__(self, shape, n_tracks=None):
        self.values = np.zeros(shape)
        self.metadata = list(range(n_tracks if n_tracks is not None else shape[-1]))


class _FakeOutput:
    def __init__(self, rna_seq_shape=(10, 3)):
        self.rna_seq = _FakeTrackData(rna_seq_shape)


class _FakeVariantOutput:
    def __init__(self, reference, alternate):
        self.reference = reference
        self.alternate = alternate


class _FakeOutputMetadata:
    def __init__(self, rna_seq_table):
        self.rna_seq = rna_seq_table


class _AmbiguousTruthinessTable:
    """Regression fixture: a fake pandas.DataFrame whose __bool__ raises,
    exactly like the real thing -- catches a regression to `x or []`."""

    def __init__(self, length):
        self._length = length

    def __len__(self):
        return self._length

    def __bool__(self):
        raise ValueError(
            "The truth value of a DataFrame is ambiguous. Use a.empty, "
            "a.bool(), a.item(), a.any() or a.all()."
        )


class _NonStringVariantLabel:
    """A real Atlas obs["variant"] entry is a Variant object, not a string --
    its repr and str differ, so this checks the code calls str(), not repr()."""

    def __str__(self):
        return "chr22:100:A>T"

    def __repr__(self):
        return "Variant(chromosome='chr22', position=100, ...)"


class _FakeDnaClientModule:
    class Organism:
        HOMO_SAPIENS = "HOMO_SAPIENS"
        MUS_MUSCULUS = "MUS_MUSCULUS"

    class OutputType:
        RNA_SEQ = "RNA_SEQ"

    SEQUENCE_LENGTH_16KB = 16384
    SEQUENCE_LENGTH_100KB = 131072
    SEQUENCE_LENGTH_500KB = 524288
    SEQUENCE_LENGTH_1MB = 1048576

    def __init__(self, model):
        self._model = model

    def create(self, api_key):
        self._model.api_key = api_key
        return self._model


class _FakeModel:
    def __init__(self):
        self.api_key = None
        self.calls = []

    def predict_variant(self, **kwargs):
        self.calls.append(("predict_variant", kwargs))
        return _FakeVariantOutput(
            reference=_FakeOutput((10, 3)), alternate=_FakeOutput((10, 3))
        )

    def predict_sequence(self, **kwargs):
        self.calls.append(("predict_sequence", kwargs))
        return _FakeOutput((10, 3))

    def score_interval(self, **kwargs):
        self.calls.append(("score_interval", kwargs))
        return [
            _FakeAnnData(
                x=[[1.0, -2.0], [0.1, 0.2]],
                track_names=["track_a", "track_b"],
                gene_names=["GENE_A", "GENE_B"],
            )
        ]

    def score_ism_variants(self, **kwargs):
        self.calls.append(("score_ism_variants", kwargs))
        return [
            [
                _FakeAnnData(
                    x=[[0.5, -0.2]],
                    track_names=["track_a", "track_b"],
                    gene_names=["GENE_A"],
                    uns={"variant": _NonStringVariantLabel()},
                )
            ],
            [
                _FakeAnnData(
                    x=[[3.0, 0.1]],
                    track_names=["track_a", "track_b"],
                    gene_names=["GENE_A"],
                    uns={"variant": "chr22:101:A>C"},
                )
            ],
        ]

    def output_metadata(self, **kwargs):
        self.calls.append(("output_metadata", kwargs))
        return _FakeOutputMetadata(
            rna_seq_table=_FakeColumnTable(
                n=3, name=["a", "b", "c"], ontology_curie=["CL:1", "CL:2", None]
            )
        )


class _FakeAtlasClient:
    def __init__(self, query_result=None, scorer_metadata_result=None):
        self.query_result = query_result or {}
        self.scorer_metadata_result = scorer_metadata_result or {}
        self.calls = []

    def query_variant(self, variant, *, requested_scorers):
        return self.query_result

    def query_interval(self, interval, *, requested_scorers):
        self.calls.append(("query_interval", interval, list(requested_scorers)))
        return self.query_result

    def scorer_metadata(self):
        return self.scorer_metadata_result


class _FakeScorerMetadata:
    def __init__(self, is_signed, n_tracks):
        self.is_signed = is_signed
        self.track_metadata = _AmbiguousTruthinessTable(n_tracks)


# --------------------------------------------------------------- stub wiring
def _stub_modules(monkeypatch, model=None, atlas_client=None):
    alphagenome_pkg = types.ModuleType("alphagenome")

    data_pkg = types.ModuleType("alphagenome.data")
    genome_mod = types.ModuleType("alphagenome.data.genome")
    genome_mod.Variant = _FakeVariant
    genome_mod.Interval = _FakeInterval
    data_pkg.genome = genome_mod

    models_pkg = types.ModuleType("alphagenome.models")
    dna_client_mod = _FakeDnaClientModule(model or _FakeModel())
    variant_scorers_mod = types.ModuleType("alphagenome.models.variant_scorers")
    variant_scorers_mod.RECOMMENDED_VARIANT_SCORERS = {"RNA_SEQ": object()}
    models_pkg.dna_client = dna_client_mod
    models_pkg.variant_scorers = variant_scorers_mod

    atlas_pkg = types.ModuleType("alphagenome.atlas")
    atlas_mod = types.ModuleType("alphagenome.atlas.atlas")
    client = atlas_client or _FakeAtlasClient()
    atlas_mod.create = lambda api_key: client
    atlas_pkg.atlas = atlas_mod

    for name, mod in {
        "alphagenome": alphagenome_pkg,
        "alphagenome.data": data_pkg,
        "alphagenome.data.genome": genome_mod,
        "alphagenome.models": models_pkg,
        "alphagenome.models.dna_client": dna_client_mod,
        "alphagenome.models.variant_scorers": variant_scorers_mod,
        "alphagenome.atlas": atlas_pkg,
        "alphagenome.atlas.atlas": atlas_mod,
    }.items():
        monkeypatch.setitem(sys.modules, name, mod)

    monkeypatch.setenv("ALPHA_GENOME_API_KEY", "test-key")
    return dna_client_mod._model, client


def _tool(operation):
    return AlphaGenomeTool({"fields": {"operation": operation}})


# ------------------------------------------------------------------- tests
def test_predict_variant_success(monkeypatch):
    _stub_modules(monkeypatch)
    result = _tool("predict_variant").run(
        {
            "chromosome": "chr22",
            "position": 36201698,
            "reference_bases": "A",
            "alternate_bases": "C",
        }
    )
    assert result["status"] == "success"
    assert result["data"]["variant"] == "chr22:36201698A>C"
    assert result["data"]["reference"][0]["modality"] == "rna_seq"
    assert result["data"]["reference"][0]["shape"] == [10, 3]
    assert result["data"]["alternate"][0]["shape"] == [10, 3]


def test_predict_variant_missing_params(monkeypatch):
    _stub_modules(monkeypatch)
    result = _tool("predict_variant").run({"chromosome": "chr22"})
    assert result["status"] == "error"
    assert "Missing required parameter" in result["error"]


def test_predict_sequence_success(monkeypatch):
    _stub_modules(monkeypatch)
    result = _tool("predict_sequence").run({"sequence": "ACGT" * 4})
    assert result["status"] == "success"
    assert result["data"]["sequence_length"] == 16
    assert result["data"]["tracks"][0]["modality"] == "rna_seq"


def test_predict_sequence_missing_sequence(monkeypatch):
    _stub_modules(monkeypatch)
    result = _tool("predict_sequence").run({})
    assert result["status"] == "error"
    assert "sequence" in result["error"]


def test_score_interval_success(monkeypatch):
    _stub_modules(monkeypatch)
    result = _tool("score_interval").run(
        {"chromosome": "chr22", "start": 100, "end": 200, "top_n": 5}
    )
    assert result["status"] == "success"
    scores = result["data"]["scores"]
    assert scores[0] == {"track": "track_b", "score": -2.0, "gene": "GENE_A"}


def test_score_interval_missing_params(monkeypatch):
    _stub_modules(monkeypatch)
    result = _tool("score_interval").run({"chromosome": "chr22"})
    assert result["status"] == "error"
    assert "Missing required parameter" in result["error"]


def test_score_ism_variants_width_guard_blocks_before_any_call(monkeypatch):
    model, _ = _stub_modules(monkeypatch)
    result = _tool("score_ism_variants").run(
        {"chromosome": "chr22", "start": 0, "end": 1000}
    )
    assert result["status"] == "error"
    assert "too wide" in result["error"]
    assert model.calls == []  # never reached the live model


def test_score_ism_variants_ranks_by_peak_effect_and_stringifies_variant(monkeypatch):
    # Regression: uns["variant"] can be a non-string object (a real Variant,
    # verified live); the tool must str() it, and the -0.2/3.0 max-abs pick
    # per candidate must be correct (not the first value in the row).
    _stub_modules(monkeypatch)
    result = _tool("score_ism_variants").run(
        {"chromosome": "chr22", "start": 0, "end": 20, "top_n": 5}
    )
    assert result["status"] == "success"
    top = result["data"]["top_variants"]
    assert top[0]["variant"] == "chr22:101:A>C"
    assert top[0]["score"] == pytest.approx(3.0)
    assert top[1]["variant"] == "chr22:100:A>T"  # str(), not the repr()
    assert top[1]["score"] == pytest.approx(0.5)  # |0.5| > |-0.2| in that row


def test_output_metadata_success(monkeypatch):
    _stub_modules(monkeypatch)
    result = _tool("output_metadata").run({})
    assert result["status"] == "success"
    modalities = {m["modality"]: m for m in result["data"]["modalities"]}
    assert modalities["rna_seq"]["n_tracks"] == 3
    assert modalities["rna_seq"]["sample_ontology_terms"] == ["CL:1", "CL:2"]


def test_atlas_scan_interval_width_guard_blocks_before_any_call(monkeypatch):
    _, client = _stub_modules(monkeypatch)
    result = _tool("atlas_scan_interval").run(
        {"chromosome": "chr22", "start": 0, "end": 20_000}
    )
    assert result["status"] == "error"
    assert "too wide" in result["error"]
    assert client.calls == []


def test_atlas_scan_interval_stringifies_non_string_variant_labels(monkeypatch):
    # Regression: real Atlas obs["variant"] holds Variant objects, not
    # strings -- found live, would otherwise leak non-JSON-serializable
    # objects into the response.
    adata = _FakeAnnDataWithVariantObs(
        x=[[1.5]], track_names=["AVI_SCORE"], variants=[_NonStringVariantLabel()]
    )
    _, client = _stub_modules(
        monkeypatch, atlas_client=_FakeAtlasClient(query_result={"AVI_SCORE": adata})
    )
    result = _tool("atlas_scan_interval").run(
        {"chromosome": "chr22", "start": 0, "end": 100}
    )
    assert result["status"] == "success"
    row = result["data"]["scores"]["AVI_SCORE"][0]
    assert row["variant"] == "chr22:100:A>T"
    assert isinstance(row["variant"], str)


def test_atlas_list_scorers_success_and_survives_dataframe_track_metadata(monkeypatch):
    # Regression: track_metadata is a real pandas.DataFrame; `x or []` on it
    # raises "truth value of a DataFrame is ambiguous" instead of skipping to
    # []. _AmbiguousTruthinessTable's __bool__ raises exactly that, so this
    # test fails loudly if the `or []` pattern is reintroduced.
    scorer_metadata_result = {
        "AVI_SCORE": _FakeScorerMetadata(is_signed=False, n_tracks=1),
        "RNA_SEQ": _FakeScorerMetadata(is_signed=True, n_tracks=371),
    }
    _, client = _stub_modules(
        monkeypatch,
        atlas_client=_FakeAtlasClient(scorer_metadata_result=scorer_metadata_result),
    )
    result = _tool("atlas_list_scorers").run({})
    assert result["status"] == "success"
    scorers = {s["name"]: s for s in result["data"]["scorers"]}
    assert scorers["AVI_SCORE"] == {"name": "AVI_SCORE", "is_signed": False, "n_tracks": 1}
    assert scorers["RNA_SEQ"]["n_tracks"] == 371
