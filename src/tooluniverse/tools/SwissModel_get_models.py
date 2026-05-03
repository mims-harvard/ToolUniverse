"""
SwissModel_get_models

Get all available protein homology models from SWISS-MODEL Repository for a UniProt accession. Re...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SwissModel_get_models(
    uniprot_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get all available protein homology models from SWISS-MODEL Repository for a UniProt accession. Re...

    Parameters
    ----------
    uniprot_id : str
        UniProt accession identifier. Examples: 'P04637' (human p53), 'P00533' (human...
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
    _args = {k: v for k, v in {"uniprot_id": uniprot_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "SwissModel_get_models",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SwissModel_get_models"]
