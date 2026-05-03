"""
ENCODE_search_rnaseq_experiments

Search ENCODE RNA-seq experiments by biosample (cell type or tissue), organism, and assay type (t...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ENCODE_search_rnaseq_experiments(
    biosample_term_name: Optional[str | Any] = None,
    biosample: Optional[str | Any] = None,
    cell_type: Optional[str | Any] = None,
    tissue: Optional[str | Any] = None,
    organism: Optional[str] = "Homo sapiens",
    assay_type: Optional[str] = "total RNA-seq",
    limit: Optional[int] = 25,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search ENCODE RNA-seq experiments by biosample (cell type or tissue), organism, and assay type (t...

    Parameters
    ----------
    biosample_term_name : str | Any
        Biosample name from ENCODE ontology (e.g., 'K562', 'HepG2', 'GM12878', 'liver...
    biosample : str | Any
        Alias for biosample_term_name. Cell type or tissue (e.g., 'K562', 'liver').
    cell_type : str | Any
        Alias for biosample_term_name. Cell type (e.g., 'K562', 'HepG2', 'GM12878').
    tissue : str | Any
        Alias for biosample_term_name. Tissue type (e.g., 'liver', 'brain', 'heart').
    organism : str
        Organism scientific name (e.g., 'Homo sapiens', 'Mus musculus').
    assay_type : str
        RNA-seq assay type: 'total RNA-seq' (default, all RNA), 'polyA plus RNA-seq' ...
    limit : int
        Maximum number of results to return (1-100).
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
            "biosample_term_name": biosample_term_name,
            "biosample": biosample,
            "cell_type": cell_type,
            "tissue": tissue,
            "organism": organism,
            "assay_type": assay_type,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ENCODE_search_rnaseq_experiments",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ENCODE_search_rnaseq_experiments"]
