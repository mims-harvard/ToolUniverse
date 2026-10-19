"""
predict_molecular_property

Predict one ADMET property for one molecule, with one model or every model that covers it. REQUIR...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def predict_molecular_property(
    property: str,
    smiles: Optional[str] = None,
    drug: Optional[str] = None,
    backend: Optional[str | list[str]] = None,
    list_models: Optional[bool] = None,
    include_notes: Optional[bool] = None,
    include_details: Optional[bool] = None,
    include_raw: Optional[bool] = None,
    max_workers: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Predict one ADMET property for one molecule, with one model or every model that covers it. REQUIR...

    Parameters
    ----------
    smiles : str
        Molecule as SMILES.
    drug : str
        Compound name, resolved to SMILES via PubChem when 'smiles' is not given.
    property : str
        Canonical property id, using Therapeutics Data Commons dataset names: bbb_mar...
    backend : str | list[str]
        Which model(s) to run. Omit or use 'all' to run every applicable model and ge...
    list_models : bool
        Return the catalogue of models for this task -- id, units, direction, API key...
    include_notes : bool
        With list_models, include per-model caveats. Default true.
    include_details : bool
        Include each model's full canonical record, not just the summary table. Defau...
    include_raw : bool
        Keep bulky payloads (structure coordinates, docking poses) in the reply. Defa...
    max_workers : int
        Models to run concurrently. Default 6.
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
            "smiles": smiles,
            "drug": drug,
            "property": property,
            "backend": backend,
            "list_models": list_models,
            "include_notes": include_notes,
            "include_details": include_details,
            "include_raw": include_raw,
            "max_workers": max_workers,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "predict_molecular_property",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["predict_molecular_property"]
