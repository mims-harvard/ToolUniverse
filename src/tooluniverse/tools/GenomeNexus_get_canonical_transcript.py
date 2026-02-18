"""
GenomeNexus_get_canonical_transcript

Get the canonical transcript for a gene from Genome Nexus (MSK). Returns the Ensembl transcript I...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GenomeNexus_get_canonical_transcript(
    gene_symbol: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the canonical transcript for a gene from Genome Nexus (MSK). Returns the Ensembl transcript I...

    Parameters
    ----------
    gene_symbol : str
        HUGO gene symbol. Examples: 'TP53', 'BRAF', 'BRCA1', 'EGFR', 'KRAS'.
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
        {
            "name": "GenomeNexus_get_canonical_transcript",
            "arguments": {"gene_symbol": gene_symbol},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GenomeNexus_get_canonical_transcript"]
