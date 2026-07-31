"""
HuBMAP_search_samples

Search HuBMAP (Human BioMolecular Atlas Program) biospecimen Samples (the physical tissue layer, ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HuBMAP_search_samples(
    organ: Optional[str] = None,
    sample_category: Optional[str] = None,
    registered_only: Optional[bool] = False,
    limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search HuBMAP (Human BioMolecular Atlas Program) biospecimen Samples (the physical tissue layer, ...

    Parameters
    ----------
    organ : str
        2-letter RUI organ code to filter by (e.g. 'LK' left kidney, 'HT' heart, 'SK'...
    sample_category : str
        Tissue granularity: 'block', 'section', 'organ', or 'suspension'. Case-insens...
    registered_only : bool
        If true, return only spatially-registered samples that carry CCF/RUI coordina...
    limit : int
        Maximum number of results (1-50, default 10).
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
            "organ": organ,
            "sample_category": sample_category,
            "registered_only": registered_only,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "HuBMAP_search_samples",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HuBMAP_search_samples"]
