"""
Orphadata_get_phenotypes

Retrieve HPO phenotype annotations for a rare disease by ORPHAcode, with each phenotype's frequen...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Orphadata_get_phenotypes(
    orphacode: int | str,
    limit: Optional[int] = None,
    lang: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve HPO phenotype annotations for a rare disease by ORPHAcode, with each phenotype's frequen...

    Parameters
    ----------
    orphacode : int | str
        ORPHAcode, e.g. 558.
    limit : int
        Maximum phenotypes to return. Omit for all.
    lang : str
        Language code. Default en.
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
        for k, v in {"orphacode": orphacode, "limit": limit, "lang": lang}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Orphadata_get_phenotypes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Orphadata_get_phenotypes"]
