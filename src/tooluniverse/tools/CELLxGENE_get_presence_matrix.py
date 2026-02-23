"""
CELLxGENE_get_presence_matrix

Get feature presence matrix showing which genes are measured in which datasets. Returns sparse ma...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CELLxGENE_get_presence_matrix(
    operation: str,
    organism: Optional[str] = "Homo sapiens",
    census_version: Optional[str] = "stable",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get feature presence matrix showing which genes are measured in which datasets. Returns sparse ma...

    Parameters
    ----------
    operation : str
        Operation type
    organism : str
        Organism name
    census_version : str
        Census version to query. 'stable' (recommended, Long-Term Support release), '...
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
            "name": "CELLxGENE_get_presence_matrix",
            "arguments": {
                "operation": operation,
                "organism": organism,
                "census_version": census_version,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CELLxGENE_get_presence_matrix"]
