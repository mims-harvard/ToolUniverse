import asyncio
import importlib.util
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_source_module(name, relative_path):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _registry_stub():
    registry = types.ModuleType("tooluniverse.mcp_tool_registry")

    def register_mcp_tool(*_args, **_kwargs):
        return lambda decorated: decorated

    registry.register_mcp_tool = register_mcp_tool
    registry.start_mcp_server = mock.Mock()
    registry.collect_tools_for_serve = mock.Mock(return_value=[{"name": "test"}])
    return registry


class Macs3BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.treatment = self.root / "treatment.bam"
        self.treatment.write_bytes(b"synthetic BAM placeholder")

    def tearDown(self):
        sys.modules.pop("macs3_tool_under_test", None)
        self.tempdir.cleanup()

    def _load_macs3(self):
        path_module = _load_source_module(
            "tooluniverse.remote_data_path",
            "src/tooluniverse/remote_data_path.py",
        )
        stubs = {
            "tooluniverse.mcp_tool_registry": _registry_stub(),
            "tooluniverse.remote_data_path": path_module,
        }
        with mock.patch.dict(sys.modules, stubs):
            return _load_source_module(
                "macs3_tool_under_test",
                "src/tooluniverse/remote/macs3/macs3_tool.py",
            )

    def test_rejects_urls_and_files_outside_provider_root(self):
        module = self._load_macs3()
        tool = module.Macs3CallpeakTool()
        with tempfile.TemporaryDirectory() as outside_dir:
            outside = Path(outside_dir) / "outside.bam"
            outside.write_bytes(b"private")
            with mock.patch.dict(
                os.environ, {"TOOLUNIVERSE_REMOTE_DATA_ROOT": str(self.root)}
            ), mock.patch.object(module.subprocess, "run") as run:
                for value in ("https://example.test/reads.bam", str(outside)):
                    with self.subTest(value=value):
                        result = tool.run({"treatment": value})
                        self.assertIn("error", result)
                        self.assertNotIn(outside_dir, result["error"])
                run.assert_not_called()

    def test_rejects_unsafe_or_unbounded_options_before_execution(self):
        module = self._load_macs3()
        invalid_arguments = (
            {"qvalue": float("nan")},
            {"qvalue": 0},
            {"qvalue": 1.1},
            {"top_n": True},
            {"top_n": 0},
            {"top_n": 1001},
            {"nomodel": "false"},
            {"nomodel": True, "extsize": 0},
            {"nomodel": True, "extsize": 1_000_001},
        )
        with mock.patch.dict(
            os.environ, {"TOOLUNIVERSE_REMOTE_DATA_ROOT": str(self.root)}
        ), mock.patch.object(module.subprocess, "run") as run:
            for extra in invalid_arguments:
                with self.subTest(extra=extra):
                    result = module.Macs3CallpeakTool().run(
                        {"treatment": "treatment.bam", **extra}
                    )
                    self.assertIn("error", result)
            run.assert_not_called()

    def test_valid_synthetic_output_is_parsed_without_disclosing_paths(self):
        module = self._load_macs3()

        def fake_run(command, **_kwargs):
            outdir = Path(command[command.index("--outdir") + 1])
            (outdir / "macs3_run_peaks.narrowPeak").write_text(
                "chr1\t10\t30\tpeak-1\t42\t.\t8.5\t6.0\t5.0\t12\n",
                encoding="utf-8",
            )
            return types.SimpleNamespace(returncode=0, stderr="")

        with mock.patch.dict(
            os.environ, {"TOOLUNIVERSE_REMOTE_DATA_ROOT": str(self.root)}
        ), mock.patch.object(module.subprocess, "run", side_effect=fake_run) as run:
            result = module.Macs3CallpeakTool().run(
                {
                    "treatment": "treatment.bam",
                    "format": "BAM",
                    "nomodel": True,
                    "extsize": 147,
                    "top_n": 1,
                }
            )

        self.assertEqual(result["n_peaks"], 1)
        self.assertEqual(result["top_peaks"][0]["chrom"], "chr1")
        command = run.call_args.args[0]
        self.assertIn(str(self.treatment), command)
        self.assertIn("--nomodel", command)
        self.assertIn("147", command)
        self.assertNotIn(str(self.root), repr(result))
        published = json.loads(
            (
                REPO_ROOT
                / "src/tooluniverse/data/remote_tools/macs3_tools.json"
            ).read_text(encoding="utf-8")
        )[0]
        self.assertLessEqual(
            set(result), set(published["return_schema"]["properties"])
        )

    def test_provider_failure_does_not_return_stderr_or_local_paths(self):
        module = self._load_macs3()
        private_detail = f"failed while reading {self.treatment}"
        failed = types.SimpleNamespace(returncode=2, stderr=private_detail)
        with mock.patch.dict(
            os.environ, {"TOOLUNIVERSE_REMOTE_DATA_ROOT": str(self.root)}
        ), mock.patch.object(module.subprocess, "run", return_value=failed):
            result = module.Macs3CallpeakTool().run(
                {"treatment": "treatment.bam", "format": "BAM"}
            )

        self.assertIn("error", result)
        self.assertNotIn(private_detail, result["error"])
        self.assertNotIn(str(self.root), result["error"])

    def test_current_macs3_frag_format_accepts_gzipped_fragment_files(self):
        module = self._load_macs3()
        fragments = self.root / "fragments.tsv.gz"
        fragments.write_bytes(b"synthetic gzipped fragment placeholder")

        def fake_run(command, **_kwargs):
            outdir = Path(command[command.index("--outdir") + 1])
            (outdir / "macs3_run_peaks.narrowPeak").write_text(
                "chr1\t10\t30\tpeak-1\t42\t.\t8.5\t6.0\t5.0\t12\n",
                encoding="utf-8",
            )
            return types.SimpleNamespace(returncode=0, stderr="")

        with mock.patch.dict(
            os.environ, {"TOOLUNIVERSE_REMOTE_DATA_ROOT": str(self.root)}
        ), mock.patch.object(module.subprocess, "run", side_effect=fake_run) as run:
            result = module.Macs3CallpeakTool().run(
                {"treatment": "fragments.tsv.gz", "format": "FRAG"}
            )

        self.assertEqual(result["n_peaks"], 1)
        self.assertIn("FRAG", run.call_args.args[0])

    def test_even_peak_count_uses_the_statistical_median_width(self):
        module = self._load_macs3()
        narrowpeak = self.root / "two-peaks.narrowPeak"
        narrowpeak.write_text(
            "chr1\t10\t30\tp1\t20\t.\t8\t6\t5\t12\n"
            "chr1\t40\t80\tp2\t10\t.\t7\t5\t4\t22\n",
            encoding="utf-8",
        )

        result = module._parse_narrowpeak(str(narrowpeak), top_n=2)

        self.assertEqual(result["summary"]["median_peak_width"], 30)


