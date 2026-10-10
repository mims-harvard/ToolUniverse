"""
LiverTox_get_drug

Drug-induced liver injury (hepatotoxicity) profile for one drug, herbal or dietary supplement, or...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def LiverTox_get_drug(
    drug_name: str,
    section: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Drug-induced liver injury (hepatotoxicity) profile for one drug, herbal or dietary supplement, or...

    Parameters
    ----------
    drug_name : str
        Generic (preferred) or brand drug name, e.g. 'nabumetone' or 'Relafen'.
    section : str
        Optional: return only this section in full, e.g. 'Hepatotoxicity' or 'Outcome...
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
        for k, v in {"drug_name": drug_name, "section": section}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "LiverTox_get_drug",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["LiverTox_get_drug"]
