"""
OpenTargets_get_publications_by_disease_efoId

Retrieve publications related to a disease efoId, including PubMed IDs and publication dates.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenTargets_get_publications_by_disease_efoId(
    entityId: str,
    additionalIds: Optional[list[str]] = None,
    startYear: Optional[int] = None,
    startMonth: Optional[int] = None,
    endYear: Optional[int] = None,
    endMonth: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Retrieve publications related to a disease efoId, including PubMed IDs and publication dates.

    Parameters
    ----------
    entityId : str
        The ID of the entity (efoId).
    additionalIds : list[str]
        List of additional IDs to include in the search.
    startYear : int
        Year at the lower end of the filter.
    startMonth : int
        Month at the lower end of the filter.
    endYear : int
        Year at the higher end of the filter.
    endMonth : int
        Month at the higher end of the filter.
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
            "entityId": entityId,
            "additionalIds": additionalIds,
            "startYear": startYear,
            "startMonth": startMonth,
            "endYear": endYear,
            "endMonth": endMonth,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenTargets_get_publications_by_disease_efoId",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenTargets_get_publications_by_disease_efoId"]
