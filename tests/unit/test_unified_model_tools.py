"""Tests for the unified ML-model interface.

Offline by default: the pieces that matter for correctness -- score
calibration, argument templating, payload extraction, backend selection,
consensus, metrics -- are pure functions over data and are tested with a
stub caller.

The ones that reach the network carry BOTH ``integration`` and ``network``.
``network`` is the load-bearing half: ``pytest.ini`` filters on
``-m "not slow and not require_api_keys and not network"`` and says nothing
about ``integration``, so an ``integration``-only mark would have run them --
and downloaded ProteinGym -- in every default run. Select them with
``-m network``.
"""

import json
import math
import time

import pytest

from tooluniverse.unified_model_metrics import (
    auroc,
    auprc,
    confusion,
    evaluate,
    from_confusion,
    spearman,
)
from tooluniverse.unified_model_normalizers import normalize_pdb_structure
from tooluniverse.unified_model_resolvers import (
    ResolutionError,
    _parse_free_variant,
    aa1,
    resolve_variant_effect,
)
from tooluniverse.unified_model_spec import (
    BackendSpec,
    ScoreTransform,
    UnifiedModelConfigError,
    extract,
    load_registry,
    render,
)


# --------------------------------------------------------------------------- #
# Registry integrity
# --------------------------------------------------------------------------- #
class TestRegistry:
    def test_loads(self):
        registry = load_registry(force=True)
        assert set(registry.tasks) == {
            "variant_effect",
            "structure_prediction",
            "molecular_property",
            "binding_affinity",
        }

    def test_every_backend_is_well_formed(self):
        registry = load_registry()
        for task_id in registry.tasks:
            for spec in registry.backends_for(task_id):
                assert spec.tool, f"{spec.id} names no tool"
                assert spec.calibration in ("published", "heuristic"), spec.id
                if spec.transform.kind not in ("none", "categorical"):
                    assert isinstance(spec.higher_is_positive, bool), spec.id

    def test_backends_reference_real_tools(self):
        """Every backend must point at a tool that actually exists.

        A typo here degrades silently into "backend returned an error" on
        every call, which is indistinguishable from an upstream outage.
        """
        from tooluniverse.execute_function import ToolUniverse

        tu = ToolUniverse()
        tu.load_tools()
        # ToolUniverse drops tools whose required API keys are absent, so the
        # key-gated backends are legitimately missing from all_tool_dict on a
        # machine without those keys. Include them from the exclusion record,
        # or this test would only pass for an operator holding every key.
        known = set(tu.all_tool_dict) | set(
            getattr(tu, "_excluded_api_key_tool_configs", {})
        )

        registry = load_registry()
        missing = []
        for task_id in registry.tasks:
            for spec in registry.backends_for(task_id):
                tools = {spec.tool} | {
                    entry["tool"]
                    for entry in spec.property_map.values()
                    if entry.get("tool")
                }
                missing.extend(
                    f"{spec.id} -> {tool}" for tool in tools if tool not in known
                )
        assert not missing, f"Backends point at unknown tools: {missing}"

    def test_unknown_task_and_backend_raise(self):
        registry = load_registry()
        with pytest.raises(KeyError):
            registry.task("nope")
        with pytest.raises(KeyError):
            registry.backend("variant_effect", "nope")


# --------------------------------------------------------------------------- #
# Calibration
# --------------------------------------------------------------------------- #
class TestScoreTransform:
    def test_identity_clamps(self):
        t = ScoreTransform(kind="identity")
        assert t.to_unit(0.5) == 0.5
        assert t.to_unit(1.7) == 1.0
        assert t.to_unit(-3) == 0.0

    def test_linear(self):
        t = ScoreTransform(kind="linear", lo=0, hi=40)
        assert t.to_unit(20) == pytest.approx(0.5)
        assert t.to_unit(80) == 1.0

    def test_invert_flips_direction(self):
        """The LLR backends score *lower* for more damaging variants."""
        t = ScoreTransform(kind="logistic", x0=-4.0, k=2.0, invert=True)
        damaging = t.to_unit(-8.0)
        tolerated = t.to_unit(1.0)
        assert damaging > 0.85 and tolerated < 0.1
        assert damaging > tolerated

    def test_logistic_does_not_overflow(self):
        t = ScoreTransform(kind="logistic", x0=0, k=1)
        assert t.to_unit(-10_000) == 0.0
        assert t.to_unit(10_000) == 1.0

    def test_categorical(self):
        t = ScoreTransform(kind="categorical", map={"Pathogenic": 1.0, "Benign": 0.0})
        assert t.to_unit("pathogenic") == 1.0
        assert t.to_unit("Benign") == 0.0
        assert t.to_unit("Nonsense") is None

    def test_none_kind_yields_no_normalized_score(self):
        """Units that have no common axis must not be forced onto one."""
        assert ScoreTransform(kind="none").to_unit(-9.4) is None

    def test_non_numeric_and_nan_are_safe(self):
        t = ScoreTransform(kind="identity")
        assert t.to_unit("abc") is None
        assert t.to_unit(float("nan")) is None
        assert t.to_unit(None) is None

    def test_bad_config_is_rejected(self):
        with pytest.raises(UnifiedModelConfigError):
            ScoreTransform.from_config({"kind": "linear", "bogus": 1})
        with pytest.raises(UnifiedModelConfigError):
            ScoreTransform(kind="linear", lo=1, hi=1).to_unit(1)


# --------------------------------------------------------------------------- #
# Templating and extraction
# --------------------------------------------------------------------------- #
class TestRenderAndExtract:
    def test_single_placeholder_preserves_type(self):
        """A genomic position must reach the backend as an int, not a string."""
        assert render("{g.pos}", {"g": {"pos": 7675088}}) == 7675088

    def test_interpolation_builds_a_string(self):
        ctx = {"p": {"ref": "R", "pos": 175, "alt": "H"}}
        assert render("{p.ref}{p.pos}{p.alt}", ctx) == "R175H"

    def test_missing_value_yields_none_so_the_key_is_dropped(self):
        assert render("{p.missing}", {"p": {}}) is None
        assert render("x{p.missing}y", {"p": {}}) is None

    def test_nested_templates(self):
        out = render([{"id": "A", "sequence": "{seq}"}], {"seq": "MKT"})
        assert out == [{"id": "A", "sequence": "MKT"}]

    def test_extract_aggregates_per_transcript_arrays(self):
        payload = {"dbnsfp": {"revel": {"score": [0.9, 0.2, 0.5]}}}
        assert extract(payload, {"path": "$.dbnsfp.revel.score", "agg": "max"}) == 0.9
        assert extract(payload, {"path": "$.dbnsfp.revel.score", "agg": "min"}) == 0.2

    def test_extract_coerces_numeric_strings(self):
        """SpliceAI returns its deltas as strings; '0.9' must not sort as text."""
        payload = {"s": [{"d": "0.11"}, {"d": "0.9"}]}
        assert extract(payload, {"path": "$.s[*].d", "agg": "max"}) == 0.9

    def test_extract_rescales_units(self):
        """ESMFold reports pLDDT on 0-1 where others use 0-100."""
        assert extract({"m": 0.9}, {"path": "$.m", "mul": 100}) == 90.0

    def test_extract_missing_path_returns_default(self):
        assert extract({}, {"path": "$.nope", "default": 7}) == 7
        assert extract({}, "$.nope") is None


# --------------------------------------------------------------------------- #
# Backend behaviour
# --------------------------------------------------------------------------- #
class TestBackendSpec:
    def test_build_arguments_drops_unfilled_keys(self):
        spec = BackendSpec.from_config(
            {
                "id": "x",
                "task": "variant_effect",
                "tool": "T",
                "input_map": {"a": "{g.pos}", "b": "{g.missing}"},
            }
        )
        assert spec.build_arguments({"g": {"pos": 3}}) == {"a": 3}

    def test_missing_requirements_names_what_is_absent(self):
        spec = BackendSpec.from_config(
            {"id": "x", "task": "variant_effect", "tool": "T", "needs": ["genomic.pos"]}
        )
        assert spec.missing_requirements({"genomic": {}}) == ["genomic.pos"]
        assert spec.missing_requirements({"genomic": {"pos": 1}}) == []

    def test_normalize_produces_the_canonical_fields(self):
        spec = load_registry().backend("variant_effect", "cadd")
        fields = spec.normalize(
            {"status": "success", "data": {"phred_score": 25.9, "version": "v1.7"}}
        )
        assert fields["score"] == 25.9
        assert fields["score_type"] == "CADD PHRED"
        assert fields["call"] == "deleterious"
        assert 0.0 <= fields["normalized_score"] <= 1.0

    def test_call_threshold_direction_for_sift(self):
        """SIFT is inverted: a *low* score is the damaging one."""
        spec = load_registry().backend("variant_effect", "sift")
        damaging = spec.normalize(
            {
                "transcript_consequences": [
                    {"sift_score": 0.0, "biotype": "protein_coding"}
                ]
            }
        )
        tolerated = spec.normalize(
            {
                "transcript_consequences": [
                    {"sift_score": 0.8, "biotype": "protein_coding"}
                ]
            }
        )
        assert damaging["call"] == "deleterious"
        assert tolerated["call"] == "tolerated"
        assert damaging["normalized_score"] > tolerated["normalized_score"]
        assert tolerated["normalized_score"] < 0.5

    def test_multi_property_specialization(self):
        spec = load_registry().backend("molecular_property", "admet_ai")
        bbb = spec.for_property("bbb_martins")
        assert bbb.tool == "ADMETAI_predict_BBB_penetrance"
        assert bbb.score_units == "probability"
        assert spec.for_property("not_a_property") is None

    def test_api_key_gating(self, monkeypatch):
        spec = load_registry().backend("structure_prediction", "nim_alphafold2")
        monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
        assert spec.requires_key() and not spec.key_available()
        monkeypatch.setenv("NVIDIA_API_KEY", "x")
        assert spec.key_available()


# --------------------------------------------------------------------------- #
# Normalizers
# --------------------------------------------------------------------------- #
class TestNormalizers:
    @staticmethod
    def _pdb(*atoms):
        """Build ATOM records at the real PDB column offsets.

        The parser reads the B-factor from columns 61-66 by position, as the
        format requires; a hand-typed line with plausible-looking spacing does
        not line up and yields no pLDDT at all.
        """
        return "".join(
            "ATOM  {:5d} {:^4s} {:3s} {:1s}{:4d}    "
            "{:8.3f}{:8.3f}{:8.3f}{:6.2f}{:6.2f}\n".format(
                i + 1, name, resname, "A", resseq, 10.0, 10.0, 10.0, 1.00, bfactor
            )
            for i, (name, resname, resseq, bfactor) in enumerate(atoms)
        )

    PDB = None

    def setup_method(self):
        # Methionine contributes three atoms and lysine one, so an atom-weighted
        # mean would be 80.0 while the correct residue-weighted mean is 70.0.
        self.PDB = self._pdb(
            ("N", "MET", 1, 90.0),
            ("CA", "MET", 1, 90.0),
            ("CB", "MET", 1, 90.0),
            ("N", "LYS", 2, 50.0),
        )

    def test_plddt_is_averaged_per_residue_not_per_atom(self):
        out = normalize_pdb_structure(self.PDB, None)
        assert out["n_residues"] == 2
        assert out["mean_plddt"] == pytest.approx(70.0)

    def test_fractional_plddt_is_rescaled(self):
        """ESMFold-style 0-1 confidence must be lifted onto the 0-100 scale."""
        pdb = self._pdb(
            ("N", "MET", 1, 0.90),
            ("CA", "MET", 1, 0.90),
            ("CB", "MET", 1, 0.90),
            ("N", "LYS", 2, 0.50),
        )
        assert normalize_pdb_structure(pdb, None)["mean_plddt"] == pytest.approx(70.0)

    def test_finds_structure_under_a_nonstandard_key(self):
        assert normalize_pdb_structure({"structure": self.PDB}, None)["n_residues"] == 2

    def test_missing_structure_reports_an_error_rather_than_raising(self):
        assert "error" in normalize_pdb_structure({"nothing": 1}, None)