class ChrombpnetBoundaryTests(unittest.TestCase):
    def tearDown(self):
        sys.modules.pop("chrombpnet_tool_under_test", None)

    def _load_chrombpnet(self):
        argument_module = _load_source_module(
            "tooluniverse.remote_argument_validation",
            "src/tooluniverse/remote_argument_validation.py",
        )
        sequence_module = _load_source_module(
            "tooluniverse.remote_sequence_input",
            "src/tooluniverse/remote_sequence_input.py",
        )
        tensorflow = types.ModuleType("tensorflow")
        tensorflow.keras = types.SimpleNamespace(
            models=types.SimpleNamespace(load_model=mock.Mock())
        )
        numpy = types.ModuleType("numpy")
        numpy.ndarray = object
        stubs = {
            "numpy": numpy,
            "tensorflow": tensorflow,
            "tooluniverse.mcp_tool_registry": _registry_stub(),
            "tooluniverse.remote_argument_validation": argument_module,
            "tooluniverse.remote_sequence_input": sequence_module,
        }
        with mock.patch.dict(sys.modules, stubs):
            module = _load_source_module(
                "chrombpnet_tool_under_test",
                "src/tooluniverse/remote/chrombpnet/chrombpnet_tool.py",
            )
        return module, tensorflow.keras.models.load_model

    def test_model_is_provider_selected_and_uses_safe_keras_loading(self):
        module, load_model = self._load_chrombpnet()
        with mock.patch.dict(os.environ, {}, clear=True):
            result = module.ChrombpnetPredictTool().run(
                {"model_path": "/tmp/caller-selected.h5", "sequence": "ACGT"}
            )
        self.assertIn("error", result)
        load_model.assert_not_called()

        with tempfile.TemporaryDirectory() as tempdir:
            legacy = Path(tempdir) / "legacy.h5"
            legacy.write_bytes(b"legacy")
            with mock.patch.dict(
                os.environ, {"CHROMBPNET_MODEL_PATH": str(legacy)}, clear=True
            ), self.assertRaises(RuntimeError):
                module._get_model()
            load_model.assert_not_called()

            reviewed = Path(tempdir) / "reviewed.keras"
            reviewed.write_bytes(b"reviewed")
            load_model.return_value = object()
            with mock.patch.dict(
                os.environ, {"CHROMBPNET_MODEL_PATH": str(reviewed)}, clear=True
            ):
                self.assertIs(module._get_model(), load_model.return_value)
            load_model.assert_called_once_with(
                str(reviewed), compile=False, safe_mode=True
            )

    def test_invalid_sequences_fail_before_model_loading(self):
        module, load_model = self._load_chrombpnet()
        cases = (
            (module.ChrombpnetPredictTool, {"sequence": "ACGT*"}),
            (
                module.ChrombpnetVariantEffectTool,
                {"ref_sequence": "ACGT", "alt_sequence": "ACG"},
            ),
            (
                module.ChrombpnetPredictTool,
                {"sequence": "A" * (module.MAX_SEQUENCE_LENGTH + 1)},
            ),
        )
        for tool_class, arguments in cases:
            with self.subTest(tool=tool_class.__name__):
                self.assertIn("error", tool_class().run(arguments))
        load_model.assert_not_called()


