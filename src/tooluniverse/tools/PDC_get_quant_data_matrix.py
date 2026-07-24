"""
PDC_get_quant_data_matrix

Get the quantitative protein abundance matrix (gene x aliquot/case) for a CPTAC/PDC study - the c...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PDC_get_quant_data_matrix(
    operation: str,
    pdc_study_id: str,
    data_type: Optional[str] = "log2_ratio",
    max_genes: Optional[int] = 50,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the quantitative protein abundance matrix (gene x aliquot/case) for a CPTAC/PDC study - the c...

    Parameters
    ----------
    operation : str
        Operation type
    pdc_study_id : str
        PDC study identifier (e.g. 'PDC000127' for CPTAC CCRCC Discovery Study - Prot...
    data_type : str
        Quantitation data type. Common values: 'log2_ratio' (default), 'unshared_log2...
    max_genes : int
        Maximum number of gene rows to return (the aliquot column header is always re...
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
            "pdc_study_id": pdc_study_id,
            "data_type": data_type,
            "max_genes": max_genes,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PDC_get_quant_data_matrix",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PDC_get_quant_data_matrix"]
