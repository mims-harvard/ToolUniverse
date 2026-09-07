import importlib.util
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_source_module(name, relative_path):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RemoteDataPathTests(unittest.TestCase):
    def setUp(self):
        module = _load_source_module(
            "remote_data_path_under_test",
            "src/tooluniverse/remote_data_path.py",
        )
        self.resolve = module.resolve_remote_data_path
        self.load_h5ad = module.load_remote_h5ad
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.dataset = self.root / "counts.h5ad"
        self.dataset.write_bytes(b"synthetic")

    def tearDown(self):
        self.tempdir.cleanup()

    def test_requires_an_explicit_provider_data_root(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "TOOLUNIVERSE_REMOTE_DATA_ROOT"):
                self.resolve("counts.h5ad", allowed_suffixes={".h5ad"})

    def test_accepts_relative_and_absolute_files_inside_root(self):
        with mock.patch.dict(
            os.environ, {"TOOLUNIVERSE_REMOTE_DATA_ROOT": str(self.root)}
        ):
            self.assertEqual(
                self.resolve("counts.h5ad", allowed_suffixes={".h5ad"}),
                self.dataset,
            )
            self.assertEqual(
                self.resolve(str(self.dataset), allowed_suffixes={".h5ad"}),
                self.dataset,
            )

    def test_rejects_urls_traversal_and_symlink_escapes(self):
        with tempfile.TemporaryDirectory() as outside_dir:
            outside = Path(outside_dir) / "outside.h5ad"
            outside.write_bytes(b"private")
            link = self.root / "escape.h5ad"
            link.symlink_to(outside)
            with mock.patch.dict(
                os.environ, {"TOOLUNIVERSE_REMOTE_DATA_ROOT": str(self.root)}
            ):
                for value in (
                    "https://example.test/counts.h5ad",
                    "../outside.h5ad",
                    "escape.h5ad",
                ):
                    with self.subTest(value=value):
                        with self.assertRaises(ValueError):
                            self.resolve(value, allowed_suffixes={".h5ad"})

    def test_rejects_wrong_suffix_missing_file_and_directory(self):
        wrong = self.root / "counts.csv"
        wrong.write_text("not h5ad", encoding="utf-8")
        with mock.patch.dict(
            os.environ, {"TOOLUNIVERSE_REMOTE_DATA_ROOT": str(self.root)}
        ):
            for value in ("counts.csv", "missing.h5ad", "."):
                with self.subTest(value=value):
                        with self.assertRaises(ValueError):
                            self.resolve(value, allowed_suffixes={".h5ad"})

    def test_rejects_oversized_and_nul_containing_file_names(self):
        with mock.patch.dict(
            os.environ, {"TOOLUNIVERSE_REMOTE_DATA_ROOT": str(self.root)}
        ):
            for value in ("a" * 4097 + ".h5ad", "bad\x00name.h5ad"):
                with self.subTest(value=value), self.assertRaisesRegex(
                    ValueError, "invalid"
                ):
                    self.resolve(value, allowed_suffixes={".h5ad"})

    def test_h5ad_loader_rejects_urls_and_redacts_reader_errors(self):
        reader = mock.Mock(
            side_effect=RuntimeError(f"cannot parse private file {self.dataset}")
        )
        with mock.patch.dict(
            os.environ, {"TOOLUNIVERSE_REMOTE_DATA_ROOT": str(self.root)}
        ):
            with self.assertRaisesRegex(ValueError, "URLs are not allowed"):
                self.load_h5ad("https://example.test/counts.h5ad", reader)
            with self.assertRaises(ValueError) as raised:
                self.load_h5ad("counts.h5ad", reader)

        self.assertEqual(reader.call_count, 1)
        self.assertNotIn(str(self.root), str(raised.exception))

    def test_h5ad_loader_enforces_provider_byte_and_shape_limits(self):
        adata = types.SimpleNamespace(n_obs=3, n_vars=4)
        with mock.patch.dict(
            os.environ,
            {
                "TOOLUNIVERSE_REMOTE_DATA_ROOT": str(self.root),
                "TOOLUNIVERSE_REMOTE_MAX_H5AD_BYTES": "8",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(ValueError, "size limit"):
                self.load_h5ad("counts.h5ad", mock.Mock(return_value=adata))

        for environment_name, adata in (
            ("TOOLUNIVERSE_REMOTE_MAX_H5AD_OBS", types.SimpleNamespace(n_obs=3, n_vars=1)),
            ("TOOLUNIVERSE_REMOTE_MAX_H5AD_VARS", types.SimpleNamespace(n_obs=1, n_vars=3)),
        ):
            with self.subTest(environment_name=environment_name), mock.patch.dict(
                os.environ,
                {
                    "TOOLUNIVERSE_REMOTE_DATA_ROOT": str(self.root),
                    environment_name: "2",
                },
                clear=True,
            ):
                with self.assertRaisesRegex(ValueError, "provider n_"):
                    self.load_h5ad("counts.h5ad", mock.Mock(return_value=adata))

    def test_h5ad_loader_rejects_oversized_shape_before_full_read(self):
        close = mock.Mock()
        backed_adata = types.SimpleNamespace(
            n_obs=3,
            n_vars=1,
            file=types.SimpleNamespace(close=close),
        )

        def reader(_path, *, backed=None):
            if backed == "r":
                return backed_adata
            raise AssertionError("oversized H5AD must not be fully materialized")
        with mock.patch.dict(
            os.environ,
            {
                "TOOLUNIVERSE_REMOTE_DATA_ROOT": str(self.root),
                "TOOLUNIVERSE_REMOTE_MAX_H5AD_OBS": "2",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(ValueError, "provider n_obs limit"):
                self.load_h5ad("counts.h5ad", reader)

        close.assert_called_once_with()

    def test_h5ad_loader_rejects_invalid_provider_limits(self):
        for value in ("0", "-1", "not-an-integer"):
            with self.subTest(value=value), mock.patch.dict(
                os.environ,
                {
                    "TOOLUNIVERSE_REMOTE_DATA_ROOT": str(self.root),
                    "TOOLUNIVERSE_REMOTE_MAX_H5AD_BYTES": value,
                },
                clear=True,
            ):
                with self.assertRaisesRegex(ValueError, "positive integer"):
                    self.load_h5ad("counts.h5ad", mock.Mock())


class ScrubletPathBoundaryTests(unittest.TestCase):
    def _load_scrublet(self, fake_scanpy):
        path_module = _load_source_module(
            "tooluniverse.remote_data_path",
            "src/tooluniverse/remote_data_path.py",
        )
        fake_registry = types.ModuleType("tooluniverse.mcp_tool_registry")

        def register_mcp_tool(*_args, **_kwargs):
            return lambda cls: cls

        fake_registry.register_mcp_tool = register_mcp_tool
        fake_registry.start_mcp_server = mock.Mock()
        stubs = {
            "scanpy": fake_scanpy,
            "tooluniverse.mcp_tool_registry": fake_registry,
            "tooluniverse.remote_data_path": path_module,
        }
        with mock.patch.dict(sys.modules, stubs):
            return _load_source_module(
                "scrublet_tool_under_test",
                "src/tooluniverse/remote/scrublet/scrublet_tool.py",
            )

    def test_url_is_rejected_before_scanpy_reads_it(self):
        fake_scanpy = types.ModuleType("scanpy")
        fake_scanpy.read_h5ad = mock.Mock(
            side_effect=AssertionError("scanpy must not receive an untrusted URL")
        )
        try:
            module = self._load_scrublet(fake_scanpy)
            result = module.ScrubletDoubletTool().run(
                {"adata_path": "https://example.test/private.h5ad"}
            )
        finally:
            sys.modules.pop("scrublet_tool_under_test", None)

        self.assertIn("URLs are not allowed", result["error"])
        fake_scanpy.read_h5ad.assert_not_called()

    def test_valid_file_uses_default_rate_and_returns_aligned_results(self):
        class FakeArray:
            def __init__(self, values):
                self.values = values

            def to_numpy(self):
                return self

            def astype(self, kind):
                return FakeArray([kind(value) for value in self.values])

            def sum(self):
                return sum(self.values)

            @property
            def shape(self):
                return (len(self.values),)

            def tolist(self):
                return self.values

        class FakeNames(FakeArray):
            pass

        fake_adata = types.SimpleNamespace(
            obs={
                "doublet_score": FakeArray([0.1, 0.9]),
                "predicted_doublet": FakeArray([False, True]),
            },
            obs_names=FakeNames(["cell-1", "cell-2"]),
            n_obs=2,
            n_vars=2,
        )
        fake_scanpy = types.ModuleType("scanpy")
        fake_scanpy.read_h5ad = mock.Mock(return_value=fake_adata)
        fake_scanpy.pp = types.SimpleNamespace(scrublet=mock.Mock())

        with tempfile.TemporaryDirectory() as tempdir:
            dataset = Path(tempdir) / "counts.h5ad"
            dataset.write_bytes(b"synthetic")
            with mock.patch.dict(
                os.environ, {"TOOLUNIVERSE_REMOTE_DATA_ROOT": tempdir}
            ):
                module = self._load_scrublet(fake_scanpy)
                result = module.ScrubletDoubletTool().run(
                    {"adata_path": "counts.h5ad"}
                )

        self.assertEqual(
            fake_scanpy.read_h5ad.call_args_list,
            [mock.call(dataset, backed="r"), mock.call(dataset)],
        )
        fake_scanpy.pp.scrublet.assert_called_once_with(
            fake_adata, expected_doublet_rate=0.06
        )
        self.assertEqual(result["cell_ids"], ["cell-1", "cell-2"])
        self.assertEqual(result["n_doublets"], 1)
        self.assertEqual(result["doublet_rate"], 0.5)

    def test_read_error_does_not_disclose_provider_path(self):
        fake_scanpy = types.ModuleType("scanpy")
        with tempfile.TemporaryDirectory() as tempdir:
            dataset = Path(tempdir) / "private.h5ad"
            dataset.write_bytes(b"not h5ad")
            fake_scanpy.read_h5ad = mock.Mock(
                side_effect=RuntimeError(f"cannot parse {dataset}")
            )
            with mock.patch.dict(
                os.environ, {"TOOLUNIVERSE_REMOTE_DATA_ROOT": tempdir}
            ):
                module = self._load_scrublet(fake_scanpy)
                result = module.ScrubletDoubletTool().run(
                    {"adata_path": "private.h5ad"}
                )

        self.assertIn("Failed to read", result["error"])
        self.assertNotIn(tempdir, result["error"])

    def test_invalid_expected_doublet_rates_are_actionable(self):
        fake_scanpy = types.ModuleType("scanpy")
        fake_scanpy.read_h5ad = mock.Mock(
            side_effect=AssertionError("invalid rates must fail before file reads")
        )
        try:
            module = self._load_scrublet(fake_scanpy)
            for rate in ("bad", -0.1, 0, 1, 1.1, float("nan"), float("inf")):
                with self.subTest(rate=rate):
                    result = module.ScrubletDoubletTool().run(
                        {"adata_path": "counts.h5ad", "expected_doublet_rate": rate}
                    )
                    self.assertIn("expected_doublet_rate", result["error"])
        finally:
            sys.modules.pop("scrublet_tool_under_test", None)

        fake_scanpy.read_h5ad.assert_not_called()


if __name__ == "__main__":
    unittest.main()
