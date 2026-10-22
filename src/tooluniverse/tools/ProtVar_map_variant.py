"""
ProtVar_map_variant

Map a human protein variant to genomic coordinates and retrieve computational variant-effect pred...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ProtVar_map_variant(
    variant: str,
    assembly: Optional[str] = "GRCh38",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Map a human protein variant to genomic coordinates and retrieve computational variant-effect pred...

    Parameters
    ----------
    variant : str
        Variant identifier in one of three formats: (1) 'UniProtAccession SingleLette...
    assembly : str
        Genome assembly used for genomic input and output coordinates.
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
        for k, v in {"variant": variant, "assembly": assembly}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ProtVar_map_variant",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ProtVar_map_variant"]
