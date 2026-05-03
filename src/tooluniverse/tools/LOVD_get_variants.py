"""
LOVD_get_variants

Get all curated variants for a gene from LOVD. Returns variant details including HGVS DNA/RNA/pro...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def LOVD_get_variants(
    gene_symbol: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get all curated variants for a gene from LOVD. Returns variant details including HGVS DNA/RNA/pro...

    Parameters
    ----------
    gene_symbol : str
        HGNC gene symbol (e.g., 'TP53', 'BRCA1').
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {"gene_symbol": gene_symbol}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "LOVD_get_variants",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["LOVD_get_variants"]
