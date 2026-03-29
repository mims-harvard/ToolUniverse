"""
SMILES_verify

Parse a SMILES string without RDKit and compute molecular properties: molecular weight, molecular...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SMILES_verify(
    smiles: str,
    expected_mw: Optional[float] = None,
    expected_heavy_atoms: Optional[int] = None,
    expected_valence_electrons: Optional[int] = None,
    expected_formula: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Parse a SMILES string without RDKit and compute molecular properties: molecular weight, molecular...

    Parameters
    ----------
    smiles : str
        SMILES string to parse and verify (e.g., 'c1ccccc1' for benzene, 'CC(=O)O' fo...
    expected_mw : float
        Optional expected molecular weight to verify against (tolerance +/- 0.5 Da)
    expected_heavy_atoms : int
        Optional expected heavy atom count to verify against
    expected_valence_electrons : int
        Optional expected total valence electron count to verify against
    expected_formula : str
        Optional expected molecular formula string to verify against (e.g., 'C6H6')
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
            "smiles": smiles,
            "expected_mw": expected_mw,
            "expected_heavy_atoms": expected_heavy_atoms,
            "expected_valence_electrons": expected_valence_electrons,
            "expected_formula": expected_formula,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SMILES_verify",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SMILES_verify"]
