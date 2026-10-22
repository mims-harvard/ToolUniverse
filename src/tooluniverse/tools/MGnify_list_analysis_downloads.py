"""
MGnify_list_analysis_downloads

List a page of downloadable result files produced by a MGnify analysis, including file id, label/...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MGnify_list_analysis_downloads(
    analysis_id: str,
    page: Optional[int] = 1,
    page_size: Optional[int] = 100,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List a page of downloadable result files produced by a MGnify analysis, including file id, label/...

    Parameters
    ----------
    analysis_id : str
        MGnify analysis accession (e.g., 'MGYA00585482'). Find IDs via MGnify_list_an...
    page : int
        One-based result page. Continue with metadata.next_page.
    page_size : int
        Number of download entries per page (default 100, range 1-100).
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
            "analysis_id": analysis_id,
            "page": page,
            "page_size": page_size,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MGnify_list_analysis_downloads",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MGnify_list_analysis_downloads"]
