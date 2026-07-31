"""
geo_list_supplementary_files

List the actual downloadable supplementary/raw files of a GEO Series (GSE) or Sample (GSM), with ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def geo_list_supplementary_files(
    accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List the actual downloadable supplementary/raw files of a GEO Series (GSE) or Sample (GSM), with ...

    Parameters
    ----------
    accession : str
        GEO Series (GSE...) or Sample (GSM...) accession. Examples: 'GSE42657', 'GSE1...
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
    _args = {k: v for k, v in {"accession": accession}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "geo_list_supplementary_files",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["geo_list_supplementary_files"]
