"""
pubmed_parse_pico_mcp

Parse clinical question into PICO elements (Population, Intervention, Comparison, Outcome).
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def pubmed_parse_pico_mcp(
    description: str,
    p: Optional[str] = None,
    i: Optional[str] = None,
    c: Optional[str] = None,
    o: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Parse clinical question into PICO elements (Population, Intervention, Comparison, Outcome).

    Parameters
    ----------
    description : str
        Clinical question in natural language
    p : str

    i : str

    c : str

    o : str

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
        {
            "name": "pubmed_parse_pico_mcp",
            "arguments": {"description": description, "p": p, "i": i, "c": c, "o": o},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["pubmed_parse_pico_mcp"]
