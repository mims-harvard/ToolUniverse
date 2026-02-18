"""
EBIProteins_get_interactions

Get protein-protein interaction partners for a protein from the EBI Proteins API (sourced from In...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EBIProteins_get_interactions(
    accession: str,
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
        {"name": "EBIProteins_get_interactions", "arguments": {"accession": accession}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EBIProteins_get_interactions"]
