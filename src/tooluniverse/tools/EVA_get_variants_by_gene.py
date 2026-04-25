"""
EVA_get_variants_by_gene

Get genetic variants from the European Variation Archive (EVA) for a specific gene. EVA is hosted...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EVA_get_variants_by_gene(
    gene: str,
    species: Optional[str] = 'hsapiens_grch38',
    limit: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get genetic variants from the European Variation Archive (EVA) for a specific gene. EVA is hosted...

    Parameters
    ----------
    gene : str
        Gene symbol (HGNC format, e.g., 'BRCA1', 'TP53', 'EGFR', 'BRCA2', 'APOE')
    species : str
        Species and assembly (e.g., 'hsapiens_grch38', 'hsapiens_grch37', 'mmusculus_...
    limit : int
        Maximum number of variants to return (default 20, max ~1000)
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
    _args = {k: v for k, v in {
        "gene": gene,
                "species": species,
                "limit": limit
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "EVA_get_variants_by_gene",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["EVA_get_variants_by_gene"]
