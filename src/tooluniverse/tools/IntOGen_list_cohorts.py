"""
IntOGen_list_cohorts

List available cancer cohorts from IntOGen with sample counts and tumor types. Returns cohort IDs...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IntOGen_list_cohorts(
    cancer_type: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    List available cancer cohorts from IntOGen with sample counts and tumor types. Returns cohort IDs...

    Parameters
    ----------
    cancer_type : str | Any
        Optional cancer type code to filter cohorts. If omitted, returns all 271 coho...
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

    return get_shared_client().run_one_function(
        {"name": "IntOGen_list_cohorts", "arguments": {"cancer_type": cancer_type}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["IntOGen_list_cohorts"]