class LdscBoundaryTests(unittest.TestCase):
    def tearDown(self):
        sys.modules.pop("ldsc_tool_under_test", None)

    def _load_ldsc(self):
        path_module = _load_source_module(
            "tooluniverse.remote_data_path",
            "src/tooluniverse/remote_data_path.py",
        )
        stubs = {
            "tooluniverse.mcp_tool_registry": _registry_stub(),
            "tooluniverse.remote_data_path": path_module,
        }
        with mock.patch.dict(sys.modules, stubs):
            return _load_source_module(
                "ldsc_tool_under_test",
                "src/tooluniverse/remote/ldsc/ldsc_tool.py",
            )

    def test_rejects_unapproved_sumstats_and_reference_paths_before_subprocess(self):
        with tempfile.TemporaryDirectory() as tempdir, tempfile.TemporaryDirectory() as outside_dir:
            root = Path(tempdir)
            data_root = root / "data"
            ref_root = root / "reference"
            engine_root = root / "engine"
            data_root.mkdir()
            ref_root.mkdir()
            engine_root.mkdir()
            (engine_root / "ldsc.py").write_text("# synthetic", encoding="utf-8")
            (ref_root / "eur_w_ld_chr").mkdir()
            (data_root / "trait.sumstats.gz").write_bytes(b"synthetic")
            outside = Path(outside_dir) / "private.sumstats.gz"
            outside.write_bytes(b"private")
            environment = {
                "TOOLUNIVERSE_REMOTE_DATA_ROOT": str(data_root),
                "LDSC_DIR": str(engine_root),
                "LDSC_REF_DIR": str(ref_root),
            }
            with mock.patch.dict(os.environ, environment):
                module = self._load_ldsc()
                with mock.patch.object(
                    module.subprocess,
                    "run",
                    side_effect=AssertionError("subprocess must not receive unsafe paths"),
                ) as run:
                    cases = (
                        (
                            module.LdscHeritabilityTool,
                            {"sumstats_path": "https://example.test/trait.sumstats.gz"},
                        ),
                        (
                            module.LdscHeritabilityTool,
                            {"sumstats_path": str(outside)},
                        ),
                        (
                            module.LdscGeneticCorrelationTool,
                            {
                                "sumstats_path_1": "trait.sumstats.gz",
                                "sumstats_path_2": str(outside),
                            },
                        ),
                        (
                            module.LdscHeritabilityTool,
                            {
                                "sumstats_path": "trait.sumstats.gz",
                                "ref_ld_chr": "../outside-reference",
                            },
                        ),
                    )
                    for tool_class, arguments in cases:
                        with self.subTest(tool=tool_class.__name__, arguments=arguments):
                            result = tool_class().run(arguments)
                            self.assertIn("error", result)
                            self.assertNotIn(outside_dir, result["error"])
                    run.assert_not_called()


class CelltypistBoundaryTests(unittest.TestCase):
    def tearDown(self):
        sys.modules.pop("celltypist_tool_under_test", None)

    def _load_celltypist(self, read_h5ad, annotate):
        path_module = _load_source_module(
            "tooluniverse.remote_data_path",
            "src/tooluniverse/remote_data_path.py",
        )
        scanpy = types.ModuleType("scanpy")
        scanpy.read_h5ad = read_h5ad
        scanpy.pp = types.SimpleNamespace(normalize_total=mock.Mock(), log1p=mock.Mock())
        celltypist = types.ModuleType("celltypist")
        celltypist.annotate = annotate
        models = types.ModuleType("celltypist.models")

        class Model:
            def __init__(self, classifier, scaler, description):
                self.classifier = classifier
                self.scaler = scaler
                self.description = description

        models.Model = Model
        celltypist.models = models
        sklearn = types.ModuleType("sklearn")
        linear_model = types.ModuleType("sklearn.linear_model")
        preprocessing = types.ModuleType("sklearn.preprocessing")

        class LogisticRegression:
            pass

        class StandardScaler:
            def __init__(self, with_mean=True):
                self.with_mean = with_mean

        linear_model.LogisticRegression = LogisticRegression
        preprocessing.StandardScaler = StandardScaler
        sklearn.linear_model = linear_model
        sklearn.preprocessing = preprocessing
        stubs = {
            "celltypist": celltypist,
            "celltypist.models": models,
            "scanpy": scanpy,
            "sklearn": sklearn,
            "sklearn.linear_model": linear_model,
            "sklearn.preprocessing": preprocessing,
            "tooluniverse.mcp_tool_registry": _registry_stub(),
            "tooluniverse.remote_data_path": path_module,
        }
        with mock.patch.dict(sys.modules, stubs):
            return _load_source_module(
                "celltypist_tool_under_test",
                "src/tooluniverse/remote/celltypist/celltypist_tool.py",
            )

    def test_rejects_unapproved_model_names_before_artifact_or_data_loading(self):
        read_h5ad = mock.Mock(return_value=mock.Mock())
        annotate = mock.Mock(
            side_effect=AssertionError("unapproved model must not reach annotation")
        )
        module = self._load_celltypist(read_h5ad, annotate)
        with tempfile.TemporaryDirectory() as data_dir:
            (Path(data_dir) / "counts.h5ad").write_bytes(b"synthetic")
            with mock.patch.dict(
                os.environ, {"TOOLUNIVERSE_REMOTE_DATA_ROOT": data_dir}
            ):
                for model in ("../../private.pkl", "/tmp/private.pkl", "unknown.pkl"):
                    with self.subTest(model=model):
                        result = module.CelltypistAnnotateTool().run(
                            {"adata_path": "counts.h5ad", "model": model}
                        )
                        self.assertIn("error", result)
        read_h5ad.assert_not_called()
        annotate.assert_not_called()

    def test_approved_model_fails_closed_without_provider_safe_artifact(self):
        read_h5ad = mock.Mock(
            side_effect=AssertionError("missing artifact must not read expression data")
        )
        annotate = mock.Mock(
            side_effect=AssertionError("missing artifact must not run annotation")
        )
        module = self._load_celltypist(read_h5ad, annotate)
        with tempfile.TemporaryDirectory() as data_dir:
            (Path(data_dir) / "counts.h5ad").write_bytes(b"synthetic")
            with mock.patch.dict(
                os.environ, {"TOOLUNIVERSE_REMOTE_DATA_ROOT": data_dir}, clear=True
            ):
                result = module.CelltypistAnnotateTool().run(
                    {
                        "adata_path": "counts.h5ad",
                        "model": "Immune_All_Low.pkl",
                    }
                )

        self.assertIn("CELLTYPIST_SAFE_MODEL_DIR", result["error"])
        read_h5ad.assert_not_called()
        annotate.assert_not_called()

    def test_safe_npz_model_runs_and_returns_aligned_labels(self):
        adata = types.SimpleNamespace(n_obs=2, obs_names=["cell-1", "cell-2"])
        read_h5ad = mock.Mock(return_value=adata)
        predicted = pd.DataFrame(
            {"predicted_labels": ["T cell", "B cell"]}, index=adata.obs_names
        )
        annotate = mock.Mock(
            return_value=types.SimpleNamespace(predicted_labels=predicted)
        )
        module = self._load_celltypist(read_h5ad, annotate)
        with tempfile.TemporaryDirectory() as data_dir, tempfile.TemporaryDirectory() as model_dir:
            (Path(data_dir) / "counts.h5ad").write_bytes(b"synthetic")
            np.savez_compressed(
                Path(model_dir) / "Immune_All_Low.npz",
                coef=np.asarray([[1.0, -1.0]]),
                intercept=np.asarray([0.0]),
                classes=np.asarray(["B cell", "T cell"]),
                features=np.asarray(["CD3D", "MS4A1"]),
                scaler_mean=np.asarray([0.0, 0.0]),
                scaler_scale=np.asarray([1.0, 1.0]),
                scaler_var=np.asarray([1.0, 1.0]),
                with_mean=np.asarray([True]),
                source_sha256=np.asarray(["a" * 64]),
            )
            with mock.patch.dict(
                os.environ,
                {
                    "TOOLUNIVERSE_REMOTE_DATA_ROOT": data_dir,
                    "CELLTYPIST_SAFE_MODEL_DIR": model_dir,
                },
                clear=True,
            ):
                result = module.CelltypistAnnotateTool().run(
                    {
                        "adata_path": "counts.h5ad",
                        "model": "Immune_All_Low.pkl",
                        "majority_voting": False,
                    }
                )
        self.assertEqual(result["predicted_labels"], ["T cell", "B cell"])
        self.assertEqual(result["label_counts"], {"T cell": 1, "B cell": 1})
        self.assertEqual(result["artifact_format"], "celltypist-safe-npz-v1")
        annotate.assert_called_once()