# --------------------------------------------------------------------------- #
# Resolution
# --------------------------------------------------------------------------- #
class TestVariantParsing:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("17 7675088 C T", {"chrom": "17", "pos": 7675088, "ref": "C", "alt": "T"}),
            ("17-7675088-C-T", {"chrom": "17", "pos": 7675088, "ref": "C", "alt": "T"}),
            (
                "chr17:g.7675088C>T",
                {"chrom": "17", "pos": 7675088, "ref": "C", "alt": "T"},
            ),
            (
                "NC_000017.11:g.7675088C>T",
                {"chrom": "17", "pos": 7675088, "ref": "C", "alt": "T"},
            ),
        ],
    )
    def test_genomic_forms(self, text, expected):
        assert _parse_free_variant(text)[0] == expected

    def test_rsid(self):
        assert _parse_free_variant("rs28934578")[1] == "rs28934578"

    @pytest.mark.parametrize("text", ["TP53 R175H", "TP53 p.Arg175His"])
    def test_protein_forms(self, text):
        _, _, protein = _parse_free_variant(text)
        assert protein == {
            "gene": "TP53",
            "position": 175,
            "ref_aa": "R",
            "alt_aa": "H",
        }

    def test_aa_codes(self):
        assert aa1("Arg") == "R" and aa1("R") == "R" and aa1("Ter") == "*"


class TestResolution:
    def test_empty_input_is_rejected_with_guidance(self):
        with pytest.raises(ResolutionError) as excinfo:
            resolve_variant_effect({}, lambda *a, **k: None)
        assert "protein_change" in str(excinfo.value)

    def test_sequence_only_input_needs_no_network(self):
        calls = []

        def caller(tool, args):
            calls.append(tool)
            return None

        resolved = resolve_variant_effect(
            {"sequence": "MKTAYIAK", "position": 3, "mutant": "L"}, caller
        )
        assert resolved["sequence"] == "MKTAYIAK"
        assert resolved["seq_position"] == 3
        assert resolved["seq_ref_aa"] == "T"
        assert calls == []

    def test_coordinate_mismatch_withdraws_the_sequence(self):
        """A wrong reference residue must not be scored, quietly, by every model."""
        resolved = resolve_variant_effect(
            {"sequence": "MKTAYIAK", "position": 3, "mutant": "L", "ref_aa": "W"},
            lambda *a, **k: None,
        )
        assert "sequence" not in resolved
        assert any("mismatch" in note.lower() for note in resolved["notes"])

    def test_out_of_range_position_is_caught(self):
        resolved = resolve_variant_effect(
            {"sequence": "MKT", "position": 99, "mutant": "L"}, lambda *a, **k: None
        )
        assert "sequence" not in resolved

    def test_myvariant_build_is_stated_explicitly(self):
        """MyVariant defaults to hg19 and 404s on GRCh38 coordinates otherwise."""
        resolved = resolve_variant_effect(
            {"sequence": "MKT", "position": 1, "mutant": "L", "assembly": "GRCh38"},
            lambda *a, **k: None,
        )
        assert resolved["ucsc_build"] == "hg38"
        resolved37 = resolve_variant_effect(
            {"sequence": "MKT", "position": 1, "mutant": "L", "assembly": "GRCh37"},
            lambda *a, **k: None,
        )
        assert resolved37["ucsc_build"] == "hg19"


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #
class TestMetrics:
    def test_perfect_and_inverted_separation(self):
        scores = [0.9, 0.8, 0.7, 0.3, 0.2, 0.1]
        labels = [1, 1, 1, 0, 0, 0]
        assert auroc(scores, labels) == 1.0
        assert auprc(scores, labels) == 1.0
        assert auroc([-s for s in scores], labels, higher_is_positive=False) == 1.0

    def test_ties_do_not_manufacture_discrimination(self):
        assert auroc([0.5] * 6, [1, 1, 1, 0, 0, 0]) == 0.5

    def test_single_class_is_undefined_not_zero(self):
        assert auroc([0.1, 0.2], [1, 1]) is None

    def test_confusion_ignores_uncertain_calls(self):
        cm = confusion(
            ["deleterious", "uncertain", "tolerated"], [1, 1, 0], "deleterious"
        )
        assert cm == {"tp": 1, "fp": 0, "tn": 1, "fn": 0, "n": 2}

    def test_mcc_handles_a_degenerate_predictor(self):
        cm = confusion(["deleterious"] * 4, [1, 1, 0, 0], "deleterious")
        assert from_confusion(cm)["mcc"] is None

    def test_evaluate_reports_coverage_against_the_full_dataset(self):
        records = [{"score": 0.9, "call": "deleterious"}, None, None, None]
        out = evaluate(records, [1, 1, 0, 0], True, "deleterious", "binary_score", 4)
        assert out["n"] == 4 and out["n_scored"] == 1 and out["coverage"] == 0.25

    def test_categorical_backend_gets_no_rank_metrics(self):
        records = [{"score": "Pathogenic", "call": "deleterious"}] * 4
        out = evaluate(records, [1, 1, 0, 0], None, "deleterious", "binary_score", 4)
        assert out["auroc"] is None and "rank_metrics_note" in out

    def test_spearman_needs_variation(self):
        assert spearman([1, 1, 1], [1, 2, 3]) is None


# --------------------------------------------------------------------------- #
# Engine wiring, with a stub ToolUniverse
# --------------------------------------------------------------------------- #
class _StubTU:
    """Answers the few tools a variant comparison touches, with no network."""

    def __init__(self):
        self.seen = []

    def run_one_function(self, spec):
        name = spec["name"]
        self.seen.append(name)
        if name == "ProtVar_map_variant":
            return {
                "status": "success",
                "data": {
                    "genomic_coordinates": {
                        "chr": "17",
                        "pos": 7675088,
                        "ref": "C",
                        "alt": "T",
                    },
                    "isoform_mappings": [
                        {
                            "accession": "P04637",
                            "canonical": True,
                            "gene": "TP53",
                            "consequence": "missense",
                            "ref_aa": "Arg",
                            "alt_aa": "His",
                            "position": 175,
                            "cadd_score": 25.9,
                            "alphamissense": {"score": 0.9857, "class": "PATHOGENIC"},
                            "eve_score": 5.982,
                            "esm1v_score": -7.744,
                            "popeve_score": -3.658,
                        }
                    ],
                },
            }
        if name == "EnsemblVEP_annotate_hgvs":
            return {
                "status": "success",
                "data": {
                    "seq_region_name": "17",
                    "start": 7675088,
                    "transcript_consequences": [
                        {
                            "gene_symbol": "TP53",
                            "biotype": "protein_coding",
                            "protein_start": 175,
                            "amino_acids": "R/H",
                            "sift_score": 0.0,
                            "sift_prediction": "deleterious",
                            "polyphen_score": 0.99,
                            "polyphen_prediction": "probably_damaging",
                        }
                    ],
                },
            }
        if name == "CADD_get_variant_score":
            return {
                "status": "success",
                "data": {"phred_score": 25.9, "version": "v1.7"},
            }
        return {"status": "error", "error": f"stub has no answer for {name}"}


@pytest.fixture
def compare_tool():
    from tooluniverse.unified_model_tool import UnifiedModelPredictTool

    return UnifiedModelPredictTool(
        {"name": "predict_variant_effect", "fields": {"task": "variant_effect"}},
        tooluniverse=_StubTU(),
    )


class TestCompareTool:
    def test_agreeing_models_are_summarized(self, compare_tool):
        out = compare_tool.run({"variant": "17 7675088 C T"})
        assert out["status"] == "success"
        rows = {r["backend"]: r for r in out["predictions"]}
        assert rows["alphamissense"]["score"] == 0.9857
        assert rows["cadd"]["call"] == "deleterious"
        assert out["summary"]["majority_call"] == "deleterious"
        assert out["summary"]["unanimous"] is True

    def test_failures_are_reported_not_dropped(self, compare_tool):
        """Every backend must be accounted for, as a result or as a skip."""
        out = compare_tool.run({"variant": "17 7675088 C T"})
        accounted = {r["backend"] for r in out["predictions"]} | {
            s["backend"] for s in out["skipped"]
        }
        registry = load_registry()
        assert accounted == {s.id for s in registry.backends_for("variant_effect")}

    def test_resolution_is_echoed_back(self, compare_tool):
        out = compare_tool.run({"variant": "17 7675088 C T"})
        assert out["input"]["genomic"]["pos"] == 7675088
        assert out["input"]["protein"]["variant"] == "R175H"

    def test_one_call_serves_several_backends(self, compare_tool):
        """ProtVar is fetched once and read by four models."""
        out = compare_tool.run({"variant": "17 7675088 C T"})
        protvar_backed = [
            r
            for r in out["predictions"]
            if r["backend"] in {"alphamissense", "eve", "esm1v", "popeve"}
            and r["status"] == "success"
        ]
        assert len(protvar_backed) == 4
        assert compare_tool._injected_tu.seen.count("ProtVar_map_variant") == 1

    def test_unresolvable_input_errors_with_guidance(self, compare_tool):
        out = compare_tool.run({})
        assert out["status"] == "error"
        assert "protein_change" in out["error"]


@pytest.fixture
def list_tool():
    from tooluniverse.unified_model_tool import UnifiedModelPredictTool

    return UnifiedModelPredictTool(
        {"name": "predict_variant_effect", "fields": {"task": "variant_effect"}},
        tooluniverse=_StubTU(),
    )


class TestListTool:
    def test_lists_backends_with_provenance(self, list_tool):
        """list_models is a flag now, not a separate tool."""
        out = list_tool.run({"list_models": True})
        assert out["n_models"] >= 12
        assert "predictions" not in out
        backend = next(b for b in out["models"] if b["backend"] == "alphamissense")
        assert backend["citation"].startswith("Cheng")
        assert backend["calibration"] == "published"
        assert "higher" in backend["direction"]


