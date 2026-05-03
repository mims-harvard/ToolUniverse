"""
CPIC_list_guidelines

List all CPIC pharmacogenomic guidelines. Returns ~29 evidence-based guidelines (count may vary a...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CPIC_list_guidelines(
    gene: Optional[str] = None,
    gene_symbol: Optional[str] = None,
    drug: Optional[str] = None,
    drug_name: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List all CPIC pharmacogenomic guidelines. Returns ~29 evidence-based guidelines (count may vary a...

    Parameters
    ----------
    gene : str
        Filter by gene symbol (e.g., CYP2D6, TPMT). Returns only guidelines involving...
    gene_symbol : str
        Alias for gene. Filter by gene symbol (e.g., CYP2D6, TPMT).
    drug : str
        Filter by drug name (e.g., 'codeine', 'warfarin', 'clopidogrel'). Case-insens...
    drug_name : str
        Alias for drug.
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
            "gene": gene,
            "gene_symbol": gene_symbol,
            "drug": drug,
            "drug_name": drug_name,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CPIC_list_guidelines",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CPIC_list_guidelines"]