class CompassBoundaryTests(unittest.TestCase):
    def tearDown(self):
        sys.modules.pop("compass_tool_under_test", None)

    def _load_compass(self):
        path_module = _load_source_module(
            "tooluniverse.remote_data_path",
            "src/tooluniverse/remote_data_path.py",
        )
        fastmcp = types.ModuleType("fastmcp")

        class FastMCP:
            def __init__(self, *_args, **_kwargs):
                pass

            def tool(self):
                return lambda decorated: decorated

        fastmcp.FastMCP = FastMCP
        security = types.ModuleType("tooluniverse.server_security")
        security.get_fastmcp_token_auth = mock.Mock(return_value=None)
        security.run_fastmcp_server = mock.Mock()
        with mock.patch.dict(
            sys.modules,
            {
                "fastmcp": fastmcp,
                "tooluniverse.remote_data_path": path_module,
                "tooluniverse.server_security": security,
            },
        ):
            return _load_source_module(
                "compass_tool_under_test",
                "src/tooluniverse/remote/immune_compass/compass_tool.py",
            )

    def test_valid_compass_request_runs_through_single_flight_provider_tool(self):
        module = self._load_compass()
        expected = {
            "prediction": {"is_responder": False},
            "context_info": ["complete"],
        }
        provider = mock.Mock()
        provider.predict.return_value = expected
        module._COMPASS_TOOL = provider
        result = asyncio.run(module.run_compass_prediction("sample.tsv", 0.5))
        self.assertEqual(result, expected)
        provider.predict.assert_called_once_with("sample.tsv", 0.5)

    def test_compass_expression_parser_enforces_provider_root_and_layout(self):
        module = self._load_compass()
        tool = object.__new__(module.CompassTool)
        tool.feature_names = np.asarray(["A1BG", "A1CF"])
        tool.num_cancer_types = 33
        with tempfile.TemporaryDirectory() as data_dir, tempfile.TemporaryDirectory() as outside_dir:
            valid = Path(data_dir) / "sample.tsv"
            valid.write_text(
                "Index\tcancer_code\tA1BG\tA1CF\ncase-1\t25\t5.23\t0.02\n",
                encoding="utf-8",
            )
            outside = Path(outside_dir) / "outside.tsv"
            outside.write_text(valid.read_text(encoding="utf-8"), encoding="utf-8")
            with mock.patch.dict(
                os.environ, {"TOOLUNIVERSE_REMOTE_DATA_ROOT": data_dir}, clear=True
            ):
                parsed = tool._load_expression("sample.tsv")
                self.assertEqual(parsed.index.tolist(), ["case-1"])
                with self.assertRaises(ValueError):
                    tool._load_expression(str(outside))


