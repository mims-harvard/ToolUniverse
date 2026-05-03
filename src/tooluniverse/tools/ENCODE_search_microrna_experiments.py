"""
ENCODE_search_microrna_experiments

Search ENCODE microRNA-seq experiments. MicroRNA-seq profiles small regulatory RNAs (miRNAs, ~22n...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ENCODE_search_microrna_experiments(
    biosample_term_name: Optional[str | Any] = None,
    organism: Optional[str] = "Homo sapiens",
    limit: Optional[int] = 25,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search ENCODE microRNA-seq experiments. MicroRNA-seq profiles small regulatory RNAs (miRNAs, ~22n...

    Parameters
    ----------
    biosample_term_name : str | Any
        Biosample name filter (e.g., 'K562', 'GM12878', 'liver', 'heart'). Leave empt...
    organism : str
        Organism scientific name (e.g., 'Homo sapiens', 'Mus musculus').
    limit : int
        Maximum number of results to return.
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
            "biosample_term_name": biosample_term_name,
            "organism": organism,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ENCODE_search_microrna_experiments",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ENCODE_search_microrna_experiments"]
