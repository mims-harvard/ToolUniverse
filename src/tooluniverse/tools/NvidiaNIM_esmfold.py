"""
NvidiaNIM_esmfold

Fast alignment-free protein structure prediction using ESMFold via NVIDIA NIM. No MSA required - ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NvidiaNIM_esmfold(
    sequence: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Fast alignment-free protein structure prediction using ESMFold via NVIDIA NIM. No MSA required - ...

    Parameters
    ----------
    sequence : str
        Amino acid sequence (max 1024 chars, valid: ARNDCQEGHILKMFPSTWYVXBOU)
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

    return get_shared_client().run_one_function(
        {"name": "NvidiaNIM_esmfold", "arguments": {"sequence": sequence}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NvidiaNIM_esmfold"]
