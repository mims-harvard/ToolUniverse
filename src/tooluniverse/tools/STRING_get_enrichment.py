"""
STRING_get_enrichment

Perform functional enrichment analysis on a set of proteins using the STRING database. Tests whet...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def STRING_get_enrichment(
    identifiers: str,
    species: Optional[int] = 9606,
    background_string_identifiers: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Perform functional enrichment analysis on a set of proteins using the STRING database. Tests whet...

    Parameters
    ----------
    identifiers : str
        Newline-separated list of protein identifiers (gene names or STRING IDs). Exa...
    species : int
        NCBI taxonomy ID (default 9606 for human). Examples: 9606 (human), 10090 (mou...
    background_string_identifiers : str | Any
        Optional newline-separated background gene set. If not provided, the entire g...
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
        for k, v in {
            "identifiers": identifiers,
            "species": species,
            "background_string_identifiers": background_string_identifiers,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "STRING_get_enrichment",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["STRING_get_enrichment"]
