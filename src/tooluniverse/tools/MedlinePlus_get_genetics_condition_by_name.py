"""
MedlinePlus_get_genetics_condition_by_name

Get detailed information from MedlinePlus Genetics corresponding to genetic condition name. Retur...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MedlinePlus_get_genetics_condition_by_name(
    condition: str,
    format: Optional[str] = "json",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information from MedlinePlus Genetics corresponding to genetic condition name. Retur...

    Parameters
    ----------
    condition : str
        URL slug of genetic condition, e.g., "alzheimer-disease", must match MedlineP...
    format : str
        Format parameter for the endpoint (note: API always returns XML regardless of...
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
        for k, v in {"condition": condition, "format": format}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MedlinePlus_get_genetics_condition_by_name",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MedlinePlus_get_genetics_condition_by_name"]
