"""
Rfam_get_family

Get comprehensive RNA family information from Rfam database. Returns family metadata including de...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Rfam_get_family(
    operation: str,
    family_id: str,
    format: Optional[str] = "json",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get comprehensive RNA family information from Rfam database. Returns family metadata including de...

    Parameters
    ----------
    operation : str
        Operation type
    family_id : str
        Required: Rfam accession (e.g., RF00360) or family name (e.g., snoZ107_R87)
    format : str
        Output format
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
        for k, v in {
            "operation": operation,
            "family_id": family_id,
            "format": format,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Rfam_get_family",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Rfam_get_family"]
