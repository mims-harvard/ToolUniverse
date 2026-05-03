"""
OpenTargets_get_drug_adverse_events_by_chemblId

Retrieve significant adverse events reported for a specific drug chemblId.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenTargets_get_drug_adverse_events_by_chemblId(
    chemblId: str,
    page: Optional[dict[str, Any]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Retrieve significant adverse events reported for a specific drug chemblId.

    Parameters
    ----------
    chemblId : str
        The ChEMBL ID of the drug.
    page : dict[str, Any]
        Pagination settings.
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
        k: v for k, v in {"chemblId": chemblId, "page": page}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenTargets_get_drug_adverse_events_by_chemblId",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenTargets_get_drug_adverse_events_by_chemblId"]
