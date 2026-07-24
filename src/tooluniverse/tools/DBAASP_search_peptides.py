"""
DBAASP_search_peptides

Search/filter DBAASP antimicrobial peptides by sequence (exact/substring), peptide name, target o...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DBAASP_search_peptides(
    sequence: Optional[str] = None,
    sequence_option: Optional[str] = None,
    name: Optional[str] = None,
    target_species: Optional[str] = None,
    target_group: Optional[str] = None,
    sequence_length: Optional[int | str] = None,
    synthesis_type: Optional[str] = None,
    kingdom: Optional[str] = None,
    uniprot: Optional[str] = None,
    dbaasp_id: Optional[int | str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search/filter DBAASP antimicrobial peptides by sequence (exact/substring), peptide name, target o...

    Parameters
    ----------
    sequence : str
        Amino-acid sequence to match (single-letter code). Pair with sequence_option ...
    sequence_option : str
        How to match 'sequence': 'full' (exact, default) or 'part' (substring). Maps ...
    name : str
        Peptide name substring. Example: 'Magainin'.
    target_species : str
        Target organism / species name. Example: 'Staphylococcus aureus'. Maps to tar...
    target_group : str
        Target group (e.g. 'Gram+', 'Gram-'). Maps to targetGroup.value.
    sequence_length : int | str
        Exact peptide length filter. Maps to sequenceLength.value.
    synthesis_type : str
        Synthesis type, e.g. 'Ribosomal', 'Synthetic'. Maps to synthesisType.value.
    kingdom : str
        Source kingdom/taxonomy filter. Maps to kingdom.value.
    uniprot : str
        UniProt accession cross-reference. Maps to uniprot.value.
    dbaasp_id : int | str
        DBAASP numeric ID filter. Maps to id.value.
    limit : int
        Max results to return (default 25).
    offset : int
        Result offset for pagination (default 0).
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
            "sequence": sequence,
            "sequence_option": sequence_option,
            "name": name,
            "target_species": target_species,
            "target_group": target_group,
            "sequence_length": sequence_length,
            "synthesis_type": synthesis_type,
            "kingdom": kingdom,
            "uniprot": uniprot,
            "dbaasp_id": dbaasp_id,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DBAASP_search_peptides",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DBAASP_search_peptides"]