class BoltzBoundaryTests(unittest.TestCase):
    def tearDown(self):
        sys.modules.pop("tooluniverse.boltz_tool_under_test", None)

    def _load_boltz(self):
        base_tool = types.ModuleType("tooluniverse.base_tool")

        class BaseTool:
            def __init__(self, tool_config):
                self.tool_config = tool_config

        base_tool.BaseTool = BaseTool
        tool_registry = types.ModuleType("tooluniverse.tool_registry")
        tool_registry.register_tool = lambda *_args, **_kwargs: (
            lambda decorated: decorated
        )
        with mock.patch.dict(
            sys.modules,
            {
                "tooluniverse.base_tool": base_tool,
                "tooluniverse.tool_registry": tool_registry,
            },
        ):
            return _load_source_module(
                "tooluniverse.boltz_tool_under_test",
                "src/tooluniverse/boltz_tool.py",
            )

    def _tool(self, module):
        with mock.patch.object(module.shutil, "which", return_value="/usr/bin/boltz"):
            return module.Boltz2DockingTool(tool_config={})

    def test_published_sequence_name_reaches_bounded_provider_command(self):
        module = self._load_boltz()
        observed = {}

        def fake_run(command, **_kwargs):
            observed["yaml"] = Path(command[2]).read_text(encoding="utf-8")
            output_dir = Path(command[command.index("--out_dir") + 1])
            prediction_dir = (
                output_dir / "synthetic-run" / "predictions" / "boltz_input"
            )
            prediction_dir.mkdir(parents=True)
            (prediction_dir / "affinity_boltz_input.json").write_text(
                '{"affinity": 0.5}', encoding="utf-8"
            )
            return types.SimpleNamespace(returncode=0)

        with mock.patch.object(module.subprocess, "run", side_effect=fake_run) as run:
            result = self._tool(module).run(
                {
                    "sequence": "ACDEFGHIKLMNPQRSTVWY",
                    "ligands": [{"id": "L1", "smiles": "CCO"}],
                }
            )

        self.assertEqual(result["affinity_prediction"]["affinity"], 0.5)
        self.assertEqual(result["msa_mode"], "server")
        self.assertIn("sequence: ACDEFGHIKLMNPQRSTVWY", observed["yaml"])
        command = run.call_args.args[0]
        self.assertEqual(command[command.index("--num_workers") + 1], "0")
        self.assertIn("--use_msa_server", command)
        run.assert_called_once()

    def test_explicit_single_sequence_mode_does_not_contact_msa_server(self):
        module = self._load_boltz()
        observed = {}

        def fake_run(command, **_kwargs):
            observed["yaml"] = Path(command[2]).read_text(encoding="utf-8")
            observed["command"] = command
            output_dir = Path(command[command.index("--out_dir") + 1])
            prediction_dir = output_dir / "run" / "predictions" / "boltz_input"
            prediction_dir.mkdir(parents=True)
            (prediction_dir / "affinity_boltz_input.json").write_text(
                '{"affinity": 0.25}', encoding="utf-8"
            )
            return types.SimpleNamespace(returncode=0)

        with mock.patch.object(module.subprocess, "run", side_effect=fake_run):
            result = self._tool(module).run(
                {
                    "sequence": "ACD",
                    "ligands": [{"id": "L1", "smiles": "CCO"}],
                    "use_msa_server": False,
                }
            )

        self.assertEqual(result["msa_mode"], "single_sequence")
        self.assertIn("msa: empty", observed["yaml"])
        self.assertNotIn("--use_msa_server", observed["command"])

    def test_missing_affinity_artifact_fails_closed(self):
        module = self._load_boltz()

        def fake_run(command, **_kwargs):
            output_dir = Path(command[command.index("--out_dir") + 1])
            (output_dir / "run" / "predictions" / "boltz_input").mkdir(
                parents=True
            )
            return types.SimpleNamespace(returncode=0)

        with mock.patch.object(module.subprocess, "run", side_effect=fake_run):
            result = self._tool(module).run(
                {
                    "sequence": "ACD",
                    "ligands": [{"id": "L1", "smiles": "CCO"}],
                }
            )

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"], "Boltz did not produce an affinity prediction.")

    def test_invalid_or_resource_amplifying_inputs_do_not_execute(self):
        module = self._load_boltz()
        invalid_arguments = (
            {"sequence": "ACD", "ligands": []},
            {
                "sequence": "ACD*",
                "ligands": [{"id": "L1", "smiles": "CCO"}],
            },
            {
                "sequence": "ACD",
                "ligands": [{"id": "L1", "smiles": "CCO"}],
                "sampling_steps": 2001,
            },
            {
                "sequence": "ACD",
                "ligands": [{"id": "L1", "smiles": "CCO"}],
                "diffusion_samples": True,
            },
            {
                "sequence": "ACD",
                "ligands": [{"id": "L1", "smiles": "CCO"}],
                "step_scale": float("nan"),
            },
            {
                "sequence": "ACD",
                "ligands": [{"id": "L1", "smiles": "CCO"}],
                "use_msa_server": "false",
            },
        )
        with mock.patch.object(module.subprocess, "run") as run:
            for arguments in invalid_arguments:
                with self.subTest(arguments=arguments):
                    result = self._tool(module).run(arguments)
                    self.assertEqual(result["status"], "error")
            run.assert_not_called()

    def test_provider_failure_redacts_subprocess_details(self):
        module = self._load_boltz()
        private_detail = "/provider/private/model failed"
        failure = module.subprocess.CalledProcessError(
            2, ["boltz"], stderr=private_detail
        )
        with mock.patch.object(module.subprocess, "run", side_effect=failure):
            result = self._tool(module).run(
                {
                    "sequence": "ACD",
                    "ligands": [{"id": "L1", "smiles": "CCO"}],
                }
            )
        self.assertEqual(result["status"], "error")
        self.assertNotIn(private_detail, result["error"])

    def test_published_and_provider_boltz_schemas_match(self):
        published = json.loads(
            (
                REPO_ROOT / "src/tooluniverse/data/remote_tools/boltz_tools.json"
            ).read_text(encoding="utf-8")
        )[0]["parameter"]
        provider = json.loads(
            (
                REPO_ROOT
                / "src/tooluniverse/remote/boltz/boltz_client_tools.json"
            ).read_text(encoding="utf-8")
        )[0]["parameter"]
        self.assertEqual(published, provider)
        self.assertEqual(published["required"], ["sequence", "ligands"])

    def test_oversized_provider_outputs_are_not_returned(self):
        module = self._load_boltz()

        def fake_run(command, **_kwargs):
            output_dir = Path(command[command.index("--out_dir") + 1])
            prediction_dir = output_dir / "run" / "predictions" / "boltz_input"
            prediction_dir.mkdir(parents=True)
            (prediction_dir / "boltz_input_model_0.cif").write_text(
                "oversized", encoding="utf-8"
            )
            (prediction_dir / "affinity_boltz_input.json").write_text(
                '{"value": 1}', encoding="utf-8"
            )
            return types.SimpleNamespace(returncode=0)

        with mock.patch.object(module, "_MAX_STRUCTURE_BYTES", 5), mock.patch.object(
            module, "_MAX_AFFINITY_BYTES", 5
        ), mock.patch.object(module.subprocess, "run", side_effect=fake_run):
            result = self._tool(module).run(
                {
                    "sequence": "ACD",
                    "ligands": [{"id": "L1", "smiles": "CCO"}],
                    "return_structure": True,
                }
            )

        self.assertNotIn("predicted_structure", result)
        self.assertNotIn("affinity_prediction", result)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["msa_mode"], "server")

    def test_malformed_affinity_artifact_fails_closed(self):
        module = self._load_boltz()

        def fake_run(command, **_kwargs):
            output_dir = Path(command[command.index("--out_dir") + 1])
            prediction_dir = output_dir / "run" / "predictions" / "boltz_input"
            prediction_dir.mkdir(parents=True)
            (prediction_dir / "affinity_boltz_input.json").write_text(
                '{"value": NaN}', encoding="utf-8"
            )
            return types.SimpleNamespace(returncode=0)

        with mock.patch.object(module.subprocess, "run", side_effect=fake_run):
            result = self._tool(module).run(
                {
                    "sequence": "ACD",
                    "ligands": [{"id": "L1", "smiles": "CCO"}],
                }
            )

        self.assertEqual(result["status"], "error")
        self.assertNotIn("affinity_prediction", result)
        self.assertNotIn("NaN", json.dumps(result))


