"""
DrugProps_calculate_qed

Calculate Quantitative Estimate of Drug-likeness (QED) score for a compound using the Bickerton e...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DrugProps_calculate_qed(
    smiles: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Calculate Quantitative Estimate of Drug-likeness (QED) score for a compound using the Bickerton e...

    Parameters
    ----------
    smiles : str
        SMILES string of the molecule. Examples: 'CC(=O)Oc1ccccc1C(=O)O' (aspirin, QE...
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
    _args = {k: v for k, v in {"smiles": smiles}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "DrugProps_calculate_qed",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DrugProps_calculate_qed"]
