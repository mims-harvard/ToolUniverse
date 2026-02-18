"""
LiteratureSynthesisAgent

AI agent that synthesizes literature findings and provides evidence-based insights
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def LiteratureSynthesisAgent(
    topic: str,
    literature_data: str,
    focus_area: Optional[str] = "General",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    AI agent that synthesizes literature findings and provides evidence-based insights

    Parameters
    ----------
    topic : str
        Research topic or question
    literature_data : str
        Literature findings or abstracts to synthesize
    focus_area : str
        Specific focus area for synthesis
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
            "name": "LiteratureSynthesisAgent",
            "arguments": {
                "topic": topic,
                "literature_data": literature_data,
                "focus_area": focus_area,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["LiteratureSynthesisAgent"]
