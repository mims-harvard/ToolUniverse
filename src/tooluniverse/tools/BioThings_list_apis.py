"""
BioThings_list_apis

List the ~50 biomedical APIs reachable through the BioThings gateway, with a one-line description...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BioThings_list_apis(
    keyword: Optional[str] = None,
    only_without_dedicated_tool: Optional[bool] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List the ~50 biomedical APIs reachable through the BioThings gateway, with a one-line description...

    Parameters
    ----------
    keyword : str
        Filter APIs by substring in the slug or description, e.g. 'drug', 'microbiome'.
    only_without_dedicated_tool : bool
        If true, list only APIs that have no dedicated ToolUniverse equivalent.
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
        for k, v in {
            "keyword": keyword,
            "only_without_dedicated_tool": only_without_dedicated_tool,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BioThings_list_apis",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BioThings_list_apis"]
