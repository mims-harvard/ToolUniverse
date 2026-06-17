"""TDC dataset retrieval tool — load Therapeutics Data Commons benchmark
datasets locally via the PyTDC package.

This is distinct from the existing ``TDC_predict_oracle_score`` tool (which
scores SMILES with pretrained oracles). This tool *loads named TDC benchmark
datasets*: it returns a summary (row count, columns, label distribution,
train/valid/test split sizes) plus a small sample of rows, and can list the
available dataset names for a given TDC problem.

TDC datasets are organized by problem. ``single_pred`` problems
(ADME, Tox, HTS, QM, Yields, Epitope, Develop) each take a ``name``::

    from tdc.single_pred import ADME
    data = ADME(name='Caco2_Wang')
    df = data.get_data()          # a pandas DataFrame
    split = data.get_split()      # {'train','valid','test'} DataFrames

``multi_pred`` problems (DTI, DDI, PPI, GDA, DrugRes, DrugSyn, PeptideMHC,
AntibodyAff, MTI, Catalyst, TCREpitopeBinding, TrialOutcome) follow the same
pattern from ``tdc.multi_pred``.

Notes
-----
- Datasets DOWNLOAD on first use (network). The returned sample is capped
  (default 5 rows, max 20) so responses stay small.
- The problem class is imported lazily per call. Some problem modules pull in
  heavy optional dependencies; if such an import fails in the local
  environment, this tool returns a clean error for that problem instead of
  failing to load. ``single_pred`` problems have minimal dependencies and are
  the most reliable.

PyTDC (1.1.x) ships a legacy ``from rdkit.six import iteritems`` import that
fails on modern RDKit. We install a tiny ``rdkit.six`` shim before importing
tdc so the package imports cleanly on current RDKit.
"""

from .base_tool import BaseTool
from .tool_registry import register_tool


def _install_rdkit_six_shim():
    """Provide a minimal ``rdkit.six`` so PyTDC's legacy import succeeds.

    ``rdkit.six`` was removed from modern RDKit. PyTDC still imports
    ``iteritems`` from it inside a try/except that masks the real error.
    Only the symbols PyTDC references are provided. No-op when ``rdkit.six``
    already exists or when RDKit is absent.
    """
    try:
        import rdkit.six  # noqa: F401  -- already present, nothing to do

        return
    except Exception:
        pass

    try:
        import sys
        import types

        import rdkit  # noqa: F401  -- ensure base package exists first
    except Exception:
        # RDKit itself is missing; let the real import error surface later.
        return

    six_mod = types.ModuleType("rdkit.six")
    six_mod.iteritems = lambda d: iter(d.items())
    six_mod.itervalues = lambda d: iter(d.values())
    six_mod.iterkeys = lambda d: iter(d.keys())
    sys.modules["rdkit.six"] = six_mod
    try:
        rdkit.six = six_mod
    except Exception:
        pass


# Attempt the optional import at module load so missing-dependency handling is
# a clean error rather than an exception. Only the lightweight ``tdc.utils``
# helper is imported here; the per-problem dataset classes are imported lazily
# inside run() so that one heavy/broken problem module does not prevent the
# tool from loading or block the other problems.
TDC_AVAILABLE = False
_IMPORT_ERROR = None
try:
    _install_rdkit_six_shim()
    from tdc.utils import retrieve_dataset_names as _retrieve_dataset_names  # noqa: E402

    TDC_AVAILABLE = True
except Exception as exc:  # ImportError or downstream rdkit-guard ImportError
    _retrieve_dataset_names = None
    _IMPORT_ERROR = str(exc)


# Problem name -> submodule that defines its dataset class. The class name is
# the same as the (canonical) problem key.
_SINGLE_PRED = {
    "ADME": "tdc.single_pred",
    "TOX": "tdc.single_pred",
    "HTS": "tdc.single_pred",
    "QM": "tdc.single_pred",
    "YIELDS": "tdc.single_pred",
    "EPITOPE": "tdc.single_pred",
    "DEVELOP": "tdc.single_pred",
}
_MULTI_PRED = {
    "DTI": "tdc.multi_pred",
    "DDI": "tdc.multi_pred",
    "PPI": "tdc.multi_pred",
    "GDA": "tdc.multi_pred",
    "DRUGRES": "tdc.multi_pred",
    "DRUGSYN": "tdc.multi_pred",
    "PEPTIDEMHC": "tdc.multi_pred",
    "ANTIBODYAFF": "tdc.multi_pred",
    "MTI": "tdc.multi_pred",
    "CATALYST": "tdc.multi_pred",
    "TCREPITOPEBINDING": "tdc.multi_pred",
    "TRIALOUTCOME": "tdc.multi_pred",
}

