"""
EuroPMCAnnot_get_chemicals_from_article

Extract chemical/compound mentions from a scientific article using Europe PMC text mining. Return...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EuroPMCAnnot_get_chemicals_from_article(
    article_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Extract chemical/compound mentions from a scientific article using Europe PMC text mining. Return...

    Parameters
    ----------
    article_id : str
        PMC article identifier. Format: 'PMC:PMCXXXXXXX'. Examples: 'PMC:PMC4353746',...
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
    _args = {k: v for k, v in {"article_id": article_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "EuroPMCAnnot_get_chemicals_from_article",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EuroPMCAnnot_get_chemicals_from_article"]
