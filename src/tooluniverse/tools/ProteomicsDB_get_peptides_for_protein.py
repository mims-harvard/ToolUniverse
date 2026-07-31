"""
ProteomicsDB_get_peptides_for_protein

Get peptide-level mass spectrometry identification evidence for a protein from ProteomicsDB. Give...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ProteomicsDB_get_peptides_for_protein(
    operation: str,
    uniprot_id: str,
    max_results: Optional[int] = 50,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get peptide-level mass spectrometry identification evidence for a protein from ProteomicsDB. Give...

    Parameters
    ----------
    operation : str
        Operation type
    uniprot_id : str
        UniProt accession for the protein (e.g. 'P00533' for EGFR, 'P04637' for TP53).
    max_results : int
        Maximum number of peptide identification rows to return (default 50).
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
            "operation": operation,
            "uniprot_id": uniprot_id,
            "max_results": max_results,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ProteomicsDB_get_peptides_for_protein",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ProteomicsDB_get_peptides_for_protein"]