# Canonical class name for each problem (preserves TDC's expected casing).
_PROBLEM_CANONICAL = {
    "ADME": "ADME",
    "TOX": "Tox",
    "HTS": "HTS",
    "QM": "QM",
    "YIELDS": "Yields",
    "EPITOPE": "Epitope",
    "DEVELOP": "Develop",
    "DTI": "DTI",
    "DDI": "DDI",
    "PPI": "PPI",
    "GDA": "GDA",
    "DRUGRES": "DrugRes",
    "DRUGSYN": "DrugSyn",
    "PEPTIDEMHC": "PeptideMHC",
    "ANTIBODYAFF": "AntibodyAff",
    "MTI": "MTI",
    "CATALYST": "Catalyst",
    "TCREPITOPEBINDING": "TCREpitopeBinding",
    "TRIALOUTCOME": "TrialOutcome",
}

# How many distinct numeric label values still counts as "categorical" (so we
# report a value-count distribution instead of summary statistics).
_MAX_CATEGORICAL_VALUES = 20

# Default / maximum number of sample rows returned in the head() preview.
_DEFAULT_SAMPLE = 5
_MAX_SAMPLE = 20


@register_tool("TDCDatasetTool")
class TDCDatasetTool(BaseTool):
    """Load a Therapeutics Data Commons (TDC) benchmark dataset locally.

    Operations (selected via the ``operation`` argument)
    ----------------------------------------------------
    ``load_dataset`` (default)
        Load the dataset named by ``name`` within ``problem`` and return a
        summary (n_rows, columns, label distribution, split sizes) plus a small
        sample of rows.
    ``list_datasets``
        Return the available dataset names for ``problem``.

    Parameters (in ``arguments``)
    -----------------------------
    problem : str
        TDC problem, e.g. 'ADME', 'Tox', 'HTS', 'QM', 'Yields', 'Epitope',
        'Develop' (single_pred) or 'DTI', 'DDI', 'PPI', 'GDA', etc.
        (multi_pred). Case-insensitive.
    name : str
        Dataset name within the problem, e.g. 'Caco2_Wang' (ADME), 'hERG'
        (Tox). Case-insensitive. Required for ``load_dataset``.
    sample_rows : int, optional
        Number of rows to include in the head sample (default 5, max 20).
    """

    # Loaded dataset objects are cached per (problem, name) so repeated calls in
    # a session reuse the already-downloaded data.
    _dataset_cache: dict = {}

    @staticmethod
    def _problem_key(problem):
        """Normalize a user problem string to its uppercase lookup key."""
        if not isinstance(problem, str):
            return None
        return problem.strip().upper()

    @classmethod
    def _resolve_problem(cls, problem):
        """Return (module_path, class_name) for a problem, or (None, None)."""
        key = cls._problem_key(problem)
        if key is None:
            return None, None
        if key in _SINGLE_PRED:
            return _SINGLE_PRED[key], _PROBLEM_CANONICAL[key]
        if key in _MULTI_PRED:
            return _MULTI_PRED[key], _PROBLEM_CANONICAL[key]
        return None, None

    @classmethod
    def _all_problem_names(cls):
        return list(_PROBLEM_CANONICAL.values())

    def _unknown_problem_error(self, problem):
        """Standard error dict for an unrecognized problem name."""
        return {
            "status": "error",
            "error": (
                f"Unknown problem '{problem}'. Supported problems: "
                + ", ".join(self._all_problem_names())
            ),
        }

    @classmethod
    def _summarize_labels(cls, series):
        """Build a label summary dict for the 'Y' column.

        Numeric labels with few distinct values (classification) are reported
        as a value-count distribution; otherwise (regression) as summary
        statistics. Non-numeric labels report a value-count distribution.
        """
        try:
            n_unique = int(series.nunique(dropna=True))
        except Exception:
            n_unique = None

        is_numeric = False
        try:
            import pandas as pd

            is_numeric = bool(pd.api.types.is_numeric_dtype(series))
        except Exception:
            is_numeric = False

        # Classification-style: few distinct values -> distribution.
        if n_unique is not None and n_unique <= _MAX_CATEGORICAL_VALUES:
            try:
                counts = series.value_counts(dropna=True)
                distribution = {str(idx): int(cnt) for idx, cnt in counts.items()}
                return {
                    "label_type": "categorical",
                    "n_unique": n_unique,
                    "distribution": distribution,
                    "statistics": None,
                }
            except Exception:
                pass

        # Regression-style: numeric with many distinct values -> stats.
        if is_numeric:
            try:
                desc = series.describe().to_dict()
                statistics = {
                    k: (float(v) if v is not None else None) for k, v in desc.items()
                }
                return {
                    "label_type": "continuous",
                    "n_unique": n_unique,
                    "distribution": None,
                    "statistics": statistics,
                }
            except Exception:
                pass

        # Fallback: report distinct count only.
        return {
            "label_type": "other",
            "n_unique": n_unique,
            "distribution": None,
            "statistics": None,
        }

    @classmethod
    def _get_dataset(cls, module_path, class_name, name):
        """Import the problem class lazily and load the named dataset.

        Caches the loaded dataset object per (class_name, name).
        """
        cache_key = (class_name, name)
        if cache_key in cls._dataset_cache:
            return cls._dataset_cache[cache_key]

        module = __import__(module_path, fromlist=[class_name])
        problem_cls = getattr(module, class_name)
        dataset = problem_cls(name=name)
        cls._dataset_cache[cache_key] = dataset
        return dataset

    def _handle_list_datasets(self, problem):
        module_path, class_name = self._resolve_problem(problem)
        if class_name is None:
            return self._unknown_problem_error(problem)
        try:
            names = _retrieve_dataset_names(class_name)
        except Exception as exc:
            return {
                "status": "error",
                "error": f"Could not list datasets for problem '{class_name}': {exc}",
            }
        return {
            "status": "success",
            "data": {
                "problem": class_name,
                "n_datasets": len(names),
                "dataset_names": list(names),
            },
        }

    def _handle_load_dataset(self, problem, name, sample_rows):
        module_path, class_name = self._resolve_problem(problem)
        if class_name is None:
            return self._unknown_problem_error(problem)
        if not name or not isinstance(name, str):
            return {
                "status": "error",
                "error": "Parameter 'name' is required for load_dataset and must be a dataset name string.",
            }

        try:
            dataset = self._get_dataset(module_path, class_name, name)
        except Exception as exc:
            # Try to surface the valid dataset names to help the caller.
            hint = ""
            try:
                valid = _retrieve_dataset_names(class_name)
                hint = " Available dataset names: " + ", ".join(valid)
            except Exception:
                pass
            return {
                "status": "error",
                "error": (
                    f"Could not load dataset '{name}' for problem '{class_name}': {exc}."
                    + hint
                ),
            }

        try:
            df = dataset.get_data()
        except Exception as exc:
            return {
                "status": "error",
                "error": f"Could not retrieve data for '{name}' ({class_name}): {exc}",
            }

        n_rows = int(df.shape[0])
        columns = [str(c) for c in df.columns]

        # Label summary on the standard TDC label column 'Y' when present.
        label_summary = None
        if "Y" in df.columns:
            label_summary = self._summarize_labels(df["Y"])

        # Train/valid/test split sizes (best-effort; some datasets may differ).
        split_sizes = None
        try:
            split = dataset.get_split()
            split_sizes = {str(k): int(v.shape[0]) for k, v in split.items()}
        except Exception:
            split_sizes = None

        # Small head() sample, JSON-safe.
        sample = self._build_sample(df, sample_rows)

        data = {
            "problem": class_name,
            "name": name,
            "n_rows": n_rows,
            "columns": columns,
            "label_summary": label_summary,
            "split_sizes": split_sizes,
            "sample_rows": len(sample),
            "sample": sample,
        }
        return {"status": "success", "data": data}

    @staticmethod
    def _build_sample(df, sample_rows):
        """Return up to ``sample_rows`` head rows as JSON-safe dicts."""
        n = _DEFAULT_SAMPLE
        if isinstance(sample_rows, int):
            n = sample_rows
        n = max(1, min(n, _MAX_SAMPLE))

        head = df.head(n)
        records = []
        for _, row in head.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                record[str(col)] = TDCDatasetTool._jsonable(value)
            records.append(record)
        return records

    @staticmethod
    def _jsonable(value):
        """Coerce a pandas/numpy scalar to a JSON-serializable value."""
        try:
            import pandas as pd

            if pd.isna(value):
                return None
        except Exception:
            pass
        # Numpy / pandas numeric scalars expose .item().
        if hasattr(value, "item"):
            try:
                return value.item()
            except Exception:
                pass
        if isinstance(value, (int, float, bool, str)) or value is None:
            return value
        return str(value)

    def run(self, arguments=None):
        arguments = arguments or {}

        if not TDC_AVAILABLE:
            return {
                "status": "error",
                "error": (
                    "PyTDC is not available. Install it with 'pip install PyTDC' "
                    "(requires rdkit/pandas). Underlying import error: "
                    f"{_IMPORT_ERROR}"
                ),
            }

        operation = arguments.get("operation") or "load_dataset"
        operation = str(operation).strip().lower()
        problem = arguments.get("problem")

        if not problem:
            return {
                "status": "error",
                "error": (
                    "Parameter 'problem' is required. Supported problems: "
                    + ", ".join(self._all_problem_names())
                ),
            }

        if operation == "list_datasets":
            return self._handle_list_datasets(problem)
        if operation == "load_dataset":
            return self._handle_load_dataset(
                problem, arguments.get("name"), arguments.get("sample_rows")
            )
        return {
            "status": "error",
            "error": (
                f"Unknown operation '{operation}'. Supported operations: "
                "load_dataset, list_datasets."
            ),
        }
