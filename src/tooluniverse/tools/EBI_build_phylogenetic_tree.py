"""
EBI_build_phylogenetic_tree

Build a phylogenetic tree from a multiple sequence alignment via EMBL-EBI simple_phylogeny. Takes...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EBI_build_phylogenetic_tree(
    aligned_sequences: str,
    clustering: Optional[str] = "Neighbour-joining",
    distance_correction: Optional[bool] = False,
    exclude_gaps: Optional[bool] = False,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Build a phylogenetic tree from a multiple sequence alignment via EMBL-EBI simple_phylogeny. Takes...

    Parameters
    ----------
    aligned_sequences : str
        Aligned sequences in FASTA format (>=2 records, equal length with gaps as '-'...
    clustering : str
        Tree-building method: 'Neighbour-joining' (default) or 'UPGMA'.
    distance_correction : bool
        Apply Kimura distance correction for multiple substitutions (recommended for ...
    exclude_gaps : bool
        Exclude alignment columns containing any gap before computing distances.
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
            "aligned_sequences": aligned_sequences,
            "clustering": clustering,
            "distance_correction": distance_correction,
            "exclude_gaps": exclude_gaps,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EBI_build_phylogenetic_tree",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EBI_build_phylogenetic_tree"]
