"""
ThreeDBeacons_get_structure_summary

Get a summary of all available 3D structure models for a protein from the 3D Beacons Hub. Aggrega...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ThreeDBeacons_get_structure_summary(
    accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get a summary of all available 3D structure models for a protein from the 3D Beacons Hub. Aggrega...

    Parameters
    ----------
    accession : str
        UniProt protein accession. Examples: 'P04637' (TP53, 327 structures), 'P00533...
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
    _args = {k: v for k, v in {
        "accession": accession
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ThreeDBeacons_get_structure_summary",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["ThreeDBeacons_get_structure_summary"]
