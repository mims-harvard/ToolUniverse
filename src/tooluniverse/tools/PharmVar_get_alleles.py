"""
PharmVar_get_alleles

Get all allele definitions for a pharmacogene from PharmVar (Pharmacogene Variation Consortium). ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PharmVar_get_alleles(
    gene: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get all allele definitions for a pharmacogene from PharmVar (Pharmacogene Variation Consortium). ...

    Parameters
    ----------
    gene : str
        Gene symbol (e.g., 'CYP2D6', 'CYP2C9', 'CYP2C19', 'CYP2B6', 'DPYD', 'SLCO1B1'...
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
        {"name": "PharmVar_get_alleles", "arguments": {"gene": gene}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PharmVar_get_alleles"]
