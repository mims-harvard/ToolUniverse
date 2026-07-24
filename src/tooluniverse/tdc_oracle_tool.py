"""TDC Oracle tool — local ML property/bioactivity scoring via PyTDC.

Wraps Therapeutics Data Commons (TDC) pretrained ``Oracle`` scorers. Given a
SMILES string (or list of SMILES) and an oracle name, returns molecular
property / drug-likeness / bioactivity scores computed locally.

This is distinct from the existing RDKit/ADMET tools: TDC oracles include
ML-trained bioactivity classifiers (GSK3B, JNK3, DRD2) and the standard
medicinal-chemistry scorers (QED, SA, LogP) used as goal-directed molecular
optimization objectives.

Notes
-----
- ``QED`` and ``LogP`` are pure RDKit and run fully offline/instantly.
- ``SA`` downloads a tiny fragment-score table on first use, then runs locally.
- ML bioactivity oracles (``GSK3B``, ``JNK3``, ``DRD2``) download a pretrained
  model file (a few MB) on first use, then score locally.

PyTDC (1.1.x) ships a legacy ``from rdkit.six import iteritems`` import that
fails on modern RDKit (``rdkit.six`` was removed). That import sits behind a
bare ``except`` that re-raises a misleading "install rdkit" error, even though
the actual QED/SA/LogP scoring functions never touch it. We install a tiny
``rdkit.six`` shim before importing tdc so the real oracles work on current
RDKit. The shim is a no-op for environments where ``rdkit.six`` already exists.
"""

from .base_tool import BaseTool
from .tool_registry import register_tool


def _install_rdkit_six_shim():
    """Provide a minimal ``rdkit.six`` so PyTDC's legacy import succeeds.

    ``rdkit.six`` was removed from modern RDKit. PyTDC still imports
    ``iteritems`` from it inside a try/except that masks the real error.
    Only the symbol PyTDC references (``iteritems``) is provided.
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
# a clean error rather than an exception. Mirrors the framework's optional-dep
# pattern (try/except ImportError -> AVAILABLE flag).
TDC_AVAILABLE = False
_IMPORT_ERROR = None
try:
    _install_rdkit_six_shim()
    from tdc import Oracle as _TDCOracle  # noqa: E402

    TDC_AVAILABLE = True
except Exception as exc:  # ImportError or downstream rdkit-guard ImportError
    _TDCOracle = None
    _IMPORT_ERROR = str(exc)


# Oracles that are fast and either fully offline or download only a tiny table.
_FAST_ORACLES = {"QED", "SA", "LOGP"}

# Curated list of supported oracle names with one-line descriptions. TDC also
# supports many more; these are the stable, single-SMILES scorers most useful
# for property prediction and goal-directed optimization.
_SUPPORTED_ORACLES = {
    "QED": "Quantitative Estimate of Drug-likeness (0-1, higher = more drug-like). RDKit, offline.",
    "SA": "Synthetic Accessibility score (1=easy to 10=hard to synthesize). Downloads a small table once.",
    "LogP": "Octanol-water partition coefficient (lipophilicity). RDKit, offline.",
    "GSK3B": "ML bioactivity oracle: probability of GSK3-beta inhibition (0-1). Downloads model once.",
    "JNK3": "ML bioactivity oracle: probability of JNK3 inhibition (0-1). Downloads model once.",
    "DRD2": "ML bioactivity oracle: probability of DRD2 activity (0-1). Downloads model once.",
}


@register_tool("TDCOracleTool")
class TDCOracleTool(BaseTool):
    """Score SMILES with a Therapeutics Data Commons pretrained oracle.

    Parameters (in ``arguments``)
    -----------------------------
    smiles : str | list[str]
        A single SMILES string or a list of SMILES strings to score.
    oracle : str
        Oracle name. One of: QED, SA, LogP, GSK3B, JNK3, DRD2
        (case-insensitive for the canonical names above).
    """

    # Oracle instances are expensive to construct (ML oracles load a model);
    # cache them per-class so repeated calls in a session reuse the loaded model.
    _oracle_cache: dict = {}

    @classmethod
    def _resolve_oracle_name(cls, oracle):
        """Map a user-provided oracle string to its canonical TDC name."""
        if not isinstance(oracle, str):
            return None
        key = oracle.strip()
        # Case-insensitive match against the supported set, preserving TDC's
        # expected casing (e.g. "logp" -> "LogP").
        lowered = key.lower()
        for canonical in _SUPPORTED_ORACLES:
            if canonical.lower() == lowered:
                return canonical
        return key  # pass through; TDC may still recognize it

    @classmethod
    def _get_oracle(cls, name):
        """Return a cached or newly constructed TDC Oracle for ``name``."""
        if name not in cls._oracle_cache:
            cls._oracle_cache[name] = _TDCOracle(name=name)
        return cls._oracle_cache[name]

    def run(self, arguments=None):
        arguments = arguments or {}

        if not TDC_AVAILABLE:
            return {
                "status": "error",
                "error": (
                    "PyTDC is not available. Install it with 'pip install PyTDC' "
                    "(requires rdkit). Underlying import error: "
                    f"{_IMPORT_ERROR}"
                ),
            }

        smiles = arguments.get("smiles")
        oracle_arg = arguments.get("oracle")

        if smiles is None or (isinstance(smiles, (list, str)) and len(smiles) == 0):
            return {
                "status": "error",
                "error": "Parameter 'smiles' is required and cannot be empty.",
            }
        if not oracle_arg:
            return {
                "status": "error",
                "error": (
                    "Parameter 'oracle' is required. Supported oracles: "
                    + ", ".join(_SUPPORTED_ORACLES.keys())
                ),
            }

        oracle_name = self._resolve_oracle_name(oracle_arg)

        # Normalize input to a list for uniform handling, remembering whether the
        # caller passed a single string so we can return a scalar in that case.
        single_input = isinstance(smiles, str)
        smiles_list = [smiles] if single_input else list(smiles)

        if not all(isinstance(s, str) and s.strip() for s in smiles_list):
            return {
                "status": "error",
                "error": "All SMILES entries must be non-empty strings.",
            }

        try:
            oracle = self._get_oracle(oracle_name)
        except Exception as exc:
            return {
                "status": "error",
                "error": (
                    f"Could not load oracle '{oracle_name}': {exc}. "
                    "Supported oracles: " + ", ".join(_SUPPORTED_ORACLES.keys())
                ),
            }

        results = []
        for smi in smiles_list:
            try:
                score = oracle(smi)
                # TDC may return numpy float types; coerce to native float.
                score_val = float(score) if score is not None else None
                results.append({"smiles": smi, "score": score_val, "error": None})
            except Exception as exc:
                results.append({"smiles": smi, "score": None, "error": str(exc)})

        data = {
            "oracle": oracle_name,
            "oracle_description": _SUPPORTED_ORACLES.get(oracle_name),
            "results": results,
        }
        return {"status": "success", "data": data}
