"""
NvidiaNIM_esm2_650m

Generate protein sequence embeddings using ESM2-650M via NVIDIA NIM. 650 million parameter langua...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NvidiaNIM_esm2_650m(
    sequences: list[str],
    format: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Generate protein sequence embeddings using ESM2-650M via NVIDIA NIM. 650 million parameter langua...

    Parameters
    ----------
    sequences : list[str]
        Array of protein sequences (max 1024 amino acids each, valid: ARNDCQEGHILKMFP...
    format : str
        Output format: npz (binary NumPy archive) or json
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
        {
            "name": "NvidiaNIM_esm2_650m",
            "arguments": {"sequences": sequences, "format": format},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NvidiaNIM_esm2_650m"]
