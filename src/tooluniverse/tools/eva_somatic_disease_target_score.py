"""
eva_somatic_disease_target_score

Extract disease-target association scores from EVA somatic mutations. This includes somatic varia...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def eva_somatic_disease_target_score(
    efoId: str,
    pageSize: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Extract disease-target association scores from EVA somatic mutations. This includes somatic varia...

    Parameters
    ----------
    efoId : str
        The EFO (Experimental Factor Ontology) ID of the disease, e.g., 'EFO_0000339'...
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
        k: v for k, v in {"efoId": efoId, "pageSize": pageSize}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "eva_somatic_disease_target_score",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["eva_somatic_disease_target_score"]
