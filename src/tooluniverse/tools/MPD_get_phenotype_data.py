"""
MPD_get_phenotype_data

Get mouse phenotype data from Mouse Phenome Database for specific strains and phenotypes
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MPD_get_phenotype_data(
    strain: str,
    phenotype_category: Optional[str] = "behavior",
    limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get mouse phenotype data from Mouse Phenome Database for specific strains and phenotypes

    Parameters
    ----------
    strain : str
        Mouse strain (e.g., C57BL/6J, BALB/c, DBA/2J)
    phenotype_category : str
        Phenotype category (behavior, physiology, morphology)
    limit : int
        Number of results to return
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
            "strain": strain,
            "phenotype_category": phenotype_category,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MPD_get_phenotype_data",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MPD_get_phenotype_data"]
