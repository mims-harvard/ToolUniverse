"""
Rfam_accession_to_id

Convert Rfam accession to family ID/name. Takes RF accession (e.g., RF00360) and returns human-re...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Rfam_accession_to_id(
    operation: str,
    accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Convert Rfam accession to family ID/name. Takes RF accession (e.g., RF00360) and returns human-re...

    Parameters
    ----------
    operation : str
        Operation type
    accession : str
        Required: Rfam accession (e.g., RF00360)
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
        for k, v in {"operation": operation, "accession": accession}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Rfam_accession_to_id",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Rfam_accession_to_id"]
