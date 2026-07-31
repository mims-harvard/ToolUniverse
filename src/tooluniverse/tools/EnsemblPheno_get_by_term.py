"""
EnsemblPheno_get_by_term

Reverse phenotype lookup from the Ensembl REST API: given a trait/disease NAME (e.g. 'Alzheimer d...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EnsemblPheno_get_by_term(
    species: Optional[str] = "homo_sapiens",
    term: Optional[str] = None,
    accession: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Reverse phenotype lookup from the Ensembl REST API: given a trait/disease NAME (e.g. 'Alzheimer d...

    Parameters
    ----------
    species : str
        Species name. Use 'homo_sapiens' for human. Default: 'homo_sapiens'.
    term : str
        Trait or disease name. Examples: 'Alzheimer disease', 'Coronary artery diseas...
    accession : str
        Ontology accession (EFO, HP, MONDO, Orphanet). Examples: 'EFO:0000249' (Alzhe...
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
        for k, v in {"species": species, "term": term, "accession": accession}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EnsemblPheno_get_by_term",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EnsemblPheno_get_by_term"]
