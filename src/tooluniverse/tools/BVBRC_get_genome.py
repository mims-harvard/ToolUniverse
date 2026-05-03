"""
BVBRC_get_genome

Get detailed genome information from BV-BRC (Bacterial and Viral Bioinformatics Resource Center, ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BVBRC_get_genome(
    genome_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed genome information from BV-BRC (Bacterial and Viral Bioinformatics Resource Center, ...

    Parameters
    ----------
    genome_id : str
        BV-BRC genome identifier (taxon_id.version format). Examples: '83332.12' (M. ...
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
    _args = {k: v for k, v in {"genome_id": genome_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "BVBRC_get_genome",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BVBRC_get_genome"]
