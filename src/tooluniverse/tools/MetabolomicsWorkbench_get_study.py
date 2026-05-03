"""
MetabolomicsWorkbench_get_study

Get metadata and information about a metabolomics study by its study ID. Returns study summary in...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MetabolomicsWorkbench_get_study(
    study_id: str,
    output_item: Optional[str] = "summary",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get metadata and information about a metabolomics study by its study ID. Returns study summary in...

    Parameters
    ----------
    study_id : str
        Metabolomics Workbench study ID (e.g., 'ST000001', 'ST000100').
    output_item : str
        Type of information to return. Options: 'summary' (study overview), 'factors'...
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
        for k, v in {"study_id": study_id, "output_item": output_item}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MetabolomicsWorkbench_get_study",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MetabolomicsWorkbench_get_study"]
