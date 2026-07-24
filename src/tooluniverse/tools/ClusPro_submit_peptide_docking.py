"""
ClusPro_submit_peptide_docking

Submit a peptide-protein docking job to ClusPro (peptide mode) and return the ClusPro job id. Doc...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClusPro_submit_peptide_docking(
    receptor_pdb_id: str,
    peptide_sequence: str,
    peptide_motif: Optional[str] = None,
    jobname: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Submit a peptide-protein docking job to ClusPro (peptide mode) and return the ClusPro job id. Doc...

    Parameters
    ----------
    receptor_pdb_id : str
        4-letter PDB code of the receptor protein, e.g. '1A2K'.
    peptide_sequence : str
        Peptide amino-acid sequence (1-letter), e.g. 'KGRRL'. Short peptides only.
    peptide_motif : str
        Peptide motif for PDB fragment search (X = wildcard), e.g. 'KXRRL'. Defaults ...
    jobname : str
        Optional job name (defaults to a ClusPro job number).
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
            "receptor_pdb_id": receptor_pdb_id,
            "peptide_sequence": peptide_sequence,
            "peptide_motif": peptide_motif,
            "jobname": jobname,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ClusPro_submit_peptide_docking",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ClusPro_submit_peptide_docking"]
