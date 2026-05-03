"""
OpenTargets_map_any_disease_id_to_all_other_ids

Given any known disease or phenotype ID (EFO, OMIM, MONDO, UMLS, ICD10, MedDRA, etc.), return all...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenTargets_map_any_disease_id_to_all_other_ids(
    inputId: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Given any known disease or phenotype ID (EFO, OMIM, MONDO, UMLS, ICD10, MedDRA, etc.), return all...

    Parameters
    ----------
    inputId : str
        Any known disease ID (e.g. OMIM:604302, UMLS:C0003873, ICD10:M05, EFO_0000685...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {"inputId": inputId}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "OpenTargets_map_any_disease_id_to_all_other_ids",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenTargets_map_any_disease_id_to_all_other_ids"]
