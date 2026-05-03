"""
GDC_list_projects

List GDC projects (TCGA, TARGET, etc.) with case/file counts. Use to discover available cancer co...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GDC_list_projects(
    program: Optional[str] = None,
    size: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    List GDC projects (TCGA, TARGET, etc.) with case/file counts. Use to discover available cancer co...

    Parameters
    ----------
    program : str
        Filter by program name (e.g., 'TCGA', 'TARGET')
    size : int
        Number of results (1–100)
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
        k: v for k, v in {"program": program, "size": size}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GDC_list_projects",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GDC_list_projects"]