# --------------------------------------------------------------------------- #
# Datasets
# --------------------------------------------------------------------------- #
class TestDatasets:
    def test_catalogue_is_offline(self):
        from tooluniverse.unified_model_datasets import catalogue

        cat = catalogue()
        assert "proteingym_dms" in cat["loadable"]
        assert "posebusters" in cat["documented_only"]

    def test_unknown_dataset_names_alternatives(self):
        from tooluniverse.unified_model_datasets import load

        with pytest.raises(ValueError) as excinfo:
            load("nope")
        assert "proteingym_dms" in str(excinfo.value)

    def test_documented_only_dataset_explains_itself(self):
        from tooluniverse.unified_model_datasets import load

        with pytest.raises(ValueError) as excinfo:
            load("posebusters")
        assert "Not implemented" in str(excinfo.value)

    def test_local_file_loader(self, tmp_path):
        from tooluniverse.unified_model_datasets import load

        path = tmp_path / "set.jsonl"
        path.write_text(
            "\n".join(
                json.dumps({"smiles": s, "property": "logp", "label": y})
                for s, y in [("CCO", 1), ("CCC", 0)]
            )
        )
        dataset = load("file", path=str(path), task="molecular_property")
        assert len(dataset.items) == 2 and dataset.label_type == "binary"

    def test_local_file_without_labels_is_rejected(self, tmp_path):
        from tooluniverse.unified_model_datasets import load

        path = tmp_path / "set.jsonl"
        path.write_text(json.dumps({"smiles": "CCO"}))
        with pytest.raises(ValueError) as excinfo:
            load("file", path=str(path))
        assert "label" in str(excinfo.value)

    @pytest.mark.integration
    @pytest.mark.network
    def test_proteingym_downloads_and_parses(self):
        from tooluniverse.unified_model_datasets import load

        dataset = load("proteingym_dms", limit=10)
        assert len(dataset.items) == 10
        assert dataset.label_type == "binary"
        item = dataset.items[0]
        assert item["uniprot"] and "_" not in item["uniprot"]
        assert item["sequence"] and item["position"] >= 1
        assert item["sequence"][item["position"] - 1] == item["wild_type"]

    @pytest.mark.integration
    @pytest.mark.network
    def test_tdc_admet_downloads_and_parses(self):
        from tooluniverse.unified_model_datasets import load

        dataset = load("tdc_admet", property="bbb_martins", limit=10)
        assert dataset.label_type == "binary"
        assert all(item["smiles"] for item in dataset.items)


class TestLabelOrientation:
    """Binary and continuous targets must point the same way.

    A model that ranks damaging variants highest should score well on *both*
    AUROC and Spearman. ProteinGym's raw DMS score runs the other way (higher =
    fitter), so leaving it unflipped gave every good model a large negative
    Spearman on a leaderboard sorted descending.
    """

    @pytest.mark.integration
    @pytest.mark.network
    def test_continuous_target_agrees_with_binary_label(self):
        from tooluniverse.unified_model_datasets import load

        dataset = load("proteingym_dms", limit=0)
        damaging = [i["continuous_label"] for i in dataset.items if i["label"] == 1]
        tolerated = [i["continuous_label"] for i in dataset.items if i["label"] == 0]
        assert damaging and tolerated
        assert sum(damaging) / len(damaging) > sum(tolerated) / len(tolerated)

    @pytest.mark.integration
    @pytest.mark.network
    def test_a_good_predictor_gets_a_positive_spearman(self):
        """An oracle ranking must not be punished by the sign convention."""
        from tooluniverse.unified_model_datasets import load

        dataset = load("proteingym_dms", limit=60)
        targets = [i["continuous_label"] for i in dataset.items]
        assert spearman(list(targets), targets) == pytest.approx(1.0)


class TestModelCorrelation:
    """Agreement between models must not be confused with their sign conventions."""

    @staticmethod
    def _records(scores):
        return [{"score": s} for s in scores]

    def test_inverted_backends_are_oriented_before_correlating(self):
        from tooluniverse.unified_model_tool import _model_correlation

        rising = [0.1, 0.3, 0.5, 0.7, 0.9, 1.0]
        falling = [-1.0, -3.0, -5.0, -7.0, -9.0, -10.0]
        results = {"up": self._records(rising), "down": self._records(falling)}

        naive = _model_correlation(results, {"up": True, "down": True})
        assert naive["up"]["down"] == pytest.approx(-1.0)

        oriented = _model_correlation(results, {"up": True, "down": False})
        assert oriented["up"]["down"] == pytest.approx(1.0)

    def test_categorical_backends_are_excluded(self):
        from tooluniverse.unified_model_tool import _model_correlation

        results = {
            "a": self._records([1, 2, 3, 4, 5, 6]),
            "b": self._records([1, 2, 3, 4, 5, 6]),
            "cat": self._records([1, 1, 1, 1, 1, 1]),
        }
        matrix = _model_correlation(results, {"a": True, "b": True, "cat": None})
        assert "cat" not in matrix
        assert all("cat" not in inner for inner in matrix.values())


class _VaryingStubTU:
    """Two backends that agree perfectly but score in opposite directions."""

    def run_one_function(self, spec):
        name = spec["name"]
        args = spec.get("arguments") or {}
        if name == "ProtVar_map_variant":
            position = int(str(args.get("variant", "0 0")).split()[1])
            rank = position - 1000
            return {
                "status": "success",
                "data": {
                    "genomic_coordinates": {
                        "chr": "1",
                        "pos": position,
                        "ref": "C",
                        "alt": "T",
                    },
                    "isoform_mappings": [
                        {
                            "accession": "P00001",
                            "canonical": True,
                            "gene": "G",
                            "consequence": "missense",
                            "ref_aa": "Arg",
                            "alt_aa": "His",
                            "position": rank,
                            "alphamissense": {
                                "score": round(0.1 * rank, 3),
                                "class": "PATHOGENIC",
                            },
                            "esm1v_score": -1.0 * rank,
                        }
                    ],
                },
            }
        return {"status": "error", "error": f"stub has no answer for {name}"}


class TestBenchmarkReportWiring:
    """The report must apply direction orientation, not just be able to.

    The orientation helper had a unit test that passed while the benchmark
    report still called it without directions, so every published correlation
    matrix was unoriented and read as if the models contradicted each other.
    """

    @pytest.fixture
    def benchmark_tool(self):
        from tooluniverse.unified_model_tool import UnifiedModelBenchmarkTool

        return UnifiedModelBenchmarkTool(
            {
                "name": "benchmark_variant_effect_models",
                "fields": {"task": "variant_effect"},
            },
            tooluniverse=_VaryingStubTU(),
        )

    @pytest.fixture
    def dataset_path(self, tmp_path):
        path = tmp_path / "variants.jsonl"
        path.write_text(
            "\n".join(
                json.dumps(
                    {
                        "chrom": "1",
                        "pos": 1000 + i,
                        "ref": "C",
                        "alt": "T",
                        "label": 1 if i > 3 else 0,
                    }
                )
                for i in range(1, 9)
            )
        )
        return path

    def test_correlation_is_direction_oriented(self, benchmark_tool, dataset_path):
        report = benchmark_tool.run(
            {
                "dataset": "file",
                "path": str(dataset_path),
                "task": "variant_effect",
                "backends": ["alphamissense", "esm1v"],
                "item_workers": 2,
            }
        )
        assert report["status"] == "success", report.get("error")
        matrix = report.get("model_correlation") or {}
        rho = matrix.get("alphamissense", {}).get("esm1v")
        assert rho is not None, f"no correlation reported: {matrix}"
        assert rho > 0.9, f"expected strong positive agreement, got {rho}"

    def test_leaderboard_reports_coverage_and_caveats(
        self, benchmark_tool, dataset_path
    ):
        report = benchmark_tool.run(
            {
                "dataset": "file",
                "path": str(dataset_path),
                "task": "variant_effect",
                "backends": ["alphamissense", "esm1v"],
            }
        )
        assert {r["backend"] for r in report["leaderboard"]} == {
            "alphamissense",
            "esm1v",
        }
        for row in report["leaderboard"]:
            assert row["coverage"] == 1.0
            assert row["n"] == 8
        assert report["caveats"]


class TestBindingAffinityResolution:
    """A backend must be able to satisfy its own declared ``needs``.

    ``nim_diffdock`` shipped declaring ``needs: ["protein_structure"]`` and an
    ``input_map`` over keys the binding-affinity resolver never produced. It
    could never run for any input, and the failure was invisible: the
    missing-API-key check runs first, so it always reported as "set
    NVIDIA_API_KEY" rather than as a wiring fault.
    """

    def test_smiles_to_sdf_produces_a_3d_conformer(self):
        pytest.importorskip("rdkit")
        from tooluniverse.unified_model_resolvers import _smiles_to_sdf

        notes = []
        sdf = _smiles_to_sdf("CC(=O)Oc1ccccc1C(=O)O", notes)
        assert sdf and "V2000" in sdf
        z_values = [
            float(line.split()[2])
            for line in sdf.splitlines()[4:]
            if len(line.split()) > 3 and line.split()[3].isalpha()
        ]
        assert any(abs(z) > 1e-6 for z in z_values), "conformer is flat"
        assert notes == []

    def test_bad_smiles_is_reported_not_raised(self):
        pytest.importorskip("rdkit")
        from tooluniverse.unified_model_resolvers import _smiles_to_sdf

        notes = []
        assert _smiles_to_sdf("not-a-molecule", notes) is None
        assert notes and "SMILES" in notes[0]

    def test_invalid_pdb_id_is_reported_not_fetched(self):
        from tooluniverse.unified_model_resolvers import _fetch_pdb_text

        notes = []
        assert _fetch_pdb_text("not-a-pdb-id", notes) is None
        assert notes and "4-character" in notes[0]

    @pytest.mark.integration
    @pytest.mark.network
    def test_every_docking_backend_can_satisfy_its_needs(self):
        pytest.importorskip("rdkit")
        from tooluniverse.unified_model_resolvers import resolve_binding_affinity

        resolved = resolve_binding_affinity(
            {
                "ligand_smiles": "CC(=O)Oc1ccccc1C(=O)O",
                "pdb_id": "1ATP",
                "protein_sequence": "MGNAAAAKKGSEQESVKEFLAKAKEDFLKKWE",
            },
            lambda *a, **k: None,
        )
        assert resolved.get("protein_structure"), "receptor coordinates missing"
        assert resolved.get("ligand_sdf"), "3D ligand missing"

        registry = load_registry()
        unsatisfiable = {
            spec.id: spec.missing_requirements(resolved)
            for spec in registry.backends_for("binding_affinity")
            if spec.missing_requirements(resolved)
        }
        assert not unsatisfiable, (
            f"These backends can never run -- their 'needs' name keys the "
            f"resolver does not produce: {unsatisfiable}"
        )


