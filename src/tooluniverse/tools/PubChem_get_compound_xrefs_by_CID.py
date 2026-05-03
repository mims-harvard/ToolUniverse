"""
PubChem_get_compound_xrefs_by_CID

Get external references (XRefs) for compound by CID, including links to ChEBI, DrugBank, KEGG, etc.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PubChem_get_compound_xrefs_by_CID(
    cid: int,
    xref_types: list[str],
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get external references (XRefs) for compound by CID, including links to ChEBI, DrugBank, KEGG, etc.

    Parameters
    ----------
    cid : int
        Compound ID to query external references for, e.g., 2244.
    xref_types : list[str]
        List of external database types to query, e.g., ["RegistryID", "RN", "PubMedI...
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
        k: v for k, v in {"cid": cid, "xref_types": xref_types}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PubChem_get_compound_xrefs_by_CID",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PubChem_get_compound_xrefs_by_CID"]
