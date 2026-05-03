"""
ELM_get_instances

Get experimentally validated short linear motif (SLiM) instances for a protein from the ELM datab...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ELM_get_instances(
    operation: str,
    uniprot_id: Optional[str | Any] = None,
    uniprot_acc: Optional[str | Any] = None,
    motif_type: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get experimentally validated short linear motif (SLiM) instances for a protein from the ELM datab...

    Parameters
    ----------
    operation : str
        Operation type
    uniprot_id : str | Any
        UniProt accession, e.g., P04637 (TP53), P00533 (EGFR), P38398 (BRCA1), P42336...
    uniprot_acc : str | Any
        Alias for uniprot_id. UniProt accession, e.g., P04637 (TP53)
    motif_type : str | Any
        Filter by motif functional type. CLV=cleavage sites, DEG=degradation motifs, ...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "operation": operation,
            "uniprot_id": uniprot_id,
            "uniprot_acc": uniprot_acc,
            "motif_type": motif_type,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ELM_get_instances",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ELM_get_instances"]
