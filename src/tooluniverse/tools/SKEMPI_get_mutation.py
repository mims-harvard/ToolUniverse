"""
SKEMPI_get_mutation

Retrieve the measured binding effect of one specific substitution in a protein-protein complex. M...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SKEMPI_get_mutation(
    pdb_id: str,
    mutation: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve the measured binding effect of one specific substitution in a protein-protein complex. M...

    Parameters
    ----------
    pdb_id : str
        PDB entry of the complex, e.g. '1CSE'.
    mutation : str
        Substitution in SKEMPI cleaned notation, e.g. 'LI38G'.
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
        for k, v in {"pdb_id": pdb_id, "mutation": mutation}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SKEMPI_get_mutation",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SKEMPI_get_mutation"]
