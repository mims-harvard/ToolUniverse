"""
Alliance_get_gene

Get detailed gene information from the Alliance of Genome Resources, including species, synopsis,...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Alliance_get_gene(
    gene_id: str,
    xref_offset: Optional[int] = 0,
    xref_limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed gene information from the Alliance of Genome Resources, including species, synopsis,...

    Parameters
    ----------
    gene_id : str
        Alliance gene ID with source prefix. Examples: 'HGNC:6081' (human INS), 'MGI:...
    xref_offset : int
        Zero-based cross-reference offset.
    xref_limit : int
        Cross-references returned per page (default 10, maximum 500).
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
            "xref_offset": xref_offset,
            "xref_limit": xref_limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Alliance_get_gene",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Alliance_get_gene"]
