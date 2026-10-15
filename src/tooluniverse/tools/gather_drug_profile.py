"""
gather_drug_profile

Gather a drug's identity, structure, mechanism of action, approved indications and safety from Ch...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def gather_drug_profile(
    drug: str,
    sections: Optional[list[str]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Gather a drug's identity, structure, mechanism of action, approved indications and safety from Ch...

    Parameters
    ----------
    drug : str
        Drug name or ChEMBL id, e.g. 'aspirin', 'metformin', 'Tylenol', 'CHEMBL25'.
    sections : list[str]
        Limit which sections are assembled. Omit for all five; an empty list is an er...
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
        k: v for k, v in {"drug": drug, "sections": sections}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "gather_drug_profile",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["gather_drug_profile"]
