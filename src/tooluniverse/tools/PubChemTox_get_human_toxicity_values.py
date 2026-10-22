"""
PubChemTox_get_human_toxicity_values

Get human toxicity values for a chemical compound from PubChem (PUG View 'Human Toxicity Values' ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PubChemTox_get_human_toxicity_values(
    cid: Optional[int] = None,
    compound_name: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get human toxicity values for a chemical compound from PubChem (PUG View 'Human Toxicity Values' ...

    Parameters
    ----------
    cid : int
        PubChem Compound ID. Examples: 241 (benzene), 887 (methanol), 702 (ethanol), ...
    compound_name : str
        Compound name (used if cid is not provided). Examples: 'benzene', 'methanol',...
    limit : int
        Page size for human toxicity values. Default 30. Continue with metadata.next_...
    offset : int
        Zero-based human-toxicity-value offset. Default 0.
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
            "cid": cid,
            "compound_name": compound_name,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PubChemTox_get_human_toxicity_values",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PubChemTox_get_human_toxicity_values"]
