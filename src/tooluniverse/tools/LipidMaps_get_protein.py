"""
LipidMaps_get_protein

Look up a lipid-metabolism protein/enzyme in the LIPID MAPS Proteome Database (LMPD). Resolves a ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def LipidMaps_get_protein(
    input_value: str,
    input_item: Optional[str] = "uniprot_id",
    output_item: Optional[str] = "all",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Look up a lipid-metabolism protein/enzyme in the LIPID MAPS Proteome Database (LMPD). Resolves a ...

    Parameters
    ----------
    input_value : str
        The protein identifier value to resolve, e.g. 'P49327' (UniProt), 'NP_004095'...
    input_item : str
        Namespace of input_value. One of: 'uniprot_id', 'gene_symbol', 'gene_id', 'ge...
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
            "name": "LipidMaps_get_protein",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["LipidMaps_get_protein"]
