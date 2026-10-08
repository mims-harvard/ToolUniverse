"""
GSA_get_accession

Look up a GSA (Genome Sequence Archive) accession by its CRA-format ID. GSA, run by China's Natio...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GSA_get_accession(
    accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Look up a GSA (Genome Sequence Archive) accession by its CRA-format ID. GSA, run by China's Natio...

    Parameters
    ----------
    accession : str
        GSA accession, e.g. 'CRA002926'.
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
            "name": "GSA_get_accession",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GSA_get_accession"]
