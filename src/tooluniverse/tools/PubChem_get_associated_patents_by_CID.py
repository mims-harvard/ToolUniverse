"""
PubChem_get_associated_patents_by_CID

Get a list of patents associated with a specific compound CID.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PubChem_get_associated_patents_by_CID(
    cid: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get a list of patents associated with a specific compound CID.

    Parameters
    ----------
    cid : int
        PubChem compound ID to query, e.g., 2244 (Aspirin).
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
    _args = {k: v for k, v in {"cid": cid}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "PubChem_get_associated_patents_by_CID",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PubChem_get_associated_patents_by_CID"]
