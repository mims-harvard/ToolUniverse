"""
ADA_list_standards_sections

List all sections/chapters of the current ADA Standards of Medical Care in Diabetes. The ADA publ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ADA_list_standards_sections(
    year: Optional[int] = 2026,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List all sections/chapters of the current ADA Standards of Medical Care in Diabetes. The ADA publ...

    Parameters
    ----------
    year : int
        Year of the ADA Standards of Care edition to retrieve (default: 2026). Standa...
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
        {"name": "ADA_list_standards_sections", "arguments": {"year": year}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ADA_list_standards_sections"]
