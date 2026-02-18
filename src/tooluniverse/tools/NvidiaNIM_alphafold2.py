"""
NvidiaNIM_alphafold2

Predict protein 3D structure from amino acid sequence using DeepMind's AlphaFold2 via NVIDIA NIM....
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NvidiaNIM_alphafold2(
    sequence: str,
    algorithm: Optional[str] = "mmseqs2",
    databases: Optional[list[str]] = None,
    e_value: Optional[float] = 0.0001,
    iterations: Optional[int] = 1,
    relax_prediction: Optional[bool] = False,
    skip_template_search: Optional[bool] = True,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Predict protein 3D structure from amino acid sequence using DeepMind's AlphaFold2 via NVIDIA NIM....

    Parameters
    ----------
    sequence : str
        Amino acid sequence to predict structure for (single letter codes)
    algorithm : str
        MSA search algorithm. mmseqs2 is faster, jackhmmer is more sensitive
    databases : list[str]
        Sequence databases for MSA search: uniref90, mgnify, small_bfd
    e_value : float
        E-value threshold for MSA search
    iterations : int
        Number of search iterations
    relax_prediction : bool
        Whether to perform structure relaxation
    skip_template_search : bool
        Skip template-based prediction
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
        databases = ["small_bfd"]
    return get_shared_client().run_one_function(
        {
            "name": "NvidiaNIM_alphafold2",
            "arguments": {
                "sequence": sequence,
                "algorithm": algorithm,
                "databases": databases,
                "e_value": e_value,
                "iterations": iterations,
                "relax_prediction": relax_prediction,
                "skip_template_search": skip_template_search,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NvidiaNIM_alphafold2"]
