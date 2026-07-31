"""
ReactomeAnalysis_expression_analysis

Quantitative EXPRESSION analysis: map fold-change or numeric expression values onto Reactome path...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ReactomeAnalysis_expression_analysis(
    identifiers: str,
    page_size: Optional[int] = None,
    include_disease: Optional[bool] = None,
    projection: Optional[bool] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Quantitative EXPRESSION analysis: map fold-change or numeric expression values onto Reactome path...

    Parameters
    ----------
    identifiers : str
        Tab-delimited expression rows, one identifier per line as 'GENE<TAB>VALUE'. N...
    page_size : int
        Number of pathways to return (default 20, max 50).
    include_disease : bool
        Include disease pathways in results (default true).
    projection : bool
        Project identifiers to human pathways via orthology (default false; set true ...
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
            "identifiers": identifiers,
            "page_size": page_size,
            "include_disease": include_disease,
            "projection": projection,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ReactomeAnalysis_expression_analysis",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ReactomeAnalysis_expression_analysis"]
