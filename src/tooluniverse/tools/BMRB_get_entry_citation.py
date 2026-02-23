"""
BMRB_get_entry_citation

Get the citation/publication information for a BMRB NMR entry in BibTeX format. Returns author li...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BMRB_get_entry_citation(
    entry_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the citation/publication information for a BMRB NMR entry in BibTeX format. Returns author li...

    Parameters
    ----------
    entry_id : str
        BMRB entry ID (e.g., '15000', '4020')
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
        {"name": "BMRB_get_entry_citation", "arguments": {"entry_id": entry_id}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BMRB_get_entry_citation"]
