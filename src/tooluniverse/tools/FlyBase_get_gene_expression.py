"""
FlyBase_get_gene_expression

Get expression summary for a Drosophila gene from the Alliance of Genome Resources. Returns a rib...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FlyBase_get_gene_expression(
    gene_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get expression summary for a Drosophila gene from the Alliance of Genome Resources. Returns a rib...

    Parameters
    ----------
    gene_id : str
        FlyBase gene ID with 'FB:' prefix. Examples: 'FB:FBgn0000490' (dpp), 'FB:FBgn...
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
        {"name": "FlyBase_get_gene_expression", "arguments": {"gene_id": gene_id}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FlyBase_get_gene_expression"]
