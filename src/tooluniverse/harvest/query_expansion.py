
from __future__ import annotations
from typing import List

DENTAL_SYNONYMS = [
    "oral health", "dentistry", "dental caries", "tooth decay",
    "periodontal", "periodontitis", "orthodontic", "endodontic",
    "prosthodontic", "oral cancer", "DMFT", "fluoride", "NIDCR", "CDC Oral Health",
    "WHO Oral Health"
]

def expand_queries(query: str, max_queries: int = 6) -> List[str]:
    base = query.strip()
    if not base:
        return []
    expanded = [base,
                f"{base} WHO API",
                f"{base} site:who.int",
                f"{base} site:data.cdc.gov",
                f"{base} site:api.fda.gov"]
    for syn in DENTAL_SYNONYMS[:4]:
        expanded.append(f"{base} {syn}")
    # de-dup and clip
    seen = []
    for q in expanded:
        if q not in seen:
            seen.append(q)
    return seen[:max_queries]
