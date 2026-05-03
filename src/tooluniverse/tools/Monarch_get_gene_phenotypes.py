"""
Monarch_get_gene_phenotypes

Get phenotypes associated with a gene from Monarch Initiative (cross-species). Input is a gene CU...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Monarch_get_gene_phenotypes(
    subject: str,
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get phenotypes associated with a gene from Monarch Initiative (cross-species). Input is a gene CU...

    Parameters
    ----------
    subject : str
        Gene CURIE identifier (e.g., 'HGNC:11998' for TP53, 'HGNC:1100' for BRCA1). U...
    limit : int
        Maximum phenotype associations to return (default: 100)
    offset : int
        Number of initial entries to skip.
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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"subject": subject, "limit": limit, "offset": offset}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Monarch_get_gene_phenotypes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Monarch_get_gene_phenotypes"]
