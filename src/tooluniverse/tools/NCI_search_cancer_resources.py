"""
NCI_search_cancer_resources

Search NCI (National Cancer Institute) Resources for Researchers (R4R) for cancer research tools,...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NCI_search_cancer_resources(
    q: str,
    size: Optional[int] = 20,
    from_: Optional[int] = 0,
    toolTypes: Optional[str] = None,
    researchAreas: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search NCI (National Cancer Institute) Resources for Researchers (R4R) for cancer research tools,...

    Parameters
    ----------
    q : str
        Search query for cancer research resources (e.g., 'breast cancer treatment', ...
    size : int
        Number of results to return (default: 20, max: 50)
    from_ : int
        Offset for pagination (default: 0)
    toolTypes : str
        Filter by tool type key: 'analysis_tools', 'datasets_databases', 'lab_tools',...
    researchAreas : str
        Filter by research area key: 'cancer_treatment', 'cancer_biology', 'cancer_om...
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
            "q": q,
            "size": size,
            "from": from_,
            "toolTypes": toolTypes,
            "researchAreas": researchAreas,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NCI_search_cancer_resources",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NCI_search_cancer_resources"]
