"""
HuggingFace_get_model

Get detailed metadata for a specific model on HuggingFace Hub by its author and model name. Retur...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HuggingFace_get_model(
    author: str,
    model_name: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed metadata for a specific model on HuggingFace Hub by its author and model name. Retur...

    Parameters
    ----------
    author : str
        Model author or organization (e.g., 'facebook', 'openai-community', 'google-b...
    model_name : str
        Model name within the author's namespace (e.g., 'esm2_t33_650M_UR50D', 'gpt2'...
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
    _args = {k: v for k, v in {
        "author": author,
                "model_name": model_name
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "HuggingFace_get_model",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["HuggingFace_get_model"]
