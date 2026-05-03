"""
ProteomicsDB_get_expression_summary

Get a tissue expression summary for a protein from ProteomicsDB, showing the top tissues/cell lin...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ProteomicsDB_get_expression_summary(
    operation: str,
    uniprot_id: str,
    top_n: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get a tissue expression summary for a protein from ProteomicsDB, showing the top tissues/cell lin...

    Parameters
    ----------
    operation : str
        Operation type
    uniprot_id : str
        UniProt accession for the protein (e.g., 'P04637' for TP53, 'P00533' for EGFR)
    top_n : int
        Number of top tissues to return, ranked by expression level (default: 10)
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "operation": operation,
            "uniprot_id": uniprot_id,
            "top_n": top_n,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ProteomicsDB_get_expression_summary",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ProteomicsDB_get_expression_summary"]
