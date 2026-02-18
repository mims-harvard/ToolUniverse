"""
EBIProteins_get_interaction_details

Get detailed protein information along with its interaction partners, disease associations, and s...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EBIProteins_get_interaction_details(
    accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed protein information along with its interaction partners, disease associations, and s...

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
        {
            "name": "EBIProteins_get_interaction_details",
            "arguments": {"accession": accession},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EBIProteins_get_interaction_details"]