class UsptoDownloaderBoundaryTests(unittest.TestCase):
    def tearDown(self):
        sys.modules.pop("uspto_downloader_tool_under_test", None)

    def _load_uspto_downloader(self):
        fitz = types.ModuleType("fitz")
        easyocr = types.ModuleType("easyocr")
        docx = types.ModuleType("docx")
        docx.Document = mock.Mock()
        pil = types.ModuleType("PIL")
        pil.Image = mock.Mock()
        base_module = types.ModuleType("tooluniverse.uspto_tool")

        class USPTOOpenDataPortalTool:
            def __init__(self, tool_config):
                self.tool_config = tool_config
                self.headers = {"X-API-KEY": "synthetic"}

            def run(self, _arguments):
                raise AssertionError("metadata lookup must not run")

        base_module.USPTOOpenDataPortalTool = USPTOOpenDataPortalTool
        registry = types.ModuleType("tooluniverse.tool_registry")
        registry.register_tool = lambda *_args, **_kwargs: (
            lambda decorated: decorated
        )
        with mock.patch.dict(
            sys.modules,
            {
                "pymupdf": fitz,
                "easyocr": easyocr,
                "docx": docx,
                "PIL": pil,
                "PIL.Image": pil.Image,
                "tooluniverse.uspto_tool": base_module,
                "tooluniverse.tool_registry": registry,
            },
        ):
            return _load_source_module(
                "uspto_downloader_tool_under_test",
                "src/tooluniverse/remote/uspto_downloader/uspto_downloader_tool.py",
            )

    def test_application_number_is_validated_before_metadata_lookup(self):
        module = self._load_uspto_downloader()
        tool = module.USPTOPatentDocumentDownloader({"document": "ABST"})
        for value in ("", "../admin", "The quick brown fox", "1234567"):
            with self.subTest(value=value):
                result = tool.run({"applicationNumberText": value})
                self.assertIn("error", result)

    def test_unapproved_download_url_is_rejected_before_request(self):
        module = self._load_uspto_downloader()
        with mock.patch.object(module.requests, "get") as get:
            for value in (
                "http://data.uspto.gov/private.docx",
                "https://127.0.0.1/private.docx",
                "https://data.uspto.gov@example.test/private.docx",
            ):
                with self.subTest(value=value):
                    with self.assertRaises(ValueError):
                        module._download_uspto_document(value, {})
            get.assert_not_called()

    def test_download_and_public_text_are_bounded(self):
        module = self._load_uspto_downloader()
        response = mock.Mock()
        response.status_code = 200
        response.headers = {}
        response.iter_content.return_value = [b"abc", b"def"]
        with mock.patch.object(module, "_MAX_DOWNLOAD_BYTES", 5), mock.patch.object(
            module.requests, "get", return_value=response
        ):
            with self.assertRaises(ValueError):
                module._download_uspto_document(
                    "https://data.uspto.gov/document.pdf", {}
                )
        response.close.assert_called()

        tool = module.USPTOPatentDocumentDownloader({"document": "ABST"})
        with mock.patch.object(module, "_MAX_DOCUMENT_CHARS", 5), mock.patch.object(
            tool, "_run_provider", return_value={"result": "abcdefgh"}
        ):
            result = tool.run({"applicationNumberText": "19113417"})
        self.assertEqual(result["result"], "abcde")
        self.assertEqual(result["document_chars"], 5)
        self.assertTrue(result["truncated"])

    def test_docx_expansion_and_pdf_page_counts_are_bounded(self):
        module = self._load_uspto_downloader()
        buffer = module.BytesIO()
        with module.zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("word/document.xml", "x" * 10)
        with mock.patch.object(module, "_MAX_DOCX_UNCOMPRESSED_BYTES", 5):
            with self.assertRaisesRegex(ValueError, "expansion limit"):
                module._validate_docx_archive(buffer.getvalue())

        tool = module.USPTOPatentDocumentDownloader({"document": "ABST"})
        metadata = {
            "data": {
                "documentBag": [
                    {
                        "documentCode": "ABST",
                        "downloadOptionBag": [
                            {
                                "mimeTypeIdentifier": "PDF",
                                "downloadUrl": "https://data.uspto.gov/document.pdf",
                            }
                        ],
                    }
                ]
            }
        }
        pdf = mock.Mock(page_count=module._MAX_PDF_PAGES + 1)
        with mock.patch.object(
            module.USPTOOpenDataPortalTool, "run", return_value=metadata
        ), mock.patch.object(
            module, "_download_uspto_document", return_value=b"pdf"
        ), mock.patch.object(module.fitz, "open", return_value=pdf, create=True):
            with self.assertRaisesRegex(ValueError, "page limit"):
                tool._run_provider({"applicationNumberText": "19113417"})
        pdf.close.assert_called_once()

    def test_missing_pdf_extra_has_an_actionable_error(self):
        module = self._load_uspto_downloader()
        tool = module.USPTOPatentDocumentDownloader({"document": "ABST"})
        metadata = {
            "data": {
                "documentBag": [
                    {
                        "documentCode": "ABST",
                        "downloadOptionBag": [
                            {
                                "mimeTypeIdentifier": "PDF",
                                "downloadUrl": "https://data.uspto.gov/document.pdf",
                            }
                        ],
                    }
                ]
            }
        }
        with mock.patch.object(
            module.USPTOOpenDataPortalTool, "run", return_value=metadata
        ), mock.patch.object(
            module, "_download_uspto_document", return_value=b"pdf"
        ), mock.patch.object(module, "fitz", None):
            result = tool.run({"applicationNumberText": "19113417"})

        self.assertIn("dependency is not installed", result["error"])
        self.assertIn("PyMuPDF", result["hint"])


