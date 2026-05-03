"""
CTD_get_chemical_gene_interactions

Get curated chemical-gene interactions from CTD (Comparative Toxicogenomics Database). Given a ch...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CTD_get_chemical_gene_interactions(
    input_terms: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get curated chemical-gene interactions from CTD (Comparative Toxicogenomics Database). Given a ch...

    Parameters
    ----------
    input_terms : str
        Chemical name, MeSH name, synonym, CAS RN, or MeSH ID. Examples: 'bisphenol A...
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
            "name": "CTD_get_chemical_gene_interactions",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CTD_get_chemical_gene_interactions"]
