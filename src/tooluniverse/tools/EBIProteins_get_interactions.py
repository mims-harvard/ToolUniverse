"""
EBIProteins_get_interactions

Get protein-protein interaction partners for a protein from the EBI Proteins API (sourced from In...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EBIProteins_get_interactions(
    accession: str,
    limit: Optional[int] = 50,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get protein-protein interaction partners for a protein from the EBI Proteins API (sourced from In...

    Parameters
    ----------
    accession : str
        UniProt accession of the query protein. Examples: 'P04637' (TP53), 'P00533' (...
    limit : int
        Maximum number of interaction partners to return (default: 50, sorted by expe...
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
        for k, v in {"accession": accession, "limit": limit}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EBIProteins_get_interactions",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EBIProteins_get_interactions"]
