"""
PDBeSIFTS_get_all_structures

Get all PDB structures for a UniProt protein, grouped by PDB entry with chain details, from PDBe ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PDBeSIFTS_get_all_structures(
    uniprot_accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get all PDB structures for a UniProt protein, grouped by PDB entry with chain details, from PDBe ...

    Parameters
    ----------
    uniprot_accession : str
        UniProt accession for the protein. Examples: 'P04637' (TP53), 'P00533' (EGFR)...
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
            "name": "PDBeSIFTS_get_all_structures",
            "arguments": {"uniprot_accession": uniprot_accession},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PDBeSIFTS_get_all_structures"]
