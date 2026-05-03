"""
FlyBase_get_gene_orthologs

Get orthologs of a Drosophila gene across other species from the Alliance of Genome Resources. Re...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FlyBase_get_gene_orthologs(
    gene_id: str,
    limit: Optional[int] = None,
    page: Optional[int] = None,
    stringency: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get orthologs of a Drosophila gene across other species from the Alliance of Genome Resources. Re...

    Parameters
    ----------
    gene_id : str
        FlyBase gene ID with 'FB:' prefix. Examples: 'FB:FBgn0004647' (Notch/N), 'FB:...
    limit : int
        Maximum number of orthologs to return (1-100). Default: 20.
    page : int
        Page number for pagination. Default: 1.
    stringency : str
        Stringency filter for orthology calls: 'stringent' (high confidence) or 'mode...
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
            "gene_id": gene_id,
            "limit": limit,
            "page": page,
            "stringency": stringency,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FlyBase_get_gene_orthologs",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FlyBase_get_gene_orthologs"]
