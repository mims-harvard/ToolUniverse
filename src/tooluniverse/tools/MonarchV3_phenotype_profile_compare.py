"""
MonarchV3_phenotype_profile_compare

Compare two explicit phenotype profiles (HPO term sets) pairwise using Monarch Initiative semanti...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MonarchV3_phenotype_profile_compare(
    subjects: list[str],
    objects: list[str],
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Compare two explicit phenotype profiles (HPO term sets) pairwise using Monarch Initiative semanti...

    Parameters
    ----------
    subjects : list[str]
        Subject phenotype profile: list of HPO term CURIEs (e.g., ['HP:0001250', 'HP:...
    objects : list[str]
        Object phenotype profile to compare against: list of HPO term CURIEs (e.g., [...
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
        for k, v in {"subjects": subjects, "objects": objects}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MonarchV3_phenotype_profile_compare",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MonarchV3_phenotype_profile_compare"]
