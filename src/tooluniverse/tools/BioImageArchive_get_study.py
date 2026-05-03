"""
BioImageArchive_get_study

Get detailed information about a specific BioImage Archive study by accession number. Returns com...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BioImageArchive_get_study(
    accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed information about a specific BioImage Archive study by accession number. Returns com...

    Parameters
    ----------
    accession : str
        BioImage Archive study accession number. Format: S-BIAD#### or S-BSST#### or ...
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
            "name": "BioImageArchive_get_study",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BioImageArchive_get_study"]
