"""
NvidiaNIM_openfold2

Predict protein structure from sequence and MSA using OpenFold2 via NVIDIA NIM. PyTorch reimpleme...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NvidiaNIM_openfold2(
    sequence: str,
    alignments: Optional[dict[str, Any]] = None,
    selected_models: Optional[list[Any]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Predict protein structure from sequence and MSA using OpenFold2 via NVIDIA NIM. PyTorch reimpleme...

    Parameters
    ----------
    sequence : str
        Amino acid sequence to predict
    alignments : dict[str, Any]
        MSA alignments by database. Format: {db_name: {a3m: {alignment: str, format: ...
    selected_models : list[Any]
        Model indices to use for prediction (1-5)
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
    if selected_models is None:
        selected_models = [1, 2]
    return get_shared_client().run_one_function(
        {
            "name": "NvidiaNIM_openfold2",
            "arguments": {
                "sequence": sequence,
                "alignments": alignments,
                "selected_models": selected_models,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NvidiaNIM_openfold2"]
