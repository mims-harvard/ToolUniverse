"""
DisProt_get_entry

Get detailed disorder region annotations for a protein from DisProt. Accepts either a DisProt ID ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DisProt_get_entry(
    accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed disorder region annotations for a protein from DisProt. Accepts either a DisProt ID ...

    Parameters
    ----------
    accession : str
        DisProt ID (e.g., 'DP00086') or UniProt accession (e.g., 'P04637'). Both form...
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
        {"name": "DisProt_get_entry", "arguments": {"accession": accession}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DisProt_get_entry"]
