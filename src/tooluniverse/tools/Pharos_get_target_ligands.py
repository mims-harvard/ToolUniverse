"""
Pharos_get_target_ligands

Get per-target ligand and drug bioactivities from Pharos/TCRD for a drug target (by gene symbol o...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Pharos_get_target_ligands(
    gene: Optional[str] = None,
    uniprot: Optional[str] = None,
    top: Optional[int] = 3,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get per-target ligand and drug bioactivities from Pharos/TCRD for a drug target (by gene symbol o...

    Parameters
    ----------
    gene : str
        Gene symbol (e.g., 'DRD2', 'EGFR'). Use either gene or uniprot.
    uniprot : str
        UniProt accession (e.g., 'P14416'). Use either gene or uniprot.
    top : int
        Maximum number of ligands to return (1-50).
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
        for k, v in {"gene": gene, "uniprot": uniprot, "top": top}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Pharos_get_target_ligands",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Pharos_get_target_ligands"]
