"""
Pharos_get_ligand_targets

Get all protein targets for a drug or ligand from Pharos/TCRD (reverse polypharmacology). Given o...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Pharos_get_ligand_targets(
    ligid: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get all protein targets for a drug or ligand from Pharos/TCRD (reverse polypharmacology). Given o...

    Parameters
    ----------
    ligid : str
        Ligand name or Pharos ligand ID (e.g., 'Haloperidol', 'Imatinib').
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
    _args = {k: v for k, v in {"ligid": ligid}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "Pharos_get_ligand_targets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Pharos_get_ligand_targets"]
