"""
ENCODE_search_histone_experiments

Search ENCODE histone ChIP-seq experiments by histone modification mark, biosample, or organism. ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ENCODE_search_histone_experiments(
    histone_mark: Optional[str | Any] = None,
    target: Optional[str | Any] = None,
    biosample_term_name: Optional[str | Any] = None,
    biosample: Optional[str | Any] = None,
    organism: Optional[str] = "Homo sapiens",
    limit: Optional[int] = 25,
    biosample_term: Optional[str | Any] = None,
    cell_type: Optional[str | Any] = None,
    tissue: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search ENCODE histone ChIP-seq experiments by histone modification mark, biosample, or organism. ...

    Parameters
    ----------
    histone_mark : str | Any
        Histone modification mark to filter by (e.g., 'H3K4me3', 'H3K27ac', 'H3K27me3...
    target : str | Any
        Alias for histone_mark. Histone modification mark (e.g., 'H3K27ac', 'H3K4me3').
    biosample_term_name : str | Any
        Biosample name from ENCODE ontology (cell lines or tissues, NOT disease names...
    biosample : str | Any
        Alias for biosample_term_name. Biosample (tissue or cell line, e.g., 'liver',...
    organism : str
        Organism scientific name (e.g., 'Homo sapiens', 'Mus musculus').
    limit : int
        Maximum number of results to return (1-100).
    biosample_term : str | Any
        Alias for biosample_term_name. Biosample tissue or cell line (e.g., "breast e...
    cell_type : str | Any
        Alias for biosample_term_name. Cell type or tissue (e.g., 'GM12878', 'K562', ...
    tissue : str | Any
        Alias for biosample_term_name. Tissue or cell line (e.g., 'liver', 'brain', '...
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
            "histone_mark": histone_mark,
            "target": target,
            "biosample_term_name": biosample_term_name,
            "biosample": biosample,
            "organism": organism,
            "limit": limit,
            "biosample_term": biosample_term,
            "cell_type": cell_type,
            "tissue": tissue,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ENCODE_search_histone_experiments",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ENCODE_search_histone_experiments"]
