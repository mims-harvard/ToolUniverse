"""
InterPro_get_protein_domain_architecture

Get the complete Pfam domain architecture for a protein with exact residue positions using the In...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def InterPro_get_protein_domain_architecture(
    accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the complete Pfam domain architecture for a protein with exact residue positions using the In...

    Parameters
    ----------
    accession : str
        UniProt protein accession. Examples: 'P04637' (TP53, 4 Pfam domains), 'P00533...
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
            "name": "InterPro_get_protein_domain_architecture",
            "arguments": {"accession": accession},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["InterPro_get_protein_domain_architecture"]
