"""
Protein_calculate_pH_linkage

Integrate matched bound/free protein pKas into reference-normalized pH linkage curves, with decla...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Protein_calculate_pH_linkage(
    bound_groups: list[Any],
    free_groups: list[Any],
    expected_groups: list[Any],
    reference_kind: str,
    ph_values: list[Any],
    reference_ph: float,
    provenance: dict[str, Any],
    temperature_kelvin: Optional[float] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Integrate matched bound/free protein pKas into reference-normalized pH linkage curves, with decla...

    Parameters
    ----------
    bound_groups : list[Any]

    free_groups : list[Any]

    expected_groups : list[Any]

    reference_kind : str
        Both modes use titrating pKas; same-coordinate means component extraction, ne...
    ph_values : list[Any]

    reference_ph : float

    temperature_kelvin : float
        Defaults to 298.15 K; used only to convert the conditional logarithmic trend ...
    provenance : dict[str, Any]

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
        for k, v in {
            "bound_groups": bound_groups,
            "free_groups": free_groups,
            "expected_groups": expected_groups,
            "reference_kind": reference_kind,
            "ph_values": ph_values,
            "reference_ph": reference_ph,
            "temperature_kelvin": temperature_kelvin,
            "provenance": provenance,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Protein_calculate_pH_linkage",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Protein_calculate_pH_linkage"]
