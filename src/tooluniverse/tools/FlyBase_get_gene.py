"""
FlyBase_get_gene

Get detailed Drosophila melanogaster (fruit fly) gene information from FlyBase via the Alliance o...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FlyBase_get_gene(
    gene_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed Drosophila melanogaster (fruit fly) gene information from FlyBase via the Alliance o...

    Parameters
    ----------
    gene_id : str
        FlyBase gene ID with 'FB:' prefix. Examples: 'FB:FBgn0003996' (white/w), 'FB:...
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
    _args = {k: v for k, v in {"gene_id": gene_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "FlyBase_get_gene",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FlyBase_get_gene"]
