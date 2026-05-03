"""
GDC_search_cases

Search cancer cohort cases in NCI GDC by project and filters. Use to retrieve case-level metadata...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GDC_search_cases(
    project_id: Optional[str] = None,
    size: Optional[int] = 10,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search cancer cohort cases in NCI GDC by project and filters. Use to retrieve case-level metadata...

    Parameters
    ----------
    project_id : str
        GDC project identifier (e.g., 'TCGA-BRCA').
    size : int
        Number of results (1–100).
    offset : int
        Offset for pagination (0-based).
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
    _args = {
        k: v
        for k, v in {"project_id": project_id, "size": size, "offset": offset}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GDC_search_cases",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GDC_search_cases"]