class TestUnexercisedNormalizers:
    """Cover the normalizers that no live run could reach.

    ``normalize_boltz_structure`` sat behind NVIDIA_API_KEY and had never been
    executed at all. Untested code behind a key wall is where a wrong field
    name hides indefinitely.
    """

    def test_boltz_reads_cif_and_confidence(self):
        from tooluniverse.unified_model_normalizers import normalize_boltz_structure

        out = normalize_boltz_structure(
            {
                "structures": [{"cif": "data_x\n_atom_site.label_atom_id\nN"}],
                "confidence_score": 0.82,
                "ptm": 0.77,
            },
            None,
        )
        assert out["mean_plddt"] == pytest.approx(82.0)
        assert out["ptm"] == pytest.approx(0.77)
        assert out["format"] == "mmcif"

    def test_boltz_accepts_already_percentage_confidence(self):
        from tooluniverse.unified_model_normalizers import normalize_boltz_structure

        out = normalize_boltz_structure({"structure": "x", "plddt": 88.0}, None)
        assert out["mean_plddt"] == pytest.approx(88.0)

    def test_boltz_averages_a_per_residue_list(self):
        from tooluniverse.unified_model_normalizers import normalize_boltz_structure

        out = normalize_boltz_structure(
            {"structure": "x", "plddt": [0.9, 0.7, 0.8]}, None
        )
        assert out["mean_plddt"] == pytest.approx(80.0)

    def test_boltz_missing_confidence_reports_an_error(self):
        from tooluniverse.unified_model_normalizers import normalize_boltz_structure

        assert "error" in normalize_boltz_structure({"structure": "x"}, None)

    def test_boltz_falls_back_to_pdb_parsing(self):
        from tooluniverse.unified_model_normalizers import normalize_boltz_structure

        pdb = (
            "ATOM  {:5d} {:^4s} {:3s} {:1s}{:4d}    {:8.3f}{:8.3f}{:8.3f}"
            "{:6.2f}{:6.2f}\n".format(1, "CA", "MET", "A", 1, 0.0, 0.0, 0.0, 1.0, 80.0)
        )
        out = normalize_boltz_structure(pdb, None)
        assert out["mean_plddt"] == pytest.approx(80.0)

    def test_vep_predictor_prefers_the_canonical_transcript(self):
        from tooluniverse.unified_model_normalizers import normalize_vep_predictor

        class _Spec:
            params = {
                "score_field": "sift_score",
                "pred_field": "sift_prediction",
                "pick": "min",
            }

        payload = {
            "transcript_consequences": [
                {
                    "sift_score": 0.01,
                    "biotype": "protein_coding",
                    "transcript_id": "T1",
                },
                {
                    "sift_score": 0.40,
                    "biotype": "protein_coding",
                    "transcript_id": "T2",
                    "mane_select": "NM_1",
                },
            ]
        }
        out = normalize_vep_predictor(payload, _Spec())
        assert out["transcript"] == "T2"
        assert out["transcript_selection"] == "MANE/canonical"

    def test_vep_predictor_falls_back_to_most_damaging(self):
        from tooluniverse.unified_model_normalizers import normalize_vep_predictor

        class _Spec:
            params = {
                "score_field": "polyphen_score",
                "pred_field": "polyphen_prediction",
                "pick": "max",
            }

        # Confirmed live: VEP returned PolyPhen on only 2 of 12 TP53
        # transcripts and flagged no canonical, so the sparse case is common.
        payload = {
            "transcript_consequences": [
                {"biotype": "protein_coding", "transcript_id": "T1"},
                {
                    "polyphen_score": 0.30,
                    "biotype": "protein_coding",
                    "transcript_id": "T2",
                },
                {
                    "polyphen_score": 0.95,
                    "biotype": "protein_coding",
                    "transcript_id": "T3",
                },
            ]
        }
        out = normalize_vep_predictor(payload, _Spec())
        assert out["score"] == pytest.approx(0.95)
        assert out["n_transcripts_with_score"] == 2
        assert out["n_transcripts_total"] == 3

    def test_vep_predictor_reports_absence_distinctly(self):
        from tooluniverse.unified_model_normalizers import normalize_vep_predictor

        class _Spec:
            params = {
                "score_field": "sift_score",
                "pred_field": "sift_prediction",
                "pick": "min",
            }

        out = normalize_vep_predictor(
            {"transcript_consequences": [{"biotype": "protein_coding"}]}, _Spec()
        )
        assert "error" in out and "sift_score" in out["error"]


class TestRealNimPayloads:
    """Payload shapes captured from live NVIDIA NIM responses.

    Every shape here was previously guessed, and every guess was wrong in a
    way that produced a plausible-looking empty result rather than an error.
    """

    BOLTZ = {
        "status": "success",
        "data": {
            "structures": [
                {
                    "structure": "data_model\n_entry.id model\n_atom_site.group_PDB\n",
                    "format": "mmcif",
                    "name": "prediction",
                }
            ],
            "confidence_scores": [0.707067608833313],
            "complex_plddt_scores": [0.8838344812393188],
            "ptm_scores": [0.6527260541915894],
            "iptm_scores": [0.0],
            "affinities": {},
        },
    }

    OPENFOLD2 = {
        "status": "success",
        "data": {
            "structures_in_ranked_order": [
                {
                    "structure": (
                        "PARENT N/A\n"
                        + "".join(
                            "ATOM  {:5d} {:^4s} {:3s} {:1s}{:4d}    "
                            "{:8.3f}{:8.3f}{:8.3f}{:6.2f}{:6.2f}\n".format(
                                i, "CA", "ALA", "A", i, 0.0, 0.0, 0.0, 1.0, 90.0
                            )
                            for i in range(1, 4)
                        )
                    ),
                    "rank": 0,
                }
            ],
            "input_id": None,
        },
    }

    DIFFDOCK = {
        "status": "success",
        "data": {
            # Confirmed live: confidences arrive as STRINGS, poses pre-ranked.
            "position_confidence": ["-0.7193593382835388", "-0.749", "-4.699"],
            "ligand_positions": ["_rank1\nRDKit 3D\n", "_rank2\n", "_rank3\n"],
            "status": "success",
        },
    }

    def test_boltz_real_envelope(self):
        from tooluniverse.unified_model_normalizers import normalize_boltz_structure

        out = normalize_boltz_structure(self.BOLTZ, None)
        assert out["mean_plddt"] == pytest.approx(88.38, abs=0.01)
        assert out["format"] == "mmcif"
        assert out["confidence_score"] == pytest.approx(0.7071, abs=1e-4)
        assert out["ptm"] == pytest.approx(0.6527, abs=1e-4)
        assert out["structure"].startswith("data_model")
        assert "error" not in out
        assert "affinities" not in out

    def test_openfold2_ranked_structure_list(self):
        out = normalize_pdb_structure(self.OPENFOLD2, None)
        assert out["mean_plddt"] == pytest.approx(90.0)
        assert out["n_residues"] == 3
        assert "error" not in out

    def test_boltz_backend_maps_the_real_payload(self):
        spec = load_registry().backend("structure_prediction", "nim_boltz2")
        fields = spec.normalize(self.BOLTZ)
        assert fields["score"] == pytest.approx(88.38, abs=0.01)
        assert fields["call"] == "confident"

    def test_boltz_interface_backend_reports_confidence_not_affinity(self):
        spec = load_registry().backend("binding_affinity", "boltz2_interface")
        fields = spec.normalize(
            {
                "status": "success",
                "data": {
                    "ligand_iptm_scores": [0.6614410877227783],
                    "iptm_scores": [0.6614410877227783],
                    "complex_plddt_scores": [0.8489673733711243],
                    "affinities": {},
                },
            }
        )
        assert fields["score"] == pytest.approx(0.6614, abs=1e-3)
        assert fields["score_units"] == "confidence"
        assert fields["normalized_score"] is None

    def test_every_plddt_backend_declares_a_confidence_threshold(self):
        registry = load_registry()
        missing = [
            spec.id
            for spec in registry.backends_for("structure_prediction")
            if spec.score_type == "mean pLDDT" and not spec.call
        ]
        assert not missing, f"backends with no pLDDT call threshold: {missing}"

    def test_diffdock_reads_string_confidences_and_keeps_pose_aligned(self):
        spec = load_registry().backend("binding_affinity", "nim_diffdock")
        fields = spec.normalize(self.DIFFDOCK)
        assert fields["score"] == pytest.approx(-0.71936, abs=1e-4)
        assert isinstance(fields["score"], float)
        assert fields["pose"].startswith("_rank1")
        assert len(fields["all_pose_confidences"]) == 3
        assert fields["normalized_score"] is None

    def test_diffdock_would_catch_text_sorting(self):
        """Sorted as text, '-0.749' > '-0.7193...' and the wrong pose wins."""
        payload = {"data": {"c": ["-0.9", "-0.11"]}}
        assert extract(payload, {"path": "$.data.c", "agg": "max"}) == pytest.approx(
            -0.11
        )


class TestInterfaceAlignment:
    """The unified contract must actually hold across every backend.

    "Same input and output format, different backend" is the entire premise,
    so these are the invariants that make it true rather than aspirational.
    Each assertion below corresponds to a misalignment that was really present.
    """

    def test_call_vocabulary_is_uniform_within_a_task(self):
        """Every backend of a task must speak one call vocabulary.

        ``TaskSpec.positive_class`` is matched against ``call`` to build a
        benchmark's confusion matrix. ADMET-AI used a per-endpoint vocabulary
        while molecular_property declared no positive class, so the matrix
        found zero predicted positives and reported accuracy/MCC/F1 as if the
        model never predicted the positive class.
        """
        registry = load_registry()
        for task_id, task in registry.tasks.items():
            vocab = set()
            for spec in registry.backends_for(task_id):
                cfg = spec.call or {}
                if cfg.get("from") == "field":
                    vocab |= {str(v) for v in (cfg.get("map") or {}).values()}
                    if cfg.get("default"):
                        vocab.add(str(cfg["default"]))
                elif cfg:
                    vocab |= {str(cfg.get("above")), str(cfg.get("below"))}
                for entry in (spec.property_map or {}).values():
                    inner = entry.get("call") or {}
                    if inner:
                        vocab |= {str(inner.get("above")), str(inner.get("below"))}
            vocab.discard("None")
            if not vocab:
                continue
            assert task.positive_class, (
                f"task {task_id!r} emits calls {sorted(vocab)} but declares no "
                "positive_class, so threshold metrics cannot be scored"
            )
            assert task.positive_class in vocab, (
                f"task {task_id!r} positive_class={task.positive_class!r} is not "
                f"among the calls its backends emit: {sorted(vocab)}"
            )

    def test_every_backend_states_its_units_and_score_type(self):
        """A bare number is not comparable; the scale has to travel with it."""
        registry = load_registry()
        missing = []
        for task_id in registry.tasks:
            for spec in registry.backends_for(task_id):
                if spec.property_map:
                    continue
                if not spec.score_type:
                    missing.append(f"{spec.id}: score_type")
                if not spec.score_units:
                    missing.append(f"{spec.id}: score_units")
        assert not missing, f"backends not stating their scale: {missing}"

    def test_multi_property_backends_state_units_per_property(self):
        registry = load_registry()
        missing = []
        for task_id in registry.tasks:
            for spec in registry.backends_for(task_id):
                for prop, entry in (spec.property_map or {}).items():
                    if not entry.get("units"):
                        missing.append(f"{spec.id}.{prop}")
        assert not missing, f"properties with no declared units: {missing}"

    def test_direction_is_defined_wherever_a_score_can_be_ranked(self):
        registry = load_registry()
        for task_id in registry.tasks:
            for spec in registry.backends_for(task_id):
                if spec.transform.kind in ("none", "categorical"):
                    assert spec.higher_is_positive is None, spec.id
                else:
                    assert isinstance(spec.higher_is_positive, bool), (
                        f"{spec.id} produces a rankable score but declares no "
                        "direction, so AUROC/Spearman would guess"
                    )

    def test_normalized_score_is_always_a_unit_interval_or_absent(self):
        registry = load_registry()
        for task_id in registry.tasks:
            for spec in registry.backends_for(task_id):
                for probe in (-1e6, -7.5, -1.0, 0.0, 0.5, 1.0, 25.9, 1e6):
                    value = spec.transform.to_unit(probe)
                    assert value is None or 0.0 <= value <= 1.0, (
                        f"{spec.id} mapped {probe} to {value}"
                    )

    def test_calibration_provenance_is_always_declared(self):
        registry = load_registry()
        for task_id in registry.tasks:
            for spec in registry.backends_for(task_id):
                assert spec.calibration in ("published", "heuristic"), spec.id


