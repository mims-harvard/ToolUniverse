"""
EBIProteins_get_variation

Get all known protein sequence variants for a UniProt protein from the EBI Proteins API. Returns ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EBIProteins_get_variation(
    accession: str,
    source_type: Optional[str | Any] = None,
    disease_only: Optional[bool] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get all known protein sequence variants for a UniProt protein from the EBI Proteins API. Returns ...

    Parameters
    ----------
    accession : str
        UniProt accession. Examples: 'P04637' (TP53), 'P00533' (EGFR), 'P38398' (BRCA1).
    source_type : str | Any
        Filter by variant source. Options: 'large_scale_study' (COSMIC, gnomAD), 'mix...
    disease_only : bool
        If true, return only variants with disease associations. Default: false.
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
            "accession": accession,
            "source_type": source_type,
            "disease_only": disease_only,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EBIProteins_get_variation",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EBIProteins_get_variation"]
