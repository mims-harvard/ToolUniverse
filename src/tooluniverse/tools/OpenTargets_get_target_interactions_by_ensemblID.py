"""
OpenTargets_get_target_interactions_by_ensemblID

Retrieve interaction data for a specific target ensemblID, including interaction partners and evi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenTargets_get_target_interactions_by_ensemblID(
    ensemblId: str,
    page: Optional[dict[str, Any]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Retrieve interaction data for a specific target ensemblID, including interaction partners and evi...

    Parameters
    ----------
    ensemblId : str
        The Ensembl ID of the target.
    page : dict[str, Any]
        Pagination parameters.
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
        k: v for k, v in {"ensemblId": ensemblId, "page": page}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenTargets_get_target_interactions_by_ensemblID",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenTargets_get_target_interactions_by_ensemblID"]
