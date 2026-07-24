"""
RxClass_get_disease_relations

Get MED-RT drug<->disease relations (may_treat, may_prevent, CI_with, induces, has_PE) from NLM R...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RxClass_get_disease_relations(
    drug_name: Optional[str] = None,
    rxcui: Optional[str] = None,
    class_id: Optional[str] = None,
    rela: Optional[str] = None,
    ttys: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get MED-RT drug<->disease relations (may_treat, may_prevent, CI_with, induces, has_PE) from NLM R...

    Parameters
    ----------
    drug_name : str
        Forward lookup: drug name. Examples: 'albuterol', 'aspirin', 'metoprolol'. Pr...
    rxcui : str
        Forward lookup: RxNorm RXCUI (alternative to drug_name).
    class_id : str
        Reverse lookup: MED-RT/MeSH disease class ID to find all related drugs for. E...
    rela : str
        MED-RT relationship to filter on. Options: 'may_treat', 'may_prevent', 'CI_wi...
    ttys : str
        Reverse lookup only: RxNorm term types for returned drugs. Options: 'IN' (ing...
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
            "drug_name": drug_name,
            "rxcui": rxcui,
            "class_id": class_id,
            "rela": rela,
            "ttys": ttys,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "RxClass_get_disease_relations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RxClass_get_disease_relations"]
