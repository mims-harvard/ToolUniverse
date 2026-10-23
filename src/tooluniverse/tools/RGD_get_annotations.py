"""
RGD_get_annotations

Get disease, phenotype, pathway, GO, and expression annotations for an RGD gene with limit/offset...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RGD_get_annotations(
    rgd_id: str,
    aspect: Optional[str] = "",
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get disease, phenotype, pathway, GO, and expression annotations for an RGD gene with limit/offset...

    Parameters
    ----------
    rgd_id : str
        RGD gene ID (e.g., '2218' for Brca1)
    aspect : str
        Filter by annotation type: 'D' (Disease), 'P' (Pathway), 'W' (Phenotype), 'F'...
    limit : int
        Maximum number of filtered annotations to return in this page.
    offset : int
        Zero-based offset after aspect filtering. Use metadata.next_offset for the ne...
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
            "rgd_id": rgd_id,
            "aspect": aspect,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "RGD_get_annotations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RGD_get_annotations"]
