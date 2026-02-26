"""
DrugProps_pains_filter

Screen a compound for PAINS (Pan-Assay Interference Compounds), Brenk undesirable substructures, ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DrugProps_pains_filter(
    smiles: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Screen a compound for PAINS (Pan-Assay Interference Compounds), Brenk undesirable substructures, ...

    Parameters
    ----------
    smiles : str
        SMILES string of the molecule to screen. Examples: 'O=C1CSC(=S)N1' (rhodanine...
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

    return get_shared_client().run_one_function(
        {"name": "DrugProps_pains_filter", "arguments": {"smiles": smiles}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DrugProps_pains_filter"]