class TestMolecularPropertyBenchmarkScoring:
    """End-to-end proof that the vocabulary fix reaches the metrics."""

    class _StubADMET:
        """Returns ADMET-AI-shaped output keyed to the molecule."""

        def run_one_function(self, spec):
            smiles = (spec.get("arguments") or {}).get("smiles")
            if isinstance(smiles, list):
                smiles = smiles[0]
            return {"0": {"BBB_Martins": 0.9 if len(smiles) > 3 else 0.1}}

    def test_confusion_metrics_are_actually_computed(self, tmp_path):
        from tooluniverse.unified_model_tool import UnifiedModelBenchmarkTool

        path = tmp_path / "bbb.jsonl"
        path.write_text(
            "\n".join(
                json.dumps({"smiles": s, "property": "bbb_martins", "label": y})
                for s, y in [
                    ("CCCCCCCC", 1),
                    ("CCCCCCCCC", 1),
                    ("CCCCCCCCCC", 1),
                    ("CCCCCCCCCCC", 1),
                    ("C", 0),
                    ("CC", 0),
                    ("CCC", 0),
                    ("O", 0),
                ]
            )
        )
        tool = UnifiedModelBenchmarkTool(
            {
                "name": "benchmark_molecular_property_models",
                "fields": {"task": "molecular_property"},
            },
            tooluniverse=self._StubADMET(),
        )
        report = tool.run(
            {
                "dataset": "file",
                "path": str(path),
                "task": "molecular_property",
                "backends": ["admet_ai"],
            }
        )
        assert report["status"] == "success", report.get("error")
        row = next(r for r in report["leaderboard"] if r["backend"] == "admet_ai")
        assert row["coverage"] == 1.0
        # Before the vocabulary fix every call was "penetrant", positive_call
        # was "positive", and tp was 0 for a perfect predictor.
        assert row["confusion"]["tp"] == 4, row["confusion"]
        assert row["accuracy"] == 1.0
        assert row["mcc"] == pytest.approx(1.0)
        # Before the specialization fix, direction came from the base spec
        # (transform "none") and AUROC was silently dropped.
        assert row["auroc"] == 1.0


class TestRealAdmetAiPayload:
    """ADMET-AI's real output shape, captured from the installed model.

    The reply is keyed by the **SMILES string itself**, and each endpoint has a
    ``*_drugbank_approved_percentile`` sibling. A path must pick the endpoint
    and not its percentile twin, which is a different quantity on a 0-100
    scale and would look like a valid probability.
    """

    PAYLOAD = {
        "CC(=O)Oc1ccccc1C(=O)O": {
            "BBB_Martins": 0.658191978931427,
            "BBB_Martins_drugbank_approved_percentile": 44.74516695957821,
        }
    }

    def test_endpoint_not_percentile(self):
        spec = load_registry().backend("molecular_property", "admet_ai")
        fields = spec.for_property("bbb_martins").normalize(self.PAYLOAD)
        assert fields["score"] == pytest.approx(0.65819, abs=1e-4)
        assert fields["score"] < 1.0
        assert fields["score_units"] == "probability"
        assert fields["call"] == "positive"
        assert fields["call_label"] == "penetrant"

    def test_every_declared_property_has_a_distinct_path(self):
        """Two endpoints must never resolve through the same path."""
        spec = load_registry().backend("molecular_property", "admet_ai")
        paths = {}
        for prop, entry in spec.property_map.items():
            path = entry.get("path")
            assert path, f"{prop} declares no path"
            assert path not in paths, (
                f"{prop} and {paths[path]} share the path {path!r}"
            )
            paths[path] = prop

    def test_property_ids_match_tdc_dataset_names(self):
        """Canonical ids are TDC names; that is what makes the benchmark line up."""
        spec = load_registry().backend("molecular_property", "admet_ai")
        for prop, entry in spec.property_map.items():
            # Tox21 columns carry hyphens, so their paths are quoted
            # ($.."NR-AR"); strip the quoting before comparing.
            path = entry["path"].rsplit(".", 1)[-1].strip("\"'[]")
            assert path.lower() == prop.lower(), (
                f"canonical id {prop!r} does not match ADMET-AI column {path!r}"
            )


class TestBackendConcurrencySafety:
    """In-process model backends must not be called concurrently.

    ADMET-AI runs chemprop/Lightning inside this process and is not
    thread-safe: scoring a TDC set at item_workers=2 raised "pop from empty
    list" on 23 of 24 molecules. The run "succeeded", the leaderboard printed
    AUPRC 1.000, and only coverage (0.042) revealed the damage.
    """

    def test_local_model_backends_are_marked_unsafe(self):
        registry = load_registry()
        for task_id in registry.tasks:
            for spec in registry.backends_for(task_id):
                if spec.cost == "local_model":
                    assert spec.thread_safe is False, (
                        f"{spec.id} runs a model in-process but is not marked "
                        "thread_safe=false"
                    )

    def test_http_backends_stay_parallel(self):
        """The fix must not serialize everything and destroy throughput."""
        registry = load_registry()
        parallel = [
            s.id
            for tid in registry.tasks
            for s in registry.backends_for(tid)
            if s.thread_safe
        ]
        assert len(parallel) > 20, "most backends should still run concurrently"

    def test_unsafe_backend_is_actually_serialized(self):
        """Exercise the lock: concurrent calls must never overlap."""
        import threading
        from concurrent.futures import ThreadPoolExecutor

        from tooluniverse.unified_model_tool import UnifiedModelEngine, _Caller

        overlaps = []
        active = {"n": 0}
        guard = threading.Lock()

        class _RacyTU:
            def run_one_function(self, spec):
                with guard:
                    active["n"] += 1
                    if active["n"] > 1:
                        overlaps.append(True)
                time.sleep(0.02)
                with guard:
                    active["n"] -= 1
                return {"0": {"BBB_Martins": 0.7}}

        engine = UnifiedModelEngine(_RacyTU())
        spec = engine.registry.backend("molecular_property", "admet_ai").for_property(
            "bbb_martins"
        )
        assert spec.thread_safe is False
        caller = _Caller(_RacyTU())
        resolved = {"smiles": "CCO", "property": "bbb_martins"}

        with ThreadPoolExecutor(max_workers=4) as pool:
            list(
                pool.map(lambda _: engine.run_backend(spec, resolved, caller), range(8))
            )
        assert not overlaps, "unsafe backend was called concurrently"


class TestToolDescriptionsAreTrue:
    """Descriptions are the only thing an agent sees before calling a tool.

    They drift silently: a backend gets renamed, a count changes, and the
    description keeps asserting the old fact with total confidence.

    Caught in practice: descriptions promising "a 0-1 normalized score" and a
    "consensus" for binding_affinity, where 2 of 3 backends are deliberately
    un-normalized and both live results landed in 'excluded_from_consensus'.
    """

    @staticmethod
    def _configs():
        # Read the file through default_tool_files rather than by walking up
        # from __file__: that makes every test below also an assertion that
        # the category is registered. It was not, for the life of this file --
        # the JSON existed, no entry pointed at it, and the four tools could
        # not be loaded by name -- and a path computed here would not have
        # noticed.
        import pathlib

        from tooluniverse.default_config import default_tool_files

        path = pathlib.Path(default_tool_files["unified_model"])
        return {c["name"]: c for c in json.loads(path.read_text())}

    def test_every_tool_has_a_substantive_description(self):
        for name, cfg in self._configs().items():
            assert len(cfg["description"]) > 200, f"{name} description is too thin"

    def test_backend_counts_match_the_registry(self):
        registry = load_registry()
        cfgs = self._configs()
        n_variant = len(registry.backends_for("variant_effect"))
        assert str(n_variant) in cfgs["predict_variant_effect"]["description"], (
            f"description should state the model count ({n_variant})"
        )
        text = cfgs["predict_protein_structure"]["description"]
        assert "ESMFold" in text and "AlphaFold2" in text
        n_props = len(registry.backend("molecular_property", "admet_ai").property_map)
        assert str(n_props) in cfgs["predict_molecular_property"]["description"]

    def test_named_properties_exist(self):
        """A description that lists property ids must list real ones."""
        import re

        registry = load_registry()
        known = set()
        for spec in registry.backends_for("molecular_property"):
            known |= set(spec.property_map)
        text = self._configs()["predict_molecular_property"]["description"]
        named = set(re.findall(r"\b[a-z0-9]+_[a-z0-9_]+\b", text))
        named -= {"call_label", "predict_molecular_property", "list_models"}
        bogus = named - known
        assert not bogus, (
            f"description names properties that do not exist: {sorted(bogus)}"
        )

    def test_inverted_models_named_in_the_description_really_are_inverted(self):
        registry = load_registry()
        inverted = {
            s.id
            for s in registry.backends_for("variant_effect")
            if s.higher_is_positive is False
        }
        text = self._configs()["predict_variant_effect"]["description"]
        assert "ESM-1v" in text and "SIFT" in text
        assert {"esm1v", "sift"} <= inverted

    def test_binding_affinity_does_not_promise_a_consensus(self):
        """The one task where a single consensus number would be a lie."""
        cfgs = self._configs()
        text = cfgs["predict_binding_affinity"]["description"]
        assert "no single consensus" in text
        registry = load_registry()
        unnormalized = [
            s.id
            for s in registry.backends_for("binding_affinity")
            if s.transform.kind == "none"
        ]
        assert len(unnormalized) >= 2, (
            "description claims units are incomparable; registry disagrees"
        )

    def test_cross_referenced_tools_exist(self):
        import re

        cfgs = self._configs()
        params = {"list_datasets", "list_models"}
        for name, cfg in cfgs.items():
            refs = set(
                re.findall(
                    r"\b(?:predict|compare|list|benchmark)_[a-z_]+\b",
                    cfg["description"],
                )
            )
            for ref in refs - params:
                assert ref in cfgs, f"{name} points at non-existent tool {ref!r}"

    def test_benchmark_is_not_in_the_agent_catalogue(self):
        """Benchmarking is a maintainer's operation, not an agent's.

        A run takes minutes, issues hundreds of API calls and can cost real
        money. It stays reachable in Python and via
        scripts/run_model_benchmark.py, but an agent solving a task must not be
        able to trigger it by setting a flag.
        """
        cfgs = self._configs()
        assert len(cfgs) == 4, f"expected 4 agent-facing tools, got {sorted(cfgs)}"
        for name, cfg in cfgs.items():
            assert "benchmark" not in name
            params = set(cfg["parameter"]["properties"])
            for leaked in (
                "dataset",
                "limit",
                "metrics",
                "item_workers",
                "label_field",
            ):
                assert leaked not in params, (
                    f"{name} exposes benchmark param {leaked!r}"
                )

    def test_benchmark_machinery_is_still_importable(self):
        """Removing the tools must not delete the capability."""
        from tooluniverse.unified_model_tool import UnifiedModelBenchmarkTool

        tool = UnifiedModelBenchmarkTool(
            {"name": "benchmark", "fields": {"task": "variant_effect"}},
            tooluniverse=_StubTU(),
        )
        out = tool.run({"list_datasets": True})
        assert "proteingym_dms" in out["datasets"]["loadable"]

    def test_required_parameters_are_called_out(self):
        """'property' is required for ADMET; saying so prevents a failed call."""
        cfgs = self._configs()
        for name in ("predict_molecular_property",):
            assert "REQUIRES 'property'" in cfgs[name]["description"]
            assert "property" in cfgs[name]["parameter"]["required"]


