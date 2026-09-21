"""
FHIRTerminology_lookup_code

Resolve a code to its display name and synonyms via HL7's public FHIR Terminology Service. Its ma...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FHIRTerminology_lookup_code(
    system: str,
    code: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Resolve a code to its display name and synonyms via HL7's public FHIR Terminology Service. Its ma...

    Parameters
    ----------
    system : str
        'snomed', or a full FHIR code system URI, e.g. 'http://snomed.info/sct'.
    code : str
        Code within that system, e.g. '22298006' (SNOMED CT: Myocardial infarction).
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
    _args = {k: v for k, v in {"system": system, "code": code}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "FHIRTerminology_lookup_code",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FHIRTerminology_lookup_code"]
