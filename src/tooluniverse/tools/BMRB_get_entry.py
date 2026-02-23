"""
BMRB_get_entry

Get NMR data entry from the Biological Magnetic Resonance Data Bank (BMRB). Returns the full NMR-...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BMRB_get_entry(
    entry_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get NMR data entry from the Biological Magnetic Resonance Data Bank (BMRB). Returns the full NMR-...

    Parameters
    ----------
    entry_id : str
        BMRB entry ID (e.g., '15000', '4020', '11086')
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
        {"name": "BMRB_get_entry", "arguments": {"entry_id": entry_id}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BMRB_get_entry"]
