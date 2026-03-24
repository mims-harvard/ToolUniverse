"""
FinnGen_get_variant_finemapping

Get fine-mapping regions associated with a genomic variant in FinnGen. Returns phenotypes where t...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FinnGen_get_variant_finemapping(
    variant: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get fine-mapping regions associated with a genomic variant in FinnGen. Returns phenotypes where t...

    Parameters
    ----------
    variant : str
        Genomic variant in chr:pos:ref:alt format (GRCh38). Examples: '19:44908684:T:...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {"variant": variant}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "FinnGen_get_variant_finemapping",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FinnGen_get_variant_finemapping"]
