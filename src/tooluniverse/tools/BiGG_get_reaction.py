"""
BiGG_get_reaction

Get detailed reaction information including stoichiometry, metabolites, gene-reaction rules, and ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BiGG_get_reaction(
    operation: str,
    reaction_id: str,
    model_id: Optional[str] = "universal",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed reaction information including stoichiometry, metabolites, gene-reaction rules, and ...

    Parameters
    ----------
    operation : str
        Operation type
    reaction_id : str
        Required: BiGG reaction ID (e.g., 'GAPD', 'PGI')
    model_id : str
        Model ID or 'universal' for universal reaction database
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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "operation": operation,
            "reaction_id": reaction_id,
            "model_id": model_id,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BiGG_get_reaction",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BiGG_get_reaction"]
