"""
SGD_get_protein_domains

Get mapped protein domains for a budding-yeast (Saccharomyces cerevisiae) gene from the Saccharom...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SGD_get_protein_domains(
    locus: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get mapped protein domains for a budding-yeast (Saccharomyces cerevisiae) gene from the Saccharom...

    Parameters
    ----------
    locus : str
        Yeast gene identifier: standard gene name (e.g. 'ACT1'), systematic/ORF name ...
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
    _args = {k: v for k, v in {"locus": locus}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "SGD_get_protein_domains",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SGD_get_protein_domains"]
