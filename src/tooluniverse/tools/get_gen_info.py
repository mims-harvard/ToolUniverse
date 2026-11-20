"""
get_gen_info

Get installation and interface details for Gen, a standalone command-line genome version control ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def get_gen_info(
    include_examples: Optional[bool] = True,
    source: Optional[str] = "auto",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get installation and interface details for Gen, a standalone command-line genome version control ...

    Parameters
    ----------
    include_examples : bool
        Whether to include metadata-only examples and quick-start instructions
    source : str
        Use `local` for curated offline Gen CLI, Python, and R details. Use `auto` to...
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
        for k, v in {"include_examples": include_examples, "source": source}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "get_gen_info",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["get_gen_info"]
