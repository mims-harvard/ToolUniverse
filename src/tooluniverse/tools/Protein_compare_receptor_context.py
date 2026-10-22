"""
Protein_compare_receptor_context

Compare conditional sequence preferences with matched receptor deletion on fixed ligand backbones...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Protein_compare_receptor_context(
    position: int,
    parent_residue: str,
    mutant_residue: str,
    alphabet: str,
    scoring_mode: str,
    scorer_family: str,
    expected_poses: list[Any],
    expected_checkpoints: list[str],
    contexts: list[Any],
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Compare conditional sequence preferences with matched receptor deletion on fixed ligand backbones...

    Parameters
    ----------
    position : int
        One-based parent ligand sequence index, not a PDB residue number.
    parent_residue : str

    mutant_residue : str

    alphabet : str
        All 20 canonical amino acids, optionally X, once each in score-vector order; ...
    scoring_mode : str
        Score the selected site conditioned on the other parent residues; backbone-on...
    scorer_family : str
        Inverse-folding architecture family, e.g. ProteinMPNN. Checkpoints are relate...
    expected_poses : list[Any]
        Declare all sampled source-family/coordinate-hash pairs before analysis. Dedu...
    expected_checkpoints : list[str]

    contexts : list[Any]
        Exactly one matched full/deleted result for each declared pose crossed with e...
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
            "position": position,
            "parent_residue": parent_residue,
            "mutant_residue": mutant_residue,
            "alphabet": alphabet,
            "scoring_mode": scoring_mode,
            "scorer_family": scorer_family,
            "expected_poses": expected_poses,
            "expected_checkpoints": expected_checkpoints,
            "contexts": contexts,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Protein_compare_receptor_context",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Protein_compare_receptor_context"]
