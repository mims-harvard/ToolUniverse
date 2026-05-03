"""
MyChem_get_chemical_annotation

Get detailed annotation for a specific chemical/drug by its InChIKey or other ID. Returns compreh...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MyChem_get_chemical_annotation(
    chem_id: str,
    fields: Optional[str] = "drugbank,chebi,pubchem,chembl,drugcentral",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed annotation for a specific chemical/drug by its InChIKey or other ID. Returns compreh...

    Parameters
    ----------
    chem_id : str
        Chemical ID. InChIKey recommended (e.g., 'BSYNRYMUTXBXSQ-UHFFFAOYSA-N' for as...
    fields : str
        Fields to return. Useful: drugbank (comprehensive), chebi, pubchem, chembl, d...
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
        k: v for k, v in {"chem_id": chem_id, "fields": fields}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MyChem_get_chemical_annotation",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MyChem_get_chemical_annotation"]
