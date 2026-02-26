"""
DrugProps_lipinski_filter

Check drug-likeness of a compound using Lipinski Rule of Five (Ro5), Veber, Pfizer 3/75, Egan, an...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DrugProps_lipinski_filter(
    smiles: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Check drug-likeness of a compound using Lipinski Rule of Five (Ro5), Veber, Pfizer 3/75, Egan, an...

    Parameters
    ----------
    smiles : str
        SMILES string of the molecule. Examples: 'CC(=O)Oc1ccccc1C(=O)O' (aspirin), '...
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
        {"name": "DrugProps_lipinski_filter", "arguments": {"smiles": smiles}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DrugProps_lipinski_filter"]
