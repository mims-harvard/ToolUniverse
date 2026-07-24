"""
SwissModel_get_models_batch

Batch SWISS-MODEL Repository lookup for up to 250 UniProt accessions in a single call. The single...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SwissModel_get_models_batch(
    uniprot_ids: list[str],
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Batch SWISS-MODEL Repository lookup for up to 250 UniProt accessions in a single call. The single...

    Parameters
    ----------
    uniprot_ids : list[str]
        List of up to 250 UniProt accessions, e.g. ['P04637', 'P00533', 'P38398']. A ...
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
    _args = {k: v for k, v in {"uniprot_ids": uniprot_ids}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "SwissModel_get_models_batch",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SwissModel_get_models_batch"]
