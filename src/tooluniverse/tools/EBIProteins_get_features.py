"""
EBIProteins_get_features

Get protein features filtered by category from the EBI Proteins API. Categories include DOMAINS_A...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EBIProteins_get_features(
    accession: str,
    category: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get protein features filtered by category from the EBI Proteins API. Categories include DOMAINS_A...

    Parameters
    ----------
    accession : str
        UniProt accession. Examples: 'P04637' (TP53), 'P00533' (EGFR), 'P01308' (Insu...
    category : str
        Feature category. Options: 'DOMAINS_AND_SITES', 'MOLECULE_PROCESSING', 'PTM',...
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
        for k, v in {"accession": accession, "category": category}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EBIProteins_get_features",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EBIProteins_get_features"]
