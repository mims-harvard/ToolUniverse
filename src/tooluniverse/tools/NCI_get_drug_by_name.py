"""
NCI_get_drug_by_name

Get detailed information about a cancer drug from the NCI Drug Dictionary by its pretty-url-name ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NCI_get_drug_by_name(
    drug_name: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed information about a cancer drug from the NCI Drug Dictionary by its pretty-url-name ...

    Parameters
    ----------
    drug_name : str
        Pretty URL name (slug) of the drug (e.g., 'pembrolizumab', 'tamoxifen-citrate...
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
    _args = {k: v for k, v in {"drug_name": drug_name}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "NCI_get_drug_by_name",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NCI_get_drug_by_name"]
