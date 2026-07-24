"""
ESM_fold_protein

Predict protein 3D structure from sequence using ESM3, returning pTM (predicted TM-score), per-re...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ESM_fold_protein(
    sequence: str,
    model: Optional[str] = "esm3-open-2024-03",
    num_steps: Optional[int] = 8,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Predict protein 3D structure from sequence using ESM3, returning pTM (predicted TM-score), per-re...

    Parameters
    ----------
    sequence : str
        Protein amino acid sequence in single-letter code to fold (e.g. 'MKTAYIAKQRQI...
    model : str
        ESM3 model to use for structure prediction.
    num_steps : int
        Number of iterative structure decoding steps (default: 8). More steps may imp...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Any
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "sequence": sequence,
            "model": model,
            "num_steps": num_steps,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ESM_fold_protein",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ESM_fold_protein"]
