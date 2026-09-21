"""
Orphadata_get_disorder

Retrieve a rare disease from Orphanet by ORPHAcode, with synonyms, disorder type, and cross-refer...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Orphadata_get_disorder(
    orphacode: int | str,
    lang: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve a rare disease from Orphanet by ORPHAcode, with synonyms, disorder type, and cross-refer...

    Parameters
    ----------
    orphacode : int | str
        ORPHAcode, e.g. 558.
    lang : str
        Language code: en, fr, de, es, it, nl, pt, pl. Default en.
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
        k: v for k, v in {"orphacode": orphacode, "lang": lang}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Orphadata_get_disorder",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Orphadata_get_disorder"]
