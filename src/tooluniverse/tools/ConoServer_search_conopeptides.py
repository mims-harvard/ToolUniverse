"""
ConoServer_search_conopeptides

Search ConoServer conopeptides (cone-snail venom peptides) by one or more case-insensitive substr...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ConoServer_search_conopeptides(
    name: Optional[str] = None,
    sequence: Optional[str] = None,
    pharmacological_family: Optional[str] = None,
    gene_superfamily: Optional[str] = None,
    cysteine_framework: Optional[str] = None,
    organism: Optional[str] = None,
    conopeptide_class: Optional[str] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search ConoServer conopeptides (cone-snail venom peptides) by one or more case-insensitive substr...

    Parameters
    ----------
    name : str
        Peptide name substring.
    sequence : str
        Amino-acid sequence substring (e.g. 'GCCS').
    pharmacological_family : str
        e.g. 'alpha conotoxin', 'omega conotoxin'.
    gene_superfamily : str
        e.g. 'A superfamily', 'O1 superfamily'.
    cysteine_framework : str
        Cysteine framework, e.g. 'I', 'III', 'VI/VII'.
    organism : str
        Source Conus species, e.g. 'Conus geographus'.
    conopeptide_class : str
        Conopeptide class, e.g. 'conotoxin'.
    limit : int
        Max records to return (default 25, max 200).
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
            "name": name,
            "sequence": sequence,
            "pharmacological_family": pharmacological_family,
            "gene_superfamily": gene_superfamily,
            "cysteine_framework": cysteine_framework,
            "organism": organism,
            "conopeptide_class": conopeptide_class,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ConoServer_search_conopeptides",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ConoServer_search_conopeptides"]