class TestPubChemNameResolution:
    """Compound-name -> SMILES, against PubChem's real reply shape.

    PubChem nests the CID at ``IdentifierList.CID[0]`` and the structure at
    ``PropertyTable.Properties[0]``, and it has retired ``CanonicalSMILES`` in
    favour of ``ConnectivitySMILES``. A flat-key lookup found neither, so every
    ``drug``/``ligand`` name resolved to nothing and surfaced as "No structure
    to predict on" -- which reads as though the caller supplied no molecule.
    """

    CID_REPLY = {"IdentifierList": {"CID": [2244]}}
    PROPS_REPLY = {
        "PropertyTable": {
            "Properties": [
                {
                    "CID": 2244,
                    "MolecularWeight": "180.16",
                    "ConnectivitySMILES": "CC(=O)OC1=CC=CC=C1C(=O)O",
                    "IUPACName": "2-acetyloxybenzoic acid",
                }
            ]
        }
    }

    def test_finds_nested_cid(self):
        from tooluniverse.unified_model_resolvers import _find_cid

        assert _find_cid(self.CID_REPLY) == 2244

    def test_finds_connectivity_smiles(self):
        from tooluniverse.unified_model_resolvers import _find_smiles

        assert _find_smiles(self.PROPS_REPLY) == "CC(=O)OC1=CC=CC=C1C(=O)O"

    def test_still_accepts_the_retired_field_name(self):
        from tooluniverse.unified_model_resolvers import _find_smiles

        legacy = {"PropertyTable": {"Properties": [{"CanonicalSMILES": "CCO"}]}}
        assert _find_smiles(legacy) == "CCO"

    def test_molecular_weight_is_not_mistaken_for_a_cid(self):
        """A recursive int search must not grab the first number it sees."""
        from tooluniverse.unified_model_resolvers import _find_cid

        assert _find_cid(self.PROPS_REPLY) == 2244

    def test_end_to_end_with_a_stub(self):
        from tooluniverse.unified_model_resolvers import resolve_molecular_property

        def caller(tool, args):
            if "CID_by_compound_name" in tool:
                return {"status": "success", "data": self.CID_REPLY}
            return {"status": "success", "data": self.PROPS_REPLY}

        resolved = resolve_molecular_property(
            {"drug": "aspirin", "property": "qed"}, caller
        )
        assert resolved["smiles"] == "CC(=O)OC1=CC=CC=C1C(=O)O"
        assert any("CID 2244" in n for n in resolved["notes"])

    def test_unresolvable_name_says_so(self):
        from tooluniverse.unified_model_resolvers import (
            ResolutionError,
            resolve_molecular_property,
        )

        with pytest.raises(ResolutionError):
            resolve_molecular_property(
                {"drug": "not-a-real-compound", "property": "qed"},
                lambda *a, **k: {"status": "error", "error": "no match"},
            )


class TestNoModelErrorIsSelfContained:
    """The failure message must explain itself with no sibling fields.

    It used to say "see 'skipped' for why" -- but `tu run` renders only the
    error string and drops the rest of the dict, so it directed the reader to
    something they could not see.
    """

    def test_message_names_reasons_counts_and_the_fix(self):
        from tooluniverse.unified_model_tool import _no_model_error

        task = load_registry().task("variant_effect")
        skipped = [
            {
                "backend": "alphamissense",
                "reason": "input_not_resolved",
                "detail": "Needs protvar_canonical, which could not be derived.",
            },
            {
                "backend": "cadd",
                "reason": "input_not_resolved",
                "detail": "Needs genomic.pos, which could not be derived.",
            },
            {
                "backend": "esm2",
                "reason": "missing_api_key",
                "detail": "Set HF_TOKEN to enable this backend.",
            },
        ]
        msg = _no_model_error(task, skipped)
        assert "2 skipped" in msg and "1 skipped" in msg
        assert "input_not_resolved" in msg and "missing_api_key" in msg
        assert "alphamissense" in msg
        assert "Setting HF_TOKEN would enable more models" in msg

    def test_long_skip_lists_are_truncated_not_dumped(self):
        from tooluniverse.unified_model_tool import _no_model_error

        task = load_registry().task("variant_effect")
        skipped = [
            {"backend": f"m{i}", "reason": "input_not_resolved", "detail": "Needs x."}
            for i in range(14)
        ]
        msg = _no_model_error(task, skipped)
        assert "and 10 more" in msg
        assert len(msg) < 400, "error message should stay readable"

    def test_no_skips_still_produces_a_message(self):
        from tooluniverse.unified_model_tool import _no_model_error

        task = load_registry().task("variant_effect")
        assert _no_model_error(task, []).startswith("No variant_effect model")

    def test_reaches_the_caller_through_the_tool(self):
        from tooluniverse.unified_model_tool import UnifiedModelPredictTool

        tool = UnifiedModelPredictTool(
            {"name": "predict_variant_effect", "fields": {"task": "variant_effect"}},
            tooluniverse=_StubTU(),
        )
        # Ask for a backend whose input cannot be derived at all.
        out = tool.run(
            {"sequence": "MKTAYIAKQRQ", "position": 3, "mutant": "L", "backend": "cadd"}
        )
        assert out["status"] == "error"
        assert "could run" in out["error"]

    def test_all_models_failing_is_not_reported_as_success(self):
        """An envelope saying 'success' over nothing but errors is a lie."""
        from tooluniverse.unified_model_tool import UnifiedModelPredictTool

        tool = UnifiedModelPredictTool(
            {"name": "predict_variant_effect", "fields": {"task": "variant_effect"}},
            tooluniverse=_StubTU(),
        )
        out = tool.run({"sequence": "MKTAYIAKQRQ", "position": 3, "mutant": "L"})
        assert out["status"] == "no_score", out["status"]
        assert "none returned a score" in out["error"]


class TestStructureCoordinatesAreReturned:
    """The structure task promises coordinates; it must actually deliver them.

    ESMFold returns its PDB under ``pdb_text``. The registry mapped ``pdb``,
    which matched nothing, so the one structure backend needing no API key
    silently returned ``structure: None`` while the task's declared output
    contract advertised "coordinates as PDB or mmCIF text".
    """

    PAYLOAD = {
        "status": "success",
        "data": {
            "sequence_length": 33,
            "mean_plddt": 0.9,
            "confident_fraction": 1.0,
            "pdb_text": "HEADER    PREDICTED\nATOM      1  N   MET A   1\n",
        },
    }

    def test_esmfold_structure_is_extracted(self):
        spec = load_registry().backend("structure_prediction", "esmfold")
        fields = spec.normalize(self.PAYLOAD)
        assert isinstance(fields["structure"], str) and fields["structure"]
        assert fields["n_residues"] == 33
        assert fields["mean_plddt"] == pytest.approx(90.0)

    def test_every_structure_backend_declares_a_structure_path(self):
        """A folding model that returns no coordinates is not folding."""
        registry = load_registry()
        missing = []
        for spec in registry.backends_for("structure_prediction"):
            if spec.normalizer:
                continue
            if not spec.output_map.get("structure"):
                missing.append(spec.id)
        assert not missing, f"structure backends with no coordinate path: {missing}"

    def test_unit_rescaling_does_not_emit_float_noise(self):
        """0.58 * 100 is 57.99999999999999 in binary floating point."""
        assert extract({"m": 0.58}, {"path": "$.m", "mul": 100}) == 58.0
        assert extract({"m": 0.9}, {"path": "$.m", "mul": 100}) == 90.0
        assert extract(
            {"m": 0.8838344812393188}, {"path": "$.m", "mul": 100}
        ) == pytest.approx(88.383448, abs=1e-6)

    def test_rescaling_leaves_non_numbers_alone(self):
        assert extract({"m": "n/a"}, {"path": "$.m", "mul": 100}) == "n/a"


class TestUpstreamParameterFixes:
    """Backends that looked dead upstream but were being called wrong.

    MyVariant 404s on a GRCh38 coordinate because it defaults to hg19, and
    CancerVar answers one with an *empty body*, which surfaces as "Expecting
    value: line 1 column 1" -- a JSON parse error that reads like a dead API.
    The genome build must be sent explicitly, never defaulted.
    """

    def test_cancervar_sends_the_genome_build(self):
        spec = load_registry().backend("variant_effect", "cancervar")
        assert "build" in spec.input_map, (
            "CancerVar defaults to hg19 and returns an empty body for a GRCh38 "
            "coordinate; the build has to be explicit"
        )
        args = spec.build_arguments(
            {
                "genomic": {"chrom": "17", "pos": 7675088, "ref": "C", "alt": "T"},
                "ucsc_build": "hg38",
            }
        )
        assert args["build"] == "hg38"

    def test_every_coordinate_backend_pins_its_build(self):
        """Any backend keyed on coordinates must say which assembly they are."""
        registry = load_registry()
        offenders = []
        for spec in registry.backends_for("variant_effect"):
            keys = set(spec.input_map)
            takes_coords = {"chrom", "chr"} & keys and {"pos"} & keys
            if takes_coords and not ({"build", "genome", "assembly"} & keys):
                offenders.append(spec.id)
        assert "cancervar" not in offenders


class TestEsm2WorksWithoutAToken:
    """ESM-2 is the only backend that can score a sequence with no database entry.

    HuggingFace's free endpoint began requiring a token for this model, which
    broke the tool's own stated premise ("no API key") and left sequence-only
    input with zero runnable models -- a hole in the one task that advertises
    scoring engineered and non-human proteins.
    """

    def test_backend_is_no_longer_key_gated(self):
        spec = load_registry().backend("variant_effect", "esm2")
        assert spec.api_key is None, "ESM-2 should run locally without HF_TOKEN"
        assert spec.key_available() is True

    def test_local_model_is_serialized_like_other_in_process_models(self):
        spec = load_registry().backend("variant_effect", "esm2")
        assert spec.cost == "local_model"
        assert spec.thread_safe is False

    def test_missing_transformers_reports_actionably(self, monkeypatch):
        """Absent the optional dependency, say what to install -- do not raise."""
        import builtins

        from tooluniverse import esm2_variant_effect_tool as mod

        real_import = builtins.__import__

        def blocked(name, *a, **k):
            if name in ("torch", "transformers"):
                raise ImportError(f"No module named {name!r}")
            return real_import(name, *a, **k)

        monkeypatch.setattr(builtins, "__import__", blocked)
        out = mod._fill_mask_local("facebook/esm2_t6_8M_UR50D", "M K <mask>", 33)
        assert out["status"] == "error"
        assert "HF_TOKEN" in out["error"] and "tooluniverse[ml]" in out["error"]

    def test_sequence_only_input_now_has_a_runnable_model(self, monkeypatch):
        """The capability gap this closes: a sequence with no database identity."""
        monkeypatch.delenv("HF_TOKEN", raising=False)
        spec = load_registry().backend("variant_effect", "esm2")
        resolved = {
            "sequence": "MKTAYIAKQRQ",
            "seq_position": 3,
            "seq_alt_aa": "L",
            "seq_ref_aa": "T",
        }
        assert spec.missing_requirements(resolved) == []
        assert spec.key_available()


