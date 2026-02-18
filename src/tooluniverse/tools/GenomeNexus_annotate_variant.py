"""
GenomeNexus_annotate_variant

Annotate a genomic variant using Genome Nexus (Memorial Sloan Kettering), which aggregates varian...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GenomeNexus_annotate_variant(
    hgvsg: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Annotate a genomic variant using Genome Nexus (Memorial Sloan Kettering), which aggregates varian...

    Parameters
    ----------
    hgvsg : str
        Genomic variant in HGVS notation using GRCh37/hg19 coordinates. Format: 'chr:...
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

    return get_shared_client().run_one_function(
        {"name": "GenomeNexus_annotate_variant", "arguments": {"hgvsg": hgvsg}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GenomeNexus_annotate_variant"]
