"""
WikiPathways_find_pathways_by_gene

Find all WikiPathways pathways containing a specific gene. Takes a gene identifier (HGNC symbol, ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def WikiPathways_find_pathways_by_gene(
    gene: str,
    species: Optional[str] = "Homo sapiens",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Find all WikiPathways pathways containing a specific gene. Takes a gene identifier (HGNC symbol, ...

    Parameters
    ----------
    gene : str
        Gene identifier to search. Examples: 'TP53', 'BRCA1', 'EGFR', '7157' (Entrez)...
    species : str
        Species to filter results. Default: 'Homo sapiens'. Other options: 'Mus muscu...
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
        k: v for k, v in {"gene": gene, "species": species}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "WikiPathways_find_pathways_by_gene",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["WikiPathways_find_pathways_by_gene"]