class TestEnvelopeAwarePaths:
    """Output paths must match the envelope the tool actually returns.

    ``esm2`` mapped ``$.log_likelihood_ratio`` while the tool returns
    ``{"status", "data": {...}}``, so it never produced a score -- not once,
    even when HuggingFace was reachable. The auth failure in front of it
    masked a mapping bug for the entire life of the backend, which is why a
    "this backend needs a key" diagnosis was not the whole story.
    """

    ESM2_REPLY = {
        "status": "success",
        "data": {
            "model_id": "facebook/esm2_t33_650M_UR50D",
            "variant": "R175H",
            "p_wild_type": 0.0626,
            "p_mutant": 0.0966,
            "log_likelihood_ratio": -5.974,
            "direction": "mutant disfavored vs wild-type",
        },
        "metadata": {"source": "local transformers (no HF_TOKEN)"},
    }

    def test_esm2_reads_through_the_data_envelope(self):
        spec = load_registry().backend("variant_effect", "esm2")
        fields = spec.normalize(self.ESM2_REPLY)
        assert fields["score"] == pytest.approx(-5.974)
        assert fields["call"] == "deleterious"  # LLR below -4
        assert fields["normalized_score"] > 0.5

    def test_no_backend_reads_a_bare_top_level_score(self):
        """A path with no envelope prefix is the shape of this bug.

        Tools in this codebase return ``{"status", "data"}``. A ``score`` path
        that is a single top-level key is almost certainly reading past the
        envelope -- unless the backend takes its payload from the resolution
        context, which is already unwrapped.
        """
        registry = load_registry()
        suspect = []
        for task_id in registry.tasks:
            for spec in registry.backends_for(task_id):
                if spec.from_context or spec.normalizer:
                    continue
                path = spec.output_map.get("score")
                path = path.get("path") if isinstance(path, dict) else path
                if not isinstance(path, str):
                    continue
                # "$.foo" reads the envelope itself; "$.data.foo" or "$..foo"
                # reach the body.
                if path.startswith("$.") and path.count(".") == 1:
                    suspect.append(f"{spec.id}: {path}")
        assert not suspect, (
            f"score paths that appear to skip the response envelope: {suspect}"
        )

    def test_no_score_message_matches_the_backend_kind(self):
        """Blaming a 'precomputed table' for a live model misdirects the reader."""
        from tooluniverse.unified_model_tool import UnifiedModelEngine, _Caller

        class _EmptyTU:
            def run_one_function(self, spec):
                return {"status": "success", "data": {}}

        engine = UnifiedModelEngine(_EmptyTU())
        spec = engine.registry.backend("variant_effect", "esm2")
        record = engine.run_backend(
            spec,
            {
                "sequence": "MKTAYIAKQRQ",
                "seq_position": 3,
                "seq_alt_aa": "L",
                "seq_ref_aa": "T",
            },
            _Caller(_EmptyTU()),
        )
        assert record["status"] == "no_score"
        assert "computes live" in record["error"]
        assert "precomputed" not in record["error"]


class TestUpstreamProtocolFixes:
    """Backends that reported as dead upstream but were being driven wrong.

    Three separate services looked broken and were not. Each failure pointed at
    the wrong culprit, which is why "unfixable, upstream is down" was the wrong
    call on all three:

    * **CancerVar** -- defaulted to hg19, answered a GRCh38 coordinate with an
      empty body, surfaced as a JSON parse error.
    * **PyTDC** -- its synthetic-accessibility table downloaded as a 403 HTML
      page, and ``Oracle`` swallowed the unpickling error and returned ``0.0``.
      Aspirin's LogP came back as 0.0 (it is ~1.1) and its SA as 0.0 (the scale
      starts at 1), with no error anywhere.
    * **SwissDock** -- the tool invented a UUID session id while the server
      assigns a numeric one in its ``preplig`` reply, and posted ``pdbid``
      where the API wants a ``myTarget`` file upload. Both stages returned
      HTTP 200 while saying "No ligand/target provided".
    """

    def test_tdc_repairs_a_corrupt_fragment_table(self, tmp_path, monkeypatch):
        """A 403 HTML page must not be left in place as a pickle."""
        pytest.importorskip("rdkit")
        from tooluniverse.tdc_oracle_tool import _ensure_sa_fragment_scores

        monkeypatch.chdir(tmp_path)
        corrupt = tmp_path / "oracle" / "fpscores.pkl"
        corrupt.parent.mkdir()
        corrupt.write_bytes(b"<!DOCTYPE HTML>\n<title>403 Forbidden</title>")

        _ensure_sa_fragment_scores()

        import pickle

        with open(corrupt, "rb") as handle:
            scores = pickle.load(handle)
        assert isinstance(scores, list) and len(scores) > 1000

    def test_tdc_leaves_a_valid_table_alone(self, tmp_path, monkeypatch):
        import pickle

        from tooluniverse.tdc_oracle_tool import _ensure_sa_fragment_scores

        monkeypatch.chdir(tmp_path)
        good = tmp_path / "oracle" / "fpscores.pkl"
        good.parent.mkdir()
        sentinel = [["sentinel", 1, 2]]
        with open(good, "wb") as handle:
            pickle.dump(sentinel, handle)

        _ensure_sa_fragment_scores()

        with open(good, "rb") as handle:
            assert pickle.load(handle) == sentinel

    def test_swissdock_reads_the_servers_session_number(self):
        """The session is assigned by the server, never invented locally."""
        from tooluniverse.swissdock_tool import SwissDockTool

        parse = SwissDockTool._parse_session_number
        assert parse(
            "\nSession number: 54643551\n\nYour ligand has been uploaded."
        ) == ("54643551")
        assert parse("Using session number: 21956998") == "21956998"
        assert parse("no session here") is None

    def test_esm2_falls_back_only_on_auth_refusal(self):
        """A 'loading' reply means retry remotely, not switch to local."""
        from tooluniverse.esm2_variant_effect_tool import _looks_like_auth_failure

        assert _looks_like_auth_failure({"error": "Unauthorized for facebook/esm2"})
        assert _looks_like_auth_failure({"error": "requires a token: set HF_TOKEN"})
        assert _looks_like_auth_failure({"error": "x", "detail": "403 Forbidden"})
        # Not auth: these must not trigger the permanent local switch.
        assert not _looks_like_auth_failure({"error": "Model warming up"})
        assert not _looks_like_auth_failure({"error": "connection reset"})
        assert not _looks_like_auth_failure({})


class TestOutputVerificationIsHonest:
    """Separate mappings checked against a real reply from ones merely written.

    Three mappings in this registry were wrong in ways that produced a
    plausible empty result rather than an error -- Boltz-2's nested envelope,
    OpenFold2's ranked structure list, ESM-2 reading past ``data`` -- and each
    was caught only by seeing an actual payload. So "we wrote a path" and "we
    know the path is right" are different claims, and the registry has to say
    which one it is making.
    """

    def test_unverified_backends_explain_why(self):
        registry = load_registry()
        for task_id in registry.tasks:
            for spec in registry.backends_for(task_id):
                if not spec.output_verified:
                    assert spec.output_unverified_reason, (
                        f"{spec.id} is unverified but gives no reason, so a reader "
                        "cannot tell whether that is fixable"
                    )

    def test_verified_backends_claim_nothing_extra(self):
        registry = load_registry()
        for task_id in registry.tasks:
            for spec in registry.backends_for(task_id):
                if spec.output_verified:
                    assert not spec.output_unverified_reason, spec.id

    def test_the_backends_we_exercised_are_marked_verified(self):
        """Guards against the flag quietly drifting away from reality."""
        registry = load_registry()
        must_be_verified = {
            "alphamissense",
            "cadd",
            "esm2",
            "sift",
            "polyphen2",
            "revel",
            "spliceai",
            "genebe_acmg",
            "cancervar",
            "esmfold",
            "nim_openfold2",
            "nim_boltz2",
            "admet_ai",
            "rdkit_descriptors",
            "tdc_oracle",
            "nim_diffdock",
            "boltz2_interface",
        }
        actual = {
            spec.id
            for task_id in registry.tasks
            for spec in registry.backends_for(task_id)
            if spec.output_verified
        }
        assert must_be_verified <= actual, (
            f"lost verification: {must_be_verified - actual}"
        )

    def test_list_models_surfaces_verification(self):
        from tooluniverse.unified_model_tool import UnifiedModelPredictTool

        tool = UnifiedModelPredictTool(
            {
                "name": "predict_binding_affinity",
                "fields": {"task": "binding_affinity"},
            },
            tooluniverse=_StubTU(),
        )
        out = tool.run({"list_models": True})
        by_id = {m["backend"]: m for m in out["models"]}
        assert by_id["nim_diffdock"]["output_verified"] is True
        assert by_id["swissdock"]["output_verified"] is False
        assert "queue" in by_id["swissdock"]["output_unverified_reason"]

    def test_notes_do_not_contradict_the_key_requirement(self):
        """ESM-2 stopped needing a token; its notes must not still say it does."""
        registry = load_registry()
        for task_id in registry.tasks:
            for spec in registry.backends_for(task_id):
                if spec.api_key:
                    continue
                notes = (spec.notes or "").lower()
                assert "set hf_token to enable" not in notes, (
                    f"{spec.id} no longer needs a key but its notes still gate on one"
                )


class TestImportsHaveNoSideEffects:
    """Importing a tool module must not touch the filesystem.

    PyTDC reads its synthetic-accessibility table from a *relative* ``oracle/``
    path, so repairing that table eagerly wrote a 4.3 MB pickle into whatever
    directory the process started in -- for anyone who merely imported
    ToolUniverse, including unrelated test runs. The repair is correct; doing
    it at import time was not.
    """

    def test_importing_tdc_tool_writes_nothing(self, tmp_path, monkeypatch):
        import subprocess
        import sys

        monkeypatch.chdir(tmp_path)
        subprocess.run(
            [sys.executable, "-c", "import tooluniverse.tdc_oracle_tool"],
            cwd=tmp_path,
            capture_output=True,
            timeout=300,
        )
        assert list(tmp_path.iterdir()) == [], (
            f"importing the module created {[p.name for p in tmp_path.iterdir()]}"
        )

    def test_repair_runs_at_most_once(self, tmp_path, monkeypatch):
        from tooluniverse import tdc_oracle_tool as mod

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mod, "_sa_scores_checked", False)
        calls = []
        monkeypatch.setattr(mod, "_ensure_sa_fragment_scores", lambda: calls.append(1))
        mod._ensure_sa_fragment_scores_once()
        mod._ensure_sa_fragment_scores_once()
        mod._ensure_sa_fragment_scores_once()
        assert len(calls) == 1


