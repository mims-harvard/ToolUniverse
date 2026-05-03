"""
OpenTargets_get_similar_entities_by_disease_efoId

Retrieve similar entities for a given disease efoId using a model trained with PubMed.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenTargets_get_similar_entities_by_disease_efoId(
    efoId: str,
    threshold: float,
    size: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Retrieve similar entities for a given disease efoId using a model trained with PubMed.

    Parameters
    ----------
    efoId : str
        The EFO ID of the disease.
    threshold : float
        Threshold similarity between 0 and 1. Only results above threshold are returned.
    size : int
        Number of similar entities to fetch.
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
        for k, v in {"efoId": efoId, "threshold": threshold, "size": size}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenTargets_get_similar_entities_by_disease_efoId",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenTargets_get_similar_entities_by_disease_efoId"]
