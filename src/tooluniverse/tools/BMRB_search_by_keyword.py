"""
BMRB_search_by_keyword

Search BMRB (Biological Magnetic Resonance Data Bank) entries by keyword or molecule name. Return...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BMRB_search_by_keyword(
    term: str,
    database: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search BMRB (Biological Magnetic Resonance Data Bank) entries by keyword or molecule name. Return...

    Parameters
    ----------
    term : str
        Search term (protein name, molecule name, or keyword). Examples: 'ubiquitin',...
    database : str | Any
        Database to search: 'macromolecules' (proteins/nucleic acids) or 'metabolomic...
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
        {
            "name": "BMRB_search_by_keyword",
            "arguments": {"term": term, "database": database},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BMRB_search_by_keyword"]
