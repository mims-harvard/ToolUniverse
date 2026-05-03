"""
PubChem_get_assay_description

Get bioassay description and metadata by AID. Returns assay name, source, protocol, target inform...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PubChem_get_assay_description(
    aid: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get bioassay description and metadata by AID. Returns assay name, source, protocol, target inform...

    Parameters
    ----------
    aid : int
        PubChem BioAssay ID (e.g., 1000, 504526)
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
    _args = {k: v for k, v in {"aid": aid}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "PubChem_get_assay_description",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PubChem_get_assay_description"]
