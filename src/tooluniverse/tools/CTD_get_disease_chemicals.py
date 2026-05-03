"""
CTD_get_disease_chemicals

Get curated disease-chemical associations from CTD. Given a disease name, returns chemicals assoc...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CTD_get_disease_chemicals(
    input_terms: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get curated disease-chemical associations from CTD. Given a disease name, returns chemicals assoc...

    Parameters
    ----------
    input_terms : str
        Disease name, MeSH name, synonym, or MeSH/OMIM ID. Examples: 'Breast Neoplasm...
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
    _args = {k: v for k, v in {"input_terms": input_terms}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "CTD_get_disease_chemicals",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CTD_get_disease_chemicals"]
