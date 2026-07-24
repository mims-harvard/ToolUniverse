"""
MGnify_get_samples

List biological SAMPLES in MGnify (EBI Metagenomics) with full geographic/host/environment proven...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MGnify_get_samples(
    sample_accession: Optional[str] = None,
    study_accession: Optional[str] = None,
    biome: Optional[str] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List biological SAMPLES in MGnify (EBI Metagenomics) with full geographic/host/environment proven...

    Parameters
    ----------
    sample_accession : str
        Fetch a single sample by its MGnify/ENA accession (e.g., 'SRS10016989'). If p...
    study_accession : str
        Filter samples belonging to a study (e.g., 'MGYS00002008').
    biome : str
        Filter by biome name lineage (e.g., 'root:Host-associated:Human:Digestive sys...
    page : int
        Page number (default 1).
    page_size : int
        Samples per page (default 25, max 100).
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
            "sample_accession": sample_accession,
            "study_accession": study_accession,
            "biome": biome,
            "page": page,
            "page_size": page_size,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MGnify_get_samples",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MGnify_get_samples"]
