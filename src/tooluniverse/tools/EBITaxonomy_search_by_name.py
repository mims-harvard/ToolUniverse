"""
EBITaxonomy_search_by_name

Search for organisms by any name (scientific, common, or synonym) in EBI Taxonomy. Unlike scienti...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EBITaxonomy_search_by_name(
    name: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for organisms by any name (scientific, common, or synonym) in EBI Taxonomy. Unlike scienti...

    Parameters
    ----------
    name : str
        Any organism name (common name, scientific name, or synonym). Examples: 'mous...
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
    _args = {k: v for k, v in {"name": name}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "EBITaxonomy_search_by_name",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EBITaxonomy_search_by_name"]
