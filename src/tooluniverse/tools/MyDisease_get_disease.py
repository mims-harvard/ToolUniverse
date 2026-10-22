"""
MyDisease_get_disease

Get disease annotations from MyDisease.info. Large CTD chemical/pathway and HPO phenotype arrays ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MyDisease_get_disease(
    disease_id: str,
    fields: Optional[str] = None,
    annotation_limit: Optional[int] = 20,
    annotation_offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get disease annotations from MyDisease.info. Large CTD chemical/pathway and HPO phenotype arrays ...

    Parameters
    ----------
    disease_id : str
        Disease identifier. Supports MONDO IDs (e.g., 'MONDO:0005148' for T2DM), DOID...
    fields : str
        Comma-separated list of data fields to return. Options: 'mondo', 'disease_ont...
    annotation_limit : int
        Maximum entries returned from each CTD/HPO annotation array.
    annotation_offset : int
        Zero-based offset applied to CTD/HPO annotation arrays; follow each section's...
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
            "disease_id": disease_id,
            "fields": fields,
            "annotation_limit": annotation_limit,
            "annotation_offset": annotation_offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MyDisease_get_disease",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MyDisease_get_disease"]
