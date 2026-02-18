"""
NvidiaNIM_alphafold2_multimer

Predict multi-chain protein complex structure using AlphaFold2-Multimer via NVIDIA NIM. Input: se...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NvidiaNIM_alphafold2_multimer(
    sequences: list[str],
    databases: Optional[list[str]] = None,
    relax_prediction: Optional[bool] = False,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Predict multi-chain protein complex structure using AlphaFold2-Multimer via NVIDIA NIM. Input: se...

    Parameters
    ----------
    sequences : list[str]
        Array of 1-6 protein sequences (amino acid single letter codes) to predict as...
    databases : list[str]
        Sequence databases for MSA: uniref90, small_bfd
    relax_prediction : bool
        Whether to relax the predicted structure
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
    if databases is None:
        databases = ["uniref90", "small_bfd"]
    return get_shared_client().run_one_function(
        {
            "name": "NvidiaNIM_alphafold2_multimer",
            "arguments": {
                "sequences": sequences,
                "databases": databases,
                "relax_prediction": relax_prediction,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NvidiaNIM_alphafold2_multimer"]
