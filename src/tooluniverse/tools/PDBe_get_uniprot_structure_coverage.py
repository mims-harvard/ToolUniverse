"""
PDBe_get_uniprot_structure_coverage

Get all PDB structures mapped to a UniProt protein, ranked by quality and coverage, from the PDBe...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PDBe_get_uniprot_structure_coverage(
    uniprot_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get all PDB structures mapped to a UniProt protein, ranked by quality and coverage, from the PDBe...

    Parameters
    ----------
    uniprot_id : str
        UniProt accession. Examples: 'P04637' (TP53, many structures), 'P00533' (EGFR...
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
    _args = {k: v for k, v in {
        "uniprot_id": uniprot_id
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "PDBe_get_uniprot_structure_coverage",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["PDBe_get_uniprot_structure_coverage"]
