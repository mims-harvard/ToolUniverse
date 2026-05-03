"""
HGNC_fetch_gene_by_symbol

Fetch detailed gene information from HGNC (HUGO Gene Nomenclature Committee) by official gene sym...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HGNC_fetch_gene_by_symbol(
    symbol: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Fetch detailed gene information from HGNC (HUGO Gene Nomenclature Committee) by official gene sym...

    Parameters
    ----------
    symbol : str
        Official HGNC gene symbol. Examples: 'TP53', 'BRCA1', 'EGFR', 'INS', 'ACE2'.
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
    _args = {k: v for k, v in {"symbol": symbol}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "HGNC_fetch_gene_by_symbol",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HGNC_fetch_gene_by_symbol"]
