"""
LipidMaps_get_compound_by_xref

Look up a LIPID MAPS Structure Database (LMSD) record from an external cross-reference identifier...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def LipidMaps_get_compound_by_xref(
    input_value: str,
    xref_type: Optional[str] = "kegg_id",
    output_item: Optional[str] = "all",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Look up a LIPID MAPS Structure Database (LMSD) record from an external cross-reference identifier...

    Parameters
    ----------
    input_value : str
        The cross-reference identifier value to resolve, e.g. 'C00157' (KEGG), 'HMDB0...
    xref_type : str
        Namespace of input_value. One of: 'kegg_id', 'hmdb_id', 'chebi_id', 'pubchem_...
    output_item : str
        Type of output. Options: 'all' (complete record with all cross-refs), 'name',...
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
            "input_value": input_value,
            "xref_type": xref_type,
            "output_item": output_item,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "LipidMaps_get_compound_by_xref",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["LipidMaps_get_compound_by_xref"]
