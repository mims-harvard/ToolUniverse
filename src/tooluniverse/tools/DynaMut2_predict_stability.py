"""
DynaMut2_predict_stability

Predict the effect of a single-point amino acid mutation on protein stability and dynamics using ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DynaMut2_predict_stability(
    operation: str,
    pdb_id: str,
    chain: str,
    mutation: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Predict the effect of a single-point amino acid mutation on protein stability and dynamics using ...

    Parameters
    ----------
    operation : str
        Operation type
    pdb_id : str
        4-character PDB accession code from RCSB PDB (e.g., '4HHB' for hemoglobin, '1...
    chain : str
        Chain identifier in the PDB structure (e.g., 'A'). Must be a valid chain in t...
    mutation : str
        Single-point mutation in the format WtPosNew where Wt is the wild-type amino ...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "operation": operation,
            "pdb_id": pdb_id,
            "chain": chain,
            "mutation": mutation,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DynaMut2_predict_stability",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DynaMut2_predict_stability"]
