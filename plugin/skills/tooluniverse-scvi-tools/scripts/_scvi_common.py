"""
Shared preflight/honesty-contract helpers for the tooluniverse-scvi-tools scripts.

HONEST DESIGN (matches tooluniverse-single-cell/scripts/scrna_qc.py):
- If scvi-tools/anndata/scanpy are NOT installed, every script prints an
  install plan and exits 0. It never fabricates a model, a latent space,
  or a DE table.
- GPU is used automatically if torch reports CUDA/MPS available; otherwise
  CPU is used with an explicit, printed warning (no silent slowdown).
"""

import sys

INSTALL_CMD = "pip install scvi-tools scanpy anndata"


def preflight(require=("scvi", "anndata", "scanpy", "numpy")):
    """Return (ok, missing_list). Never raises."""
    missing = []
    for mod in require:
        try:
            __import__(mod)
        except Exception:
            missing.append(mod)
    return (len(missing) == 0, missing)


def print_install_plan(missing, extra_note=None):
    print("scvi-tools helper -- environment preflight")
    if not missing:
        print("  scvi-tools/scanpy/anndata/numpy: available")
        if extra_note:
            print(f"  {extra_note}")
        print("Environment OK.")
    else:
        print(f"  MISSING: {', '.join(missing)}")
        print("Install plan (run this, then re-run this script):")
        print(f"  {INSTALL_CMD}")
        print(
            "No analysis was run. This is a preflight only -- no results were "
            "fabricated."
        )


def report_device():
    """Print which device scvi-tools/lightning will actually train on."""
    try:
        import torch

        if torch.cuda.is_available():
            print(f"Device: CUDA ({torch.cuda.get_device_name(0)})")
            return "cuda"
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            print("Device: Apple MPS")
            return "mps"
    except Exception:
        pass
    print(
        "Device: CPU (no GPU detected). Training will be slower -- reduce "
        "--max-epochs for a quick check, or run on a GPU machine / "
        "setup-scvi-remote-tool for a GPU-backed remote."
    )
    return "cpu"


def require_raw_counts(adata, layer="counts"):
    """
    Verify integer counts exist in the given layer (or .X). Raises a clean,
    actionable ValueError rather than letting scvi fail deep inside training
    with a cryptic error, and never silently treats normalized data as counts.
    """
    import numpy as np

    X = adata.layers[layer] if layer in adata.layers else adata.X
    sample = X[:100].toarray() if hasattr(X, "toarray") else np.asarray(X[:100])
    if sample.size == 0:
        return
    non_integer_frac = np.mean(np.abs(sample - np.round(sample)) > 1e-6)
    if non_integer_frac > 0.01:
        raise ValueError(
            f"Data in layer='{layer}' does not look like raw integer counts "
            f"({non_integer_frac:.1%} of sampled values are non-integer). "
            "scvi-tools models require raw counts, not normalized/log data. "
            "Run scripts/prepare_data.py first, or pass --layer counts if "
            "the raw counts are stored under a different layer name."
        )


def exit_clean(missing):
    print_install_plan(missing)
    print("Exiting cleanly (0).")
    sys.exit(0)
