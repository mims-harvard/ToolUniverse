"""
PharmacoDB_get_drug_targets

Query PharmacoDB drug-target relationships in three directions. (1) Gene -> targets: pass gene_na...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PharmacoDB_get_drug_targets(
    operation: str,
    gene_name: Optional[str] = None,
    gene_id: Optional[int] = None,
    compound_name: Optional[str] = None,
    compound_id: Optional[int] = None,
    page: Optional[int] = 1,
    per_page: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Query PharmacoDB drug-target relationships in three directions. (1) Gene -> targets: pass gene_na...

    Parameters
    ----------
    operation : str
        Operation type
    gene_name : str
        Gene HGNC symbol for the gene->targets direction (e.g., 'EGFR', 'BRAF'). Mutu...
    gene_id : int
        PharmacoDB gene database ID for the gene->targets direction (e.g., 8931 for E...
    compound_name : str
        Compound/drug name for the compound->targets direction (e.g., 'paclitaxel'). ...
    compound_id : int
        PharmacoDB compound database ID for the compound->targets direction (e.g., 49...
    page : int
        Page number for the full drug-target table direction (when no gene/compound i...
    per_page : int
        Rows per page for the full drug-target table direction (default 20, max 200)....
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
            "gene_name": gene_name,
            "gene_id": gene_id,
            "compound_name": compound_name,
            "compound_id": compound_id,
            "page": page,
            "per_page": per_page,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PharmacoDB_get_drug_targets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PharmacoDB_get_drug_targets"]
