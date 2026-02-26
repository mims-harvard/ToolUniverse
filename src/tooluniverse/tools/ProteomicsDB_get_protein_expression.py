"""
ProteomicsDB_get_protein_expression

Get mass spectrometry-based protein expression data across human tissues, cell lines, and body fl...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ProteomicsDB_get_protein_expression(
    operation: str,
    uniprot_id: str,
    tissue_category: Optional[str] = None,
    calculation_method: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get mass spectrometry-based protein expression data across human tissues, cell lines, and body fl...

    Parameters
    ----------
    operation : str
        Operation type
    uniprot_id : str
        UniProt accession for the protein (e.g., 'P04637' for TP53, 'P00533' for EGFR...
    tissue_category : str
        Filter by biological source category. 'tissue' for normal tissues, 'cell line...
    calculation_method : str
        Protein quantification method. iBAQ (intensity-Based Absolute Quantification)...
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

    return get_shared_client().run_one_function(
        {
            "name": "ProteomicsDB_get_protein_expression",
            "arguments": {
                "operation": operation,
                "uniprot_id": uniprot_id,
                "tissue_category": tissue_category,
                "calculation_method": calculation_method,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ProteomicsDB_get_protein_expression"]
