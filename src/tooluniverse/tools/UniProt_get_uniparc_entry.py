"""
UniProt_get_uniparc_entry

Get UniParc entry by UniParc ID (UPI). UniParc is a non-redundant archive of all publicly availab...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UniProt_get_uniparc_entry(
    upi: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get UniParc entry by UniParc ID (UPI). UniParc is a non-redundant archive of all publicly availab...

    Parameters
    ----------
    upi : str
        UniParc ID (UPI) in format UPI000002ED67. Find UPI from UniProt entry (extraA...
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
    _args = {k: v for k, v in {"upi": upi}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "UniProt_get_uniparc_entry",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["UniProt_get_uniparc_entry"]
