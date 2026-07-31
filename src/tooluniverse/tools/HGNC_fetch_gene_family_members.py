"""
HGNC_fetch_gene_family_members

Enumerate ALL member genes of an HGNC gene family/group by its numeric gene_group_id, returning t...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HGNC_fetch_gene_family_members(
    gene_group_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Enumerate ALL member genes of an HGNC gene family/group by its numeric gene_group_id, returning t...

    Parameters
    ----------
    gene_group_id : str
        Numeric HGNC gene group/family ID. Examples: '366' (Ubiquitin specific peptid...
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
    _args = {k: v for k, v in {"gene_group_id": gene_group_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "HGNC_fetch_gene_family_members",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HGNC_fetch_gene_family_members"]
