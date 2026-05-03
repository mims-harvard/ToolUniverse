"""
ZFIN_get_gene

Get detailed Danio rerio (zebrafish) gene information from ZFIN via the Alliance of Genome Resour...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ZFIN_get_gene(
    gene_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed Danio rerio (zebrafish) gene information from ZFIN via the Alliance of Genome Resour...

    Parameters
    ----------
    gene_id : str
        ZFIN gene ID with 'ZFIN:' prefix. Examples: 'ZFIN:ZDB-GENE-990415-8' (pax2a),...
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
            "name": "ZFIN_get_gene",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ZFIN_get_gene"]