class StandaloneFastmcpSecurityTests(unittest.TestCase):
    def _load_security(self):
        return _load_source_module(
            "server_security_under_test",
            "src/tooluniverse/server_security.py",
        )

    def test_remote_bind_is_rejected_before_server_run_without_token(self):
        module = self._load_security()
        server = mock.Mock()
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                module.run_fastmcp_server(
                    server, host="0.0.0.0", port=8123, stateless_http=True
                )
        server.run.assert_not_called()

    def test_configured_token_authentication_fails_closed(self):
        module = self._load_security()
        with mock.patch.dict(
            os.environ, {"TOOLUNIVERSE_API_TOKEN": "synthetic"}, clear=True
        ), mock.patch.dict(sys.modules, {"fastmcp": None}):
            with self.assertRaises(RuntimeError):
                module.get_fastmcp_token_auth()


class MofaBoundaryTests(unittest.TestCase):
    def tearDown(self):
        sys.modules.pop("mofa_tool_under_test", None)

    def _load_mofa(self):
        entry_module = types.ModuleType("mofapy2.run.entry_point")
        entry_module.entry_point = mock.Mock()
        numpy = types.ModuleType("numpy")
        numpy.isfinite = lambda value: value == value and abs(value) != float("inf")
        stubs = {
            "numpy": numpy,
            "mofapy2": types.ModuleType("mofapy2"),
            "mofapy2.run": types.ModuleType("mofapy2.run"),
            "mofapy2.run.entry_point": entry_module,
            "tooluniverse.mcp_tool_registry": _registry_stub(),
        }
        with mock.patch.dict(sys.modules, stubs):
            return _load_source_module(
                "mofa_tool_under_test",
                "src/tooluniverse/remote/mofa/mofa_tool.py",
            )

    def test_invalid_or_unbounded_inline_matrices_do_not_start_training(self):
        module = self._load_mofa()
        invalid_arguments = (
            {"views": {"rna": {"g": [1.0, float("nan")]}}},
            {"views": {"rna": {"g": [1.0, True]}}},
            {"views": {"rna": {"g": [1.0, 2.0]}}, "n_iter": True},
            {"views": {"rna": {"g": [1.0, 2.0]}}, "n_iter": 10001},
            {
                "views": {"rna": {"g": [1.0, 2.0]}},
                "samples": ["duplicate", "duplicate"],
            },
        )
        for arguments in invalid_arguments:
            with self.subTest(arguments=arguments):
                result = module.MofaFactorsTool().run(arguments)
                self.assertIn("error", result)
        module.entry_point.assert_not_called()

        with mock.patch.object(module, "MAX_MATRIX_VALUES", 3):
            result = module.MofaFactorsTool().run(
                {"views": {"rna": {"g1": [1.0, 2.0], "g2": [3.0, 4.0]}}}
            )
        self.assertIn("error", result)
        module.entry_point.assert_not_called()


