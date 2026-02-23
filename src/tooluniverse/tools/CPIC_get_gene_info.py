"""
CPIC_get_gene_info

Get pharmacogenomics information for a gene from the Clinical Pharmacogenomics Implementation Con...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CPIC_get_gene_info(
    symbol: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get pharmacogenomics information for a gene from the Clinical Pharmacogenomics Implementation Con...

    Parameters
    ----------
    symbol : str
        Gene symbol (e.g., 'CYP2D6', 'CYP2C19', 'SLCO1B1', 'TPMT', 'DPYD')
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
        {"name": "CPIC_get_gene_info", "arguments": {"symbol": symbol}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CPIC_get_gene_info"]
