"""
ZFIN_get_gene_expression

Get expression annotations for a zebrafish gene from the Alliance of Genome Resources. Returns pe...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ZFIN_get_gene_expression(
    gene_id: str,
    limit: Optional[int] = 50,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get expression annotations for a zebrafish gene from the Alliance of Genome Resources. Returns pe...

    Parameters
    ----------
    gene_id : str
        ZFIN gene ID, with or without the 'ZFIN:' prefix. Examples: 'ZFIN:ZDB-GENE-99...
    limit : int
        Max annotations to return (default 50, max 100).
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
        k: v for k, v in {"gene_id": gene_id, "limit": limit}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ZFIN_get_gene_expression",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ZFIN_get_gene_expression"]
