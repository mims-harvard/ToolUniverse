"""
SwissModel_get_models

Get a paginated list of protein structures from SWISS-MODEL Repository for a UniProt accession. R...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SwissModel_get_models(
    uniprot_id: str,
    range: Optional[str] = None,
    provider: Optional[str] = None,
    template: Optional[str] = None,
    limit: Optional[int] = 30,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get a paginated list of protein structures from SWISS-MODEL Repository for a UniProt accession. R...

    Parameters
    ----------
    uniprot_id : str
        UniProt accession identifier. Examples: 'P04637' (human p53), 'P00533' (human...
    range : str
        Optional residue range filter; only models covering this range are returned. ...
    provider : str
        Optional model-provider filter. 'swissmodel' returns only SWISS-MODEL homolog...
    template : str
        Optional template filter; restrict results to models built from this template...
    limit : int
        Maximum models to return in this page.
    offset : int
        Zero-based model offset. Continue with next_offset while has_more is true.
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
            "uniprot_id": uniprot_id,
            "range": range,
            "provider": provider,
            "template": template,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SwissModel_get_models",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SwissModel_get_models"]
