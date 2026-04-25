"""
ClinGen_dosage_by_gene

Get ClinGen dosage sensitivity curation for a specific gene using the JSON API. Returns haploinsu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinGen_dosage_by_gene(
    gene: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get ClinGen dosage sensitivity curation for a specific gene using the JSON API. Returns haploinsu...

    Parameters
    ----------
    gene : str
        Gene symbol to search for (e.g., 'BRCA1', 'MECP2', 'TP53'). Case-insensitive.
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
    _args = {k: v for k, v in {
        "gene": gene
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ClinGen_dosage_by_gene",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["ClinGen_dosage_by_gene"]
