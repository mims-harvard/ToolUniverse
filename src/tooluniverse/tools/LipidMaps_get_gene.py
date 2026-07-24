"""
LipidMaps_get_gene

Look up a lipid-metabolism gene in the LIPID MAPS Proteome Database (LMPD). Resolves a gene to it...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def LipidMaps_get_gene(
    input_value: str,
    input_item: Optional[str] = "gene_symbol",
    output_item: Optional[str] = "all",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Look up a lipid-metabolism gene in the LIPID MAPS Proteome Database (LMPD). Resolves a gene to it...

    Parameters
    ----------
    input_value : str
        The gene identifier value to resolve, e.g. 'FASN' (gene symbol), '2194' (NCBI...
    input_item : str
        Namespace of input_value. One of: 'gene_symbol', 'gene_id', 'gene_name', 'lmp...
    output_item : str
        Which fields to return. 'all' (default) returns the complete record; a single...
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
            "input_value": input_value,
            "input_item": input_item,
            "output_item": output_item,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "LipidMaps_get_gene",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["LipidMaps_get_gene"]
