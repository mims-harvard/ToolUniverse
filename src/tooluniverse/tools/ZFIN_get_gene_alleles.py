"""
ZFIN_get_gene_alleles

Get alleles and variants for a zebrafish gene from ZFIN via the Alliance of Genome Resources. Ret...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ZFIN_get_gene_alleles(
    gene_id: str,
    limit: Optional[int] = None,
    page: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get alleles and variants for a zebrafish gene from ZFIN via the Alliance of Genome Resources. Ret...

    Parameters
    ----------
    gene_id : str
        ZFIN gene ID with 'ZFIN:' prefix. Examples: 'ZFIN:ZDB-GENE-990415-8' (pax2a),...
    limit : int
        Maximum number of alleles to return (1-100). Default: 20.
    page : int
        Page number for pagination. Default: 1.
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
            "name": "ZFIN_get_gene_alleles",
            "arguments": {"gene_id": gene_id, "limit": limit, "page": page},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ZFIN_get_gene_alleles"]
