"""
gather_target_profile

Gather a drug target's identity, function, expression, tractability and safety from OpenTargets, ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def gather_target_profile(
    target: str,
    species: Optional[str] = None,
    sections: Optional[list[str]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Gather a drug target's identity, function, expression, tractability and safety from OpenTargets, ...

    Parameters
    ----------
    target : str
        Gene symbol, Ensembl gene id or UniProt accession, e.g. 'TP53', 'ENSG00000141...
    species : str
        Species for symbol resolution. Default 'human'. Expression, tractability and ...
    sections : list[str]
        Limit which sections are assembled. Omit for all five; an empty list is an er...
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
        for k, v in {"target": target, "species": species, "sections": sections}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "gather_target_profile",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["gather_target_profile"]
