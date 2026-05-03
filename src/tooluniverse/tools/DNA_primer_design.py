"""
DNA_primer_design

Design forward and reverse PCR primers for a target DNA region using the SantaLucia 1998 nearest-...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DNA_primer_design(
    operation: str,
    sequence: str,
    target_start: Optional[int | Any] = None,
    target_end: Optional[int | Any] = None,
    tm_target: Optional[float | Any] = 60.0,
    product_size_min: Optional[int | Any] = 100,
    product_size_max: Optional[int | Any] = 1000,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Design forward and reverse PCR primers for a target DNA region using the SantaLucia 1998 nearest-...

    Parameters
    ----------
    operation : str
        Operation type
    sequence : str
        DNA template sequence (A, T, G, C, N only). Must be at least 200 bp for good ...
    target_start : int | Any
        0-based start position of the target region to amplify. Defaults to 0.
    target_end : int | Any
        0-based end position of the target region to amplify. Defaults to sequence le...
    tm_target : float | Any
        Target melting temperature in Celsius (default: 60.0°C).
    product_size_min : int | Any
        Minimum acceptable PCR product size in bp (default: 100).
    product_size_max : int | Any
        Maximum acceptable PCR product size in bp (default: 1000).
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
            "operation": operation,
            "sequence": sequence,
            "target_start": target_start,
            "target_end": target_end,
            "tm_target": tm_target,
            "product_size_min": product_size_min,
            "product_size_max": product_size_max,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DNA_primer_design",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DNA_primer_design"]
