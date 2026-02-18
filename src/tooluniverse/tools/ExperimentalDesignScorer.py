"""
ExperimentalDesignScorer

Assesses a proposed experimental design by assigning scores and structured feedback on hypothesis...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ExperimentalDesignScorer(
    hypothesis: str,
    design_description: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Assesses a proposed experimental design by assigning scores and structured feedback on hypothesis...

    Parameters
    ----------
    hypothesis : str
        A clear statement of the research hypothesis to be tested.
    design_description : str
        A detailed description of the proposed experimental design, including variabl...
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
            "name": "ExperimentalDesignScorer",
            "arguments": {
                "hypothesis": hypothesis,
                "design_description": design_description,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ExperimentalDesignScorer"]
