"""
MassIVE_get_protein_identifications

Identification-level access to MassIVE datasets via the ProXI standard API. MassIVE's other tools...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MassIVE_get_protein_identifications(
    accession: Optional[str] = None,
    protein_accession: Optional[str] = None,
    result_type: Optional[str] = "proteins",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Identification-level access to MassIVE datasets via the ProXI standard API. MassIVE's other tools...

    Parameters
    ----------
    accession : str
        Dataset accession (ProteomeXchange PXD or MassIVE MSV, e.g. 'PXD000561'). Req...
    protein_accession : str
        Protein accession for a cross-dataset lookup (e.g. 'A2M_MOUSE', 'A2MP_MOUSE')...
    result_type : str
        'proteins' (default) for protein identification summaries, or 'psms' for pept...
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
            "accession": accession,
            "protein_accession": protein_accession,
            "result_type": result_type,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MassIVE_get_protein_identifications",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MassIVE_get_protein_identifications"]