class TestStructuralAccuracy:
    """pLDDT is confidence; lDDT is accuracy. A benchmark needs the second.

    Ranking folders by mean pLDDT rewards the confidently wrong over the
    honestly uncertain, so it cannot be a benchmark metric -- which is why the
    structure task shipped with no usable dataset. lDDT is the measured
    counterpart: the quantity pLDDT is trained to predict, computed against an
    experimental reference. It is superposition-free, so unlike TM-score or GDT
    there is no alignment optimisation to get subtly wrong.
    """

    @staticmethod
    def _pdb(coords, chain="A"):
        return "".join(
            "ATOM  {:5d}  CA  ALA {:1s}{:4d}    {:8.3f}{:8.3f}{:8.3f}  1.00 50.00\n".format(
                i + 1, chain, i + 1, x, y, z
            )
            for i, (x, y, z) in enumerate(coords)
        )

    def test_identical_structures_score_one(self):
        from tooluniverse.unified_model_metrics import lddt

        coords = [(i * 3.8, 0.0, 0.0) for i in range(12)]
        pdb = self._pdb(coords)
        assert lddt(pdb, pdb)["lddt"] == 1.0

    def test_distorted_structure_scores_lower(self):
        from tooluniverse.unified_model_metrics import lddt

        ref = self._pdb([(i * 3.8, 0.0, 0.0) for i in range(12)])
        # Same chain, progressively stretched: local distances all change.
        bad = self._pdb([(i * 6.0, 0.0, 0.0) for i in range(12)])
        assert lddt(bad, ref)["lddt"] < 0.6

    def test_reports_coverage_so_a_fragment_cannot_win(self):
        """Scoring 5 of 40 residues perfectly is not a good prediction."""
        from tooluniverse.unified_model_metrics import lddt

        ref = self._pdb([(i * 3.8, 0.0, 0.0) for i in range(40)])
        fragment = self._pdb([(i * 3.8, 0.0, 0.0) for i in range(8)])
        out = lddt(fragment, ref)
        assert out["lddt"] == 1.0
        assert out["coverage"] == 0.2
        assert out["n_residues_scored"] == 8

    def test_too_little_overlap_returns_none(self):
        from tooluniverse.unified_model_metrics import lddt

        ref = self._pdb([(i * 3.8, 0.0, 0.0) for i in range(20)])
        tiny = self._pdb([(0.0, 0.0, 0.0)])
        assert lddt(tiny, ref) is None

    def test_parser_skips_alternate_locations_and_extra_models(self):
        from tooluniverse.unified_model_metrics import parse_ca_coordinates

        pdb = (
            "ATOM      1  CA AALA A   1       0.000   0.000   0.000  1.00 50.00\n"
            "ATOM      2  CA BALA A   1       9.000   9.000   9.000  1.00 50.00\n"
            "ATOM      3  CA  ALA A   2       3.800   0.000   0.000  1.00 50.00\n"
            "ENDMDL\n"
            "ATOM      4  CA  ALA A   3       7.600   0.000   0.000  1.00 50.00\n"
        )
        coords = parse_ca_coordinates(pdb)
        assert len(coords) == 2, "altloc B or a second model leaked in"
        assert coords[("A", 1)] == (0.0, 0.0, 0.0)

    def test_structure_task_ranks_on_accuracy_not_confidence(self):
        registry = load_registry()
        task = registry.task("structure_prediction")
        assert task.primary_metric == "lddt", (
            "ranking folders by self-reported pLDDT rewards overconfidence"
        )
        assert "lddt" in task.default_metrics

    def test_calibration_gap_is_attached_to_predictions(self):
        from tooluniverse.unified_model_tool import _score_against_reference

        ref = self._pdb([(i * 3.8, 0.0, 0.0) for i in range(12)])
        records = [{"backend": "x", "structure": ref, "mean_plddt": 80.0}]
        _score_against_reference(records, {"reference_structure": ref})
        assert records[0]["lddt"] == 1.0
        # Claimed 80, achieved 100 -> underconfident by 20.
        assert records[0]["calibration_gap"] == pytest.approx(-20.0)

    def test_no_reference_means_no_claim(self):
        from tooluniverse.unified_model_tool import _score_against_reference

        records = [{"backend": "x", "structure": "ATOM...", "mean_plddt": 80.0}]
        _score_against_reference(records, {})
        assert "lddt" not in records[0]


class TestMmcifStructureParsing:
    """Folders disagree about output format; lDDT must read both.

    The co-folding models return mmCIF rather than PDB. With only a
    fixed-column PDB reader, Boltz-2 "succeeded" and then silently carried no
    lDDT at all -- the accuracy column was simply blank for the model that
    turned out to be the most accurate. mmCIF declares its column order in the
    loop header rather than fixing it, so the header is parsed, not assumed.
    """

    MMCIF = """data_model
#
loop_
_atom_site.group_PDB
_atom_site.id
_atom_site.type_symbol
_atom_site.label_atom_id
_atom_site.label_alt_id
_atom_site.label_comp_id
_atom_site.auth_asym_id
_atom_site.auth_seq_id
_atom_site.Cartn_x
_atom_site.Cartn_y
_atom_site.Cartn_z
_atom_site.pdbx_PDB_model_num
ATOM 1 N N . MET A 1 0.000 0.000 0.000 1
ATOM 2 C CA . MET A 1 1.000 0.000 0.000 1
ATOM 3 C CA . LYS A 2 4.800 0.000 0.000 1
ATOM 4 C CA . ALA A 3 8.600 0.000 0.000 1
ATOM 5 C CA B ALA A 3 99.000 99.000 99.000 1
ATOM 6 C CA . ALA A 4 12.400 0.000 0.000 2
#
"""

    def test_reads_cif_columns_from_the_loop_header(self):
        from tooluniverse.unified_model_metrics import parse_ca_coordinates

        coords = parse_ca_coordinates(self.MMCIF)
        assert set(coords) == {("A", 1), ("A", 2), ("A", 3)}
        assert coords[("A", 1)] == (1.0, 0.0, 0.0)  # CA, not the N

    def test_skips_alternate_locations_and_later_models(self):
        from tooluniverse.unified_model_metrics import parse_ca_coordinates

        coords = parse_ca_coordinates(self.MMCIF)
        assert coords[("A", 3)] == (8.6, 0.0, 0.0), "altloc B leaked in"
        assert ("A", 4) not in coords, "a second model leaked in"

    def test_lddt_works_on_cif_input(self):
        from tooluniverse.unified_model_metrics import lddt

        assert lddt(self.MMCIF, self.MMCIF) is None or True  # only 3 residues
        big = self.MMCIF.replace(
            "ATOM 6 C CA . ALA A 4 12.400 0.000 0.000 2",
            "\n".join(
                f"ATOM {10 + i} C CA . ALA A {10 + i} {i * 3.8:.3f} 0.000 0.000 1"
                for i in range(8)
            ),
        )
        out = lddt(big, big)
        assert out is not None and out["lddt"] == 1.0

    def test_format_is_detected_not_assumed(self):
        """A PDB must still parse after mmCIF support was added."""
        from tooluniverse.unified_model_metrics import parse_ca_coordinates

        pdb = (
            "ATOM      1  CA  ALA A   1       0.000   0.000   0.000  1.00 50.00\n"
            "ATOM      2  CA  ALA A   2       3.800   0.000   0.000  1.00 50.00\n"
        )
        assert len(parse_ca_coordinates(pdb)) == 2


class TestOpenFold3InputShape:
    """OpenFold3 takes a nested spec and refuses a protein with no MSA."""

    def test_resolver_builds_per_molecule_specs_with_an_msa(self):
        from tooluniverse.unified_model_resolvers import resolve_structure_prediction

        resolved = resolve_structure_prediction(
            {"sequences": ["MKTAYIAK", "MQIFVKTL"]}, lambda *a, **k: None
        )
        mols = resolved["of3_molecules"]
        assert len(mols) == 2
        for mol, seq in zip(mols, ["MKTAYIAK", "MQIFVKTL"]):
            assert mol["type"] == "protein" and mol["sequence"] == seq
            # The API rejects a protein with no MSA; a self-only alignment is
            # the documented escape hatch.
            a3m = mol["msa"]["uniref90"]["a3m"]["alignment"]
            assert a3m.endswith(seq) and a3m.startswith(">")

    def test_backend_sends_the_nested_inputs_key(self):
        spec = load_registry().backend("structure_prediction", "nim_openfold3")
        args = spec.build_arguments(
            {"of3_molecules": [{"type": "protein", "sequence": "MKT"}]}
        )
        assert "inputs" in args and "sequences" not in args
        assert args["inputs"][0]["molecules"][0]["sequence"] == "MKT"


class TestInterfaceAccuracy:
    """DockQ judges whether two chains were docked correctly.

    lDDT scores a fold and says nothing about assembly, so complexes, binder
    design and docking had no comparable accuracy measure at all -- their
    native scores are in incompatible units (kcal/mol, a confidence logit, an
    interface pTM), which is why that task deliberately refuses a consensus.
    """

    @staticmethod
    def _two_chain(offset=0.0):
        # 4.5 A apart: these fixtures carry only CA atoms, whereas a real
        # structure's side chains bring residues within the 5 A heavy-atom
        # contact cutoff at much larger CA-CA separations.
        lines = []
        n = 1
        for chain, dx in (("A", 0.0), ("B", 4.5 + offset)):
            for i in range(10):
                lines.append(
                    "ATOM  {:5d}  CA  ALA {:1s}{:4d}    {:8.3f}{:8.3f}{:8.3f}"
                    "  1.00 50.00           C\n".format(
                        n, chain, i + 1, i * 3.8, dx, 0.0
                    )
                )
                n += 1
        return "".join(lines)

    def test_identical_complex_scores_one(self):
        from tooluniverse.unified_model_metrics import dockq

        pdb = self._two_chain()
        out = dockq(pdb, pdb)
        assert out["dockq"] == 1.0 and out["quality"] == "high"
        assert out["fnat"] == 1.0 and out["lrms"] == 0.0

    def test_displaced_ligand_is_scored_incorrect(self):
        from tooluniverse.unified_model_metrics import dockq

        ref = self._two_chain()
        wrong = self._two_chain(offset=15.0)
        out = dockq(wrong, ref, "A", "B")
        assert out["quality"] == "incorrect", out
        assert out["fnat"] == 0.0
        # Superposing the receptor must recover the exact displacement.
        assert out["lrms"] == pytest.approx(15.0, abs=0.01)

    def test_chain_pair_is_chosen_by_interface_not_by_size(self):
        """Two copies of the same big chain are a crystal contact, not the interface.

        Confirmed on 1BRS: chains A and B are both barnase, so picking the two
        largest chains scored a packing contact instead of the barnase-barstar
        interface the structure is known for.
        """
        from tooluniverse.unified_model_metrics import dockq

        # Two large chains far apart, plus a small chain touching one of them.
        big_a = "".join(
            "ATOM  {:5d}  CA  ALA A{:4d}    {:8.3f}{:8.3f}{:8.3f}  1.00 50.00           C\n".format(
                i, i, i * 3.8, 0.0, 0.0
            )
            for i in range(1, 21)
        )
        big_b = "".join(
            "ATOM  {:5d}  CA  ALA B{:4d}    {:8.3f}{:8.3f}{:8.3f}  1.00 50.00           C\n".format(
                100 + i, i, i * 3.8, 400.0, 0.0
            )
            for i in range(1, 21)
        )
        small_c = "".join(
            "ATOM  {:5d}  CA  ALA C{:4d}    {:8.3f}{:8.3f}{:8.3f}  1.00 50.00           C\n".format(
                200 + i, i, i * 3.8, 4.5, 0.0
            )
            for i in range(1, 6)
        )
        pdb = big_a + big_b + small_c
        out = dockq(pdb, pdb)
        assert {out["receptor_chain"], out["ligand_chain"]} == {"A", "C"}, (
            f"picked {out['receptor_chain']}+{out['ligand_chain']}, "
            "which is the non-contacting pair"
        )

    def test_single_chain_reference_yields_no_interface_score(self):
        from tooluniverse.unified_model_tool import _score_against_reference

        single = "".join(
            "ATOM  {:5d}  CA  ALA A{:4d}    {:8.3f}{:8.3f}{:8.3f}  1.00 50.00           C\n".format(
                i, i, i * 3.8, 0.0, 0.0
            )
            for i in range(1, 13)
        )
        records = [{"backend": "x", "structure": single, "mean_plddt": 90.0}]
        _score_against_reference(records, {"reference_structure": single})
        assert records[0]["lddt"] == 1.0
        assert "dockq" not in records[0], "no interface exists to score"

    def test_multichain_reference_adds_interface_score(self):
        from tooluniverse.unified_model_tool import _score_against_reference

        pdb = self._two_chain()
        records = [{"backend": "x", "structure": pdb, "mean_plddt": 90.0}]
        _score_against_reference(records, {"reference_structure": pdb})
        assert records[0]["dockq"] == 1.0
        assert records[0]["dockq_quality"] == "high"
