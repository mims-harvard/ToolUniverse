"""
PDBeSIFTS_get_pdb_to_uniprot

Map PDB entry chains to UniProt protein accessions using PDBe SIFTS cross-referencing. For a give...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PDBeSIFTS_get_pdb_to_uniprot(
    pdb_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Map PDB entry chains to UniProt protein accessions using PDBe SIFTS cross-referencing. For a give...

    Parameters
    ----------
    pdb_id : str
        PDB entry ID (4-character code). Examples: '1tup' (p53-DNA complex), '1m17' (...
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
    _args = {k: v for k, v in {"pdb_id": pdb_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "PDBeSIFTS_get_pdb_to_uniprot",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PDBeSIFTS_get_pdb_to_uniprot"]
