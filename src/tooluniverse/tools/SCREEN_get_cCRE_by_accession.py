"""
SCREEN_get_cCRE_by_accession

Look up one or more candidate cis-Regulatory Elements (cCREs) in the ENCODE SCREEN registry by SC...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SCREEN_get_cCRE_by_accession(
    accession: str | list[str],
    assembly: Optional[str] = "GRCh38",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Look up one or more candidate cis-Regulatory Elements (cCREs) in the ENCODE SCREEN registry by SC...

    Parameters
    ----------
    accession : str | list[str]
        A single SCREEN cCRE accession string, or a list of accession strings (e.g. '...
    assembly : str
        Genome assembly: 'GRCh38' (human, default) or 'mm10' (mouse).
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"accession": accession, "assembly": assembly}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SCREEN_get_cCRE_by_accession",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SCREEN_get_cCRE_by_accession"]
