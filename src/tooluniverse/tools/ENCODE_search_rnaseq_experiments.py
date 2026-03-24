"""
ENCODE_search_rnaseq_experiments

Search ENCODE RNA-seq experiments by biosample (cell type or tissue), organism, and assay type.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ENCODE_search_rnaseq_experiments(
    biosample_term_name: Optional[str] = None,
    biosample: Optional[str] = None,
    cell_type: Optional[str] = None,
    tissue: Optional[str] = None,
    organism: Optional[str] = "Homo sapiens",
    assay_type: Optional[str] = "total RNA-seq",
    limit: Optional[int] = 25,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search ENCODE RNA-seq experiments by biosample, organism, and assay type.

    Parameters
    ----------
    biosample_term_name : str, optional
        Biosample from ENCODE ontology (e.g., 'K562', 'HepG2', 'liver', 'brain').
    biosample : str, optional
        Alias for biosample_term_name.
    cell_type : str, optional
        Alias for biosample_term_name. Cell type (e.g., 'K562', 'GM12878').
    tissue : str, optional
        Alias for biosample_term_name. Tissue (e.g., 'liver', 'brain').
    organism : str
        Organism scientific name (e.g., 'Homo sapiens', 'Mus musculus').
    assay_type : str
        RNA-seq assay type: 'total RNA-seq' (default), 'polyA plus RNA-seq', 'small RNA-seq',
        'microRNA-seq'. Aliases: 'total', 'polya', 'mirna', 'small'.
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
