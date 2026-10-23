"""
civic_search_evidence_items

Search for curated CIViC evidence items. The tool follows CIViC's 100-record GraphQL pages up to ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def civic_search_evidence_items(
    limit: Optional[int] = 20,
    status: Optional[str] = None,
    therapy: Optional[str] = None,
    therapy_name: Optional[str] = None,
    disease: Optional[str] = None,
    disease_name: Optional[str] = None,
    molecular_profile: Optional[str] = None,
    evidence_type: Optional[str] = None,
    significance: Optional[str] = None,
    after: Optional[str] = None,
    evidence_direction: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search for curated CIViC evidence items. The tool follows CIViC's 100-record GraphQL pages up to ...

    Parameters
    ----------
    limit : int
        Maximum evidence items to return across server pages (default: 20, max: 1000).
    status : str
        Filter by curation status. Default: ACCEPTED (peer-reviewed). Options: ACCEPT...
    therapy : str
        Filter by therapy/drug name (e.g., 'imatinib', 'pembrolizumab'). Alias: thera...
    therapy_name : str
        Alias for therapy. Filter by therapy/drug name.
    disease : str
        Filter by disease name (e.g., 'leukemia', 'melanoma', 'lung cancer'). Alias: ...
    disease_name : str
        Alias for disease. Filter by disease name.
    molecular_profile : str
        Filter by molecular profile name (e.g., 'BRAF V600E', 'EGFR T790M', 'KRAS G12...
    evidence_type : str
        Filter by evidence type. Values: PREDICTIVE (drug response), DIAGNOSTIC (dise...
    significance : str
        Filter by clinical significance. Values depend on evidence_type, e.g. SENSITI...
    after : str
        Opaque CIViC continuation cursor from a previous pageInfo.endCursor.
    evidence_direction : str
        Filter by evidence direction.
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
    _args = {
        k: v
        for k, v in {
            "limit": limit,
            "status": status,
            "therapy": therapy,
            "therapy_name": therapy_name,
            "disease": disease,
            "disease_name": disease_name,
            "molecular_profile": molecular_profile,
            "evidence_type": evidence_type,
            "significance": significance,
            "after": after,
            "evidence_direction": evidence_direction,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "civic_search_evidence_items",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["civic_search_evidence_items"]
