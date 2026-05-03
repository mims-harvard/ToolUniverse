"""
cBioPortal_get_gene_info

Get detailed information about a specific gene by Entrez Gene ID. Returns gene symbol, aliases, t...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def cBioPortal_get_gene_info(
    entrez_gene_id: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information about a specific gene by Entrez Gene ID. Returns gene symbol, aliases, t...

    Parameters
    ----------
    entrez_gene_id : int
        Entrez Gene ID (e.g., 672 for BRCA1)
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
        k: v for k, v in {"entrez_gene_id": entrez_gene_id}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "cBioPortal_get_gene_info",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["cBioPortal_get_gene_info"]