class HumanExpertBoundaryTests(unittest.TestCase):
    def tearDown(self):
        module = sys.modules.pop("human_expert_tools_under_test", None)
        if module is not None:
            module.executor.shutdown(wait=False, cancel_futures=True)

    def _load_expert_tools(self):
        stubs = {"tooluniverse.mcp_tool_registry": _registry_stub()}
        with mock.patch.dict(sys.modules, stubs):
            return _load_source_module(
                "human_expert_tools_under_test",
                "src/tooluniverse/remote/expert_feedback/human_expert_mcp_tools.py",
            )

    def test_consult_rejects_invalid_arguments_before_queueing(self):
        module = self._load_expert_tools()
        module.expert_system = mock.Mock()
        invalid_arguments = (
            {"question": "   "},
            {"question": "Review this", "specialty": ""},
            {"question": "Review this", "specialty": 7},
            {"question": "Review this", "priority": "critical"},
            {"question": "Review this", "context": 7},
            {"question": "Review this", "timeout_minutes": True},
            {"question": "Review this", "timeout_minutes": 0},
            {"question": "Review this", "timeout_minutes": 61},
            {"question": "Review this", "timeout_minutes": "5"},
        )

        for arguments in invalid_arguments:
            with self.subTest(arguments=arguments):
                result = module.ConsultHumanExpertTool().run(arguments)
                self.assertEqual(result["status"], "error")
        module.expert_system.submit_request.assert_not_called()

    def test_consult_accepts_defaults_and_returns_immediate_response(self):
        module = self._load_expert_tools()
        module.expert_system = mock.Mock()
        module.expert_system.get_response.return_value = {
            "response": "Synthetic expert response",
            "expert": "Test Expert",
            "timestamp": "2026-08-11T12:00:00",
        }

        result = module.ConsultHumanExpertTool().run({"question": "Review this"})

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["specialty"], "general")
        self.assertEqual(result["priority"], "normal")
        module.expert_system.get_response.assert_called_once_with(mock.ANY, 300)

    def test_consult_failure_does_not_disclose_internal_exception(self):
        module = self._load_expert_tools()
        module.expert_system = mock.Mock()
        private_detail = "/srv/private/provider/request-store.db"
        module.expert_system.submit_request.side_effect = RuntimeError(private_detail)

        result = module.ConsultHumanExpertTool().run({"question": "Review this"})

        self.assertEqual(result["status"], "error")
        self.assertNotIn(private_detail, result["error"])

    def test_request_lifecycle_operations(self):
        module = self._load_expert_tools()
        module.expert_system = module.HumanExpertSystem(
            expert_name="Test Expert", specialty="Testing"
        )
        module.expert_system.submit_request(
            "abc12345",
            "Synthetic review question",
            {"specialty": "general", "priority": "normal", "context": ""},
        )

        pending = module.ListPendingExpertRequestsTool().run({})
        submitted = module.SubmitExpertResponseTool().run(
            {"request_id": "abc12345", "response": "Synthetic response"}
        )
        response = module.GetExpertResponseTool().run({"request_id": "abc12345"})
        status = module.GetExpertStatusTool().run({})

        self.assertEqual(pending["count"], 1)
        self.assertEqual(submitted["status"], "success")
        self.assertEqual(response["status"], "completed")
        self.assertEqual(response["expert_response"], "Synthetic response")
        self.assertEqual(status["statistics"]["pending_requests"], 0)
        self.assertEqual(status["statistics"]["completed_responses"], 1)
        published_tools = json.loads(
            (
                REPO_ROOT
                / "src/tooluniverse/data/remote_tools/expert_feedback_tools.json"
            ).read_text(encoding="utf-8")
        )
        status_config = next(
            tool for tool in published_tools if tool["name"] == "get_expert_status"
        )
        expert_properties = status_config["return_schema"]["properties"][
            "expert_info"
        ]["properties"]
        self.assertLessEqual(set(status["expert_info"]), set(expert_properties))

    def test_response_operations_reject_empty_identifiers_and_responses(self):
        module = self._load_expert_tools()
        module.expert_system = mock.Mock()

        for request_id in (None, "", "   ", 7):
            with self.subTest(operation="get", request_id=request_id):
                result = module.GetExpertResponseTool().run(
                    {"request_id": request_id}
                )
                self.assertEqual(result["status"], "error")

        for arguments in (
            {"request_id": "", "response": "answer"},
            {"request_id": "abc12345", "response": ""},
            {"request_id": "abc12345", "response": "   "},
        ):
            with self.subTest(operation="submit", arguments=arguments):
                result = module.SubmitExpertResponseTool().run(arguments)
                self.assertEqual(result["status"], "error")
        module.expert_system.submit_response.assert_not_called()

    def test_companion_flask_api_requires_configured_bearer_token(self):
        module = self._load_expert_tools()
        if not module.FLASK_AVAILABLE:
            self.skipTest("Flask is unavailable")

        with mock.patch.dict(
            os.environ, {"TOOLUNIVERSE_API_TOKEN": "synthetic-token"}, clear=True
        ):
            app = module.create_http_api_server()
            client = app.test_client()
            unauthorized = client.get("/health")
            authorized = client.get(
                "/health",
                headers={"Authorization": "Bearer synthetic-token"},
            )

        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(authorized.status_code, 200)

    def test_consultation_text_and_pending_queue_are_bounded(self):
        module = self._load_expert_tools()
        module.expert_system = mock.Mock()
        tool = module.ConsultHumanExpertTool()

        self.assertEqual(
            tool.run({"question": "x" * (module._MAX_QUESTION_CHARS + 1)})[
                "status"
            ],
            "error",
        )
        module.expert_system.submit_request.assert_not_called()

        system = module.HumanExpertSystem()
        system.pending_requests = [{}] * module._MAX_PENDING_REQUESTS
        with self.assertRaises(RuntimeError):
            system.submit_request("abc12345", "question")

    def test_custom_server_port_rebinds_mcp_tools_and_companion_api(self):
        module = self._load_expert_tools()
        with mock.patch.object(module, "start_http_api_server") as start_api, mock.patch.object(
            module, "start_monitoring_thread"
        ), mock.patch.object(module, "start_mcp_server") as start_mcp, mock.patch.object(
            sys, "argv", ["tooluniverse-expert-feedback", "--start-server", "--port", "8123"]
        ):
            module.main()

        module.collect_tools_for_serve.assert_called_once_with(
            8123,
            host="127.0.0.1",
            server_name="Human Expert Consultation Server",
        )
        start_api.assert_called_once_with(8124)
        start_mcp.assert_called_once_with(port=8123)


if __name__ == "__main__":
    unittest.main()
