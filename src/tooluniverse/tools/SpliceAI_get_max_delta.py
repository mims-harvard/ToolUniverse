"""
SpliceAI_get_max_delta

Get simplified maximum SpliceAI delta score and pathogenicity interpretation for a variant. Retur...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SpliceAI_get_max_delta(
    variant: str,
    genome: Optional[str] = "38",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get simplified maximum SpliceAI delta score and pathogenicity interpretation for a variant. Retur...

    Parameters
    ----------
    variant : str
        Variant in chr-pos-ref-alt format (e.g., chr8-140300616-T-G)
    genome : str
        Genome build: 37 or 38 (default: 38)
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
        k: v for k, v in {"variant": variant, "genome": genome}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SpliceAI_get_max_delta",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SpliceAI_get_max_delta"]
