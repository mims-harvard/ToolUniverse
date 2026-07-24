"""
NCBIDatasets_get_genome_assembly

Get genome assembly metadata for an assembly accession (RefSeq GCF_ or GenBank GCA_) from the NCB...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NCBIDatasets_get_genome_assembly(
    accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get genome assembly metadata for an assembly accession (RefSeq GCF_ or GenBank GCA_) from the NCB...

    Parameters
    ----------
    accession : str
        Assembly accession, e.g. 'GCF_000005845.2' (E. coli K-12) or 'GCF_000001405.4...
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
    _args = {k: v for k, v in {"accession": accession}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "NCBIDatasets_get_genome_assembly",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NCBIDatasets_get_genome_assembly"]
