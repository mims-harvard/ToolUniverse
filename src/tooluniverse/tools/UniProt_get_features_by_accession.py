"""
UniProt_get_features_by_accession

Extract all sequence features (domains, active/binding sites, motifs, modified residues, signal p...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UniProt_get_features_by_accession(
    accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Extract all sequence features (domains, active/binding sites, motifs, modified residues, signal p...

    Parameters
    ----------
    accession : str
        UniProtKB accession, e.g., 'P04637' (TP53) or 'P05067' (APP).
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
            "name": "UniProt_get_features_by_accession",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["UniProt_get_features_by_accession"]
