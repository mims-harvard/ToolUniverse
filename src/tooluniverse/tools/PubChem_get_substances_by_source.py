"""
PubChem_get_substances_by_source

Reverse sourcing: list ALL PubChem substance SIDs deposited/offered by a specific chemical vendor...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PubChem_get_substances_by_source(
    source: Optional[str] = None,
    vendor: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Reverse sourcing: list ALL PubChem substance SIDs deposited/offered by a specific chemical vendor...

    Parameters
    ----------
    source : str
        Exact PubChem substance source / vendor name (case-sensitive), e.g., "Combi-B...
    vendor : str
        Alias for source. The vendor/source name to retrieve SIDs for.
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
        k: v for k, v in {"source": source, "vendor": vendor}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PubChem_get_substances_by_source",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PubChem_get_substances_by_source"]
