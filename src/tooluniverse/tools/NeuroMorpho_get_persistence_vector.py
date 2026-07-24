"""
NeuroMorpho_get_persistence_vector

Get the persistence vector (Topological Morphology Descriptor, TMD) for a NeuroMorpho neuron by i...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NeuroMorpho_get_persistence_vector(
    neuron_id: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the persistence vector (Topological Morphology Descriptor, TMD) for a NeuroMorpho neuron by i...

    Parameters
    ----------
    neuron_id : int
        NeuroMorpho numeric neuron ID. Get one from NeuroMorpho_search_neurons. Examp...
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
    _args = {k: v for k, v in {"neuron_id": neuron_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "NeuroMorpho_get_persistence_vector",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NeuroMorpho_get_persistence_vector"]
