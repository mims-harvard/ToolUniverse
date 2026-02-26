"""
IntOGen_get_gene_info

Get driver gene classification for a specific gene across all cancer types from IntOGen. Returns ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IntOGen_get_gene_info(
    gene: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get driver gene classification for a specific gene across all cancer types from IntOGen. Returns ...

    Parameters
    ----------
    gene : str
        Gene symbol (HUGO nomenclature). Examples: 'TP53', 'KRAS', 'PIK3CA', 'BRAF', ...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    return get_shared_client().run_one_function(
        {"name": "IntOGen_get_gene_info", "arguments": {"gene": gene}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["IntOGen_get_gene_info"]
