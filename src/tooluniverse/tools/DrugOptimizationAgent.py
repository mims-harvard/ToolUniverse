"""
DrugOptimizationAgent

AI agent that analyzes drug optimization strategies based on ADMET and efficacy data
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DrugOptimizationAgent(
    compounds: str,
    admet_data: Optional[str] = "",
    efficacy_data: Optional[str] = "",
    target_profile: Optional[str] = "",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    AI agent that analyzes drug optimization strategies based on ADMET and efficacy data

    Parameters
    ----------
    compounds : str
        List of compounds to optimize (comma-separated)
    admet_data : str
        ADMET properties and issues
    efficacy_data : str
        Efficacy and potency data
    target_profile : str
        Target profile and requirements
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
            "name": "DrugOptimizationAgent",
            "arguments": {
                "compounds": compounds,
                "admet_data": admet_data,
                "efficacy_data": efficacy_data,
                "target_profile": target_profile,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DrugOptimizationAgent"]
