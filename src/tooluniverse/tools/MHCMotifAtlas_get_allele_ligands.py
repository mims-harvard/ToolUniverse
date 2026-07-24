"""
MHCMotifAtlas_get_allele_ligands

Retrieve curated lists of naturally-presented MHC ligand peptides for a specific allele from the ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MHCMotifAtlas_get_allele_ligands(
    allele: str,
    mhc_class: Optional[str] = "I",
    include_sequence: Optional[bool] = False,
    limit: Optional[int] = 100,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve curated lists of naturally-presented MHC ligand peptides for a specific allele from the ...

    Parameters
    ----------
    allele : str
        MHC allele in MHC Motif Atlas format. Class I example: 'A0101' (HLA-A*01:01),...
    mhc_class : str
        'I' for MHC class I or 'II' for MHC class II. Default 'I'.
    include_sequence : bool
        If true, also fetch the per-allele MHC protein sequence (from MHC_I_sequences...
    limit : int
        Maximum number of ligand peptides to return (1-1000). Default 100.
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
            "allele": allele,
            "mhc_class": mhc_class,
            "include_sequence": include_sequence,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MHCMotifAtlas_get_allele_ligands",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MHCMotifAtlas_get_allele_ligands"]
