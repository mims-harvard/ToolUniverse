"""
NCICACTUS_resolve

Convert chemical identifiers using the NCI CACTUS Chemical Identifier Resolver. Accepts chemical ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NCICACTUS_resolve(
    identifier: str,
    representation: Optional[str] = "smiles",
    resolve_all: Optional[bool] = False,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Convert chemical identifiers using the NCI CACTUS Chemical Identifier Resolver. Accepts chemical ...

    Parameters
    ----------
    identifier : str
        Chemical identifier to resolve. Accepts: common name (e.g. 'aspirin', 'ibupro...
    representation : str
        Target representation to return. Options: 'smiles' (canonical SMILES), 'iupac...
    resolve_all : bool
        If true, resolves SMILES, IUPAC name, formula, molecular weight, InChIKey, an...
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
            "identifier": identifier,
            "representation": representation,
            "resolve_all": resolve_all,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NCICACTUS_resolve",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NCICACTUS_resolve"]
