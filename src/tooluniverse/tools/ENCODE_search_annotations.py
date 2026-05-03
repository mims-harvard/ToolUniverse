"""
ENCODE_search_annotations

Search ENCODE annotations including candidate cis-Regulatory Elements (cCREs), chromatin states, ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ENCODE_search_annotations(
    annotation_type: Optional[str] = "candidate Cis-Regulatory Elements",
    biosample_term_name: Optional[str | Any] = None,
    organism: Optional[str] = "Homo sapiens",
    assembly: Optional[str] = "GRCh38",
    limit: Optional[int] = 25,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search ENCODE annotations including candidate cis-Regulatory Elements (cCREs), chromatin states, ...

    Parameters
    ----------
    annotation_type : str
        Annotation type filter. Options: 'candidate Cis-Regulatory Elements' (cCREs),...
    biosample_term_name : str | Any
        Biosample filter (e.g., 'K562', 'HepG2'). Leave empty for all.
    organism : str
        Organism scientific name.
    assembly : str
        Genome assembly (e.g., 'GRCh38', 'hg19', 'mm10').
    limit : int
        Maximum number of results.
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
            "annotation_type": annotation_type,
            "biosample_term_name": biosample_term_name,
            "organism": organism,
            "assembly": assembly,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ENCODE_search_annotations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ENCODE_search_annotations"]
