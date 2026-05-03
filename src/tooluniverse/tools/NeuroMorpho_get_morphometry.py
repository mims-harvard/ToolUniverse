"""
NeuroMorpho_get_morphometry

Get morphometric measurements for a neuron from NeuroMorpho.Org. Returns quantitative properties ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NeuroMorpho_get_morphometry(
    neuron_id: Optional[int | Any] = None,
    neuron_name: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get morphometric measurements for a neuron from NeuroMorpho.Org. Returns quantitative properties ...

    Parameters
    ----------
    neuron_id : int | Any
        Numeric neuron ID. Example: 1.
    neuron_name : str | Any
        Neuron name (alternative to neuron_id). Example: 'cnic_001'.
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
        for k, v in {"neuron_id": neuron_id, "neuron_name": neuron_name}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NeuroMorpho_get_morphometry",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NeuroMorpho_get_morphometry"]
