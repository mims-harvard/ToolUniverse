"""
PepCalc_peptide_properties

Calculate physicochemical properties for a peptide with optional N-terminal and C-terminal chemic...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PepCalc_peptide_properties(
    seq: str,
    N_term: Optional[str] = "H",
    C_term: Optional[str] = "OH",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Calculate physicochemical properties for a peptide with optional N-terminal and C-terminal chemic...

    Parameters
    ----------
    seq : str
        Peptide sequence in single-letter amino acid code (e.g. 'HAEGTFTSDVSSYLEGQAAK...
    N_term : str
        N-terminal group as a Pep-Calc chemical string. Default 'H' (free amine, unmo...
    C_term : str
        C-terminal group as a Pep-Calc chemical string. Default 'OH' (free acid, unmo...
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
        for k, v in {"seq": seq, "N_term": N_term, "C_term": C_term}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PepCalc_peptide_properties",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PepCalc_peptide_properties"]
