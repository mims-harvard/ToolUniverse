"""
disease_target_score

Extract disease-target association scores from a specific data source using GraphQL API. This too...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def disease_target_score(
    efoId: str,
    datasourceId: str,
    pageSize: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Extract disease-target association scores from a specific data source using GraphQL API. This too...

    Parameters
    ----------
    efoId : str
        The EFO (Experimental Factor Ontology) ID of the disease, e.g., 'EFO_0000339'...
    datasourceId : str
        The datasource ID to extract scores from. Available options: 'chembl', 'eva',...
    pageSize : int
        Number of results per page (default: 100, max: 100)
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
            "efoId": efoId,
            "datasourceId": datasourceId,
            "pageSize": pageSize,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "disease_target_score",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["disease_target_score"]
