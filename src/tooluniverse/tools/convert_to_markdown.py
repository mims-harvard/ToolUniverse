"""
convert_to_markdown

Convert a resource described by an http:, https:, file: or data: URI to markdown.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def convert_to_markdown(
    uri: str,
    output_path: Optional[str] = None,
    enable_plugins: Optional[bool] = False,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Convert a resource described by an http:, https:, file: or data: URI to markdown.

    Parameters
    ----------
    uri : str
        URI of the resource to convert (supports http:, https:, file:, data: URIs)
    output_path : str
        Optional output file path
    enable_plugins : bool
        Enable 3rd-party plugins
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
            "uri": uri,
            "output_path": output_path,
            "enable_plugins": enable_plugins,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "convert_to_markdown",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["convert_to_markdown"]
