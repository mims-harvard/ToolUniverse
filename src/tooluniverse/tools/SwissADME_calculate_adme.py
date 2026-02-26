"""
SwissADME_calculate_adme

Compute ADMET properties, drug-likeness, and medicinal chemistry friendliness of a small molecule...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SwissADME_calculate_adme(
    operation: str,
    smiles: str,
    molecule_name: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Compute ADMET properties, drug-likeness, and medicinal chemistry friendliness of a small molecule...

    Parameters
    ----------
    operation : str
        Operation type
    smiles : str
        SMILES string of the molecule to analyze. Must be a valid small molecule SMIL...
    molecule_name : str | Any
        Optional name for the molecule. If not provided, SwissADME assigns 'Molecule 1'.
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

    return get_shared_client().run_one_function(
        {
            "name": "SwissADME_calculate_adme",
            "arguments": {
                "operation": operation,
                "smiles": smiles,
                "molecule_name": molecule_name,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SwissADME_calculate_adme"]
