"""
CPIC_get_recommendations

Get drug dosing recommendations from a CPIC pharmacogenomic guideline. Returns clinically actiona...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CPIC_get_recommendations(
    guideline_id: Optional[int] = None,
    drug: Optional[str] = None,
    drug_name: Optional[str] = None,
    limit: Optional[int | Any] = None,
    offset: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get drug dosing recommendations from a CPIC pharmacogenomic guideline. Returns clinically actiona...

    Parameters
    ----------
    guideline_id : int
        CPIC guideline numeric ID. Alternative to drug/drug_name. Use CPIC_list_guide...
    drug : str
        Drug name to auto-resolve guideline_id (e.g., 'codeine', 'abacavir', 'tamoxif...
    drug_name : str
        Alias for drug.
    limit : int | Any
        Maximum number of recommendations to return (default 50)
    offset : int | Any
        Number of recommendations to skip for pagination (default 0)
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
    _args = {
        k: v
        for k, v in {
            "guideline_id": guideline_id,
            "drug": drug,
            "drug_name": drug_name,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CPIC_get_recommendations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CPIC_get_recommendations"]
