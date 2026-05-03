"""
NvidiaNIM_openfold3

Predict biomolecular complex structure (proteins, DNA, RNA, ligands) using OpenFold3 via NVIDIA N...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NvidiaNIM_openfold3(
    inputs: list[Any],
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Predict biomolecular complex structure (proteins, DNA, RNA, ligands) using OpenFold3 via NVIDIA N...

    Parameters
    ----------
    inputs : list[Any]
        List of input specifications for structure prediction
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
        {"name": "NvidiaNIM_openfold3", "arguments": {"inputs": inputs}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NvidiaNIM_openfold3"]
