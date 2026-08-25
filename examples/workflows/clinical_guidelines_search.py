#!/usr/bin/env python3
"""
Clinical Guidelines Search Workflow

Professional clinical guidelines search and analysis pipeline using multiple
sources for comprehensive evidence-based clinical decision support.
"""

from tooluniverse.tools import (
    NICE_Clinical_Guidelines_Search,
    PubMed_Guidelines_Search,
    EuropePMC_Guidelines_Search,
    OpenAlex_Guidelines_Search,
    TRIP_Database_Guidelines_Search,
    WHO_Guidelines_Search,
    GIN_Guidelines_Search,
    CMA_Guidelines_Search,
)


def _titles_similar(title1: str, title2: str, threshold: float = 0.8) -> bool:
    """
    Check if two titles are similar enough to be considered duplicates.
    
    Args:
        title1: First title (lowercase)
        title2: Second title (lowercase)
        threshold: Similarity threshold (0.0 to 1.0)
        
    Returns:
        bool: True if titles are similar enough
    """
    # Simple word-based similarity
    words1 = set(title1.split())
    words2 = set(title2.split())
    
    if not words1 or not words2:
        return False
    
    # Calculate Jaccard similarity
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    similarity = intersection / union if union > 0 else 0
    return similarity >= threshold


def is_valid_guideline(guideline: dict) -> bool:
    """
    Validate if a result is actually a clinical guideline.
    
    Args:
        guideline: Dictionary containing guideline information
        
    Returns:
        bool: True if it appears to be a valid clinical guideline
    """
    # Filter out known placeholders
    if guideline.get("is_placeholder"):
        return False

    note = guideline.get("note", "")
    if isinstance(note, str):
        note_lower = note.lower()
        if any(
            phrase in note_lower
            for phrase in [
                "temporarily unavailable",
                "try again later",
                "access failed",
                "visit g-i-n.net",
                "visit joulecma",
            ]
        ):
            return False

    # Basic metadata checks
    title_raw = str(guideline.get("title", "")).strip()
    if len(title_raw) < 10:
        return False

    url = str(guideline.get("url", "")).strip()
    if not url:
        return False

    title_lower = title_raw.lower()
    abstract_raw = str(guideline.get("abstract", ""))
    summary_raw = str(guideline.get("summary", ""))
    description_raw = str(guideline.get("description", ""))
    content_raw = str(guideline.get("content", ""))

    # Guard against search-result placeholders masquerading as guidelines
    if any(phrase in title_lower for phrase in ["guidelines search", "search for"]):
        return False

    # Require at least one substantial content field
    content_fields = [abstract_raw, summary_raw, description_raw, content_raw]
    has_substantive_content = any(
        isinstance(field, str) and len(field.strip()) >= 40 for field in content_fields
    )
    if not has_substantive_content:
        return False

    abstract = abstract_raw.lower()
    summary = summary_raw.lower()
    description = description_raw.lower()
    content = content_raw.lower()
    
    # Positive indicators
    guideline_keywords = [
        "guideline", "guidelines", "recommendation", "recommendations",
        "practice guideline", "clinical practice", "consensus",
        "position statement", "clinical guidance", "best practice"
    ]
    
    # Negative indicators (exclude these)
    exclude_keywords = [
        "preprint", "protocol", "study protocol", "trial protocol",
        "case report", "case series", "letter to editor", "editorial"
    ]
    
    # Check for positive indicators (must appear in meaningful content)
    text_sections = [title_lower, abstract, summary, description, content]
    keyword_hits = sum(
        1 for section in text_sections if any(keyword in section for keyword in guideline_keywords)
    )
    has_guideline_keywords = keyword_hits > 0
    
    # Check for negative indicators
    has_exclude_keywords = any(
        keyword in title_lower
        or keyword in abstract
        or keyword in summary
        or keyword in description
        or keyword in content
        for keyword in exclude_keywords
    )
    
    # Check publication type if available
    pub_type = guideline.get("publication_type", "").lower()
    is_guideline_type = "guideline" in pub_type or "practice guideline" in pub_type
    
    # Check if explicitly marked as guideline
    is_explicitly_guideline = guideline.get("is_guideline", False)

    # Additional metadata indicators
    category_text = str(guideline.get("category", "")).lower()
    type_text = str(guideline.get("type", "")).lower()
    has_metadata_indicator = (
        is_guideline_type
        or is_explicitly_guideline
        or "guideline" in category_text
        or "guideline" in type_text
    )

    # Require either strong metadata signal or guideline keywords present in
    # multiple sections to reduce false positives from generic abstracts
    has_redundant_keyword_support = keyword_hits >= 2

    if not has_guideline_keywords:
        return False

    if not (has_metadata_indicator or has_redundant_keyword_support):
        return False

    return not has_exclude_keywords


def enhance_search_query(query: str) -> str:
    """
    Enhance search query with medical terminology and guideline-specific terms.
    
    Args:
        query: Original search query
        
    Returns:
        str: Enhanced query with medical terms
    """
    # Add guideline-specific terms
    enhanced_query = (f"{query} AND (guideline OR guidelines OR recommendation OR "
                     f"recommendations OR practice guideline OR clinical practice OR "
                     f"consensus OR position statement)")
    
    # Add common medical terminology patterns
    if "diabetes" in query.lower():
        enhanced_query += (" AND (type 1 diabetes OR type 2 diabetes OR "
                          "diabetes mellitus)")
    elif "hypertension" in query.lower() or "blood pressure" in query.lower():
        enhanced_query += (" AND (hypertension OR high blood pressure OR "
                          "arterial hypertension)")
    elif "cancer" in query.lower() or "oncology" in query.lower():
        enhanced_query += (" AND (cancer OR neoplasm OR oncology OR "
                          "tumor OR tumour)")
    
    return enhanced_query


def clinical_guidelines_search_workflow(query: str, max_results_per_source: int = 5):
    """
    Comprehensive clinical guidelines search across multiple sources.

    Args:
        query: Search query for clinical guidelines
        max_results_per_source: Maximum results to retrieve per source

    Returns:
        dict: Structured results with guidelines from all sources and analysis
    """
    print("=== Clinical Guidelines Search Workflow ===")
    print(f"Original query: '{query}'")
    
    # Enhance the search query
    enhanced_query = enhance_search_query(query)
    print(f"Enhanced query: '{enhanced_query}'")

    results = {
        "query": query,
        "enhanced_query": enhanced_query,
        "sources": {},
        "total_guidelines": 0,
        "source_summary": {},
        "top_guidelines": [],
    }

    # Define search sources
    sources = [
        ("NICE", NICE_Clinical_Guidelines_Search, "UK Official Guidelines"),
        ("PubMed", PubMed_Guidelines_Search, "Peer-Reviewed Literature"),
        ("EuropePMC", EuropePMC_Guidelines_Search, "European Literature"),
        ("OpenAlex", OpenAlex_Guidelines_Search, "Open Academic Database"),
        ("TRIP", TRIP_Database_Guidelines_Search,
         "Evidence-Based Medicine Database"),
        ("WHO", WHO_Guidelines_Search, "World Health Organization"),
        ("GIN", GIN_Guidelines_Search, "International Guidelines Network"),
        ("CMA", CMA_Guidelines_Search, "Canadian Medical Association"),
    ]

    # Step 1: Search all sources
    print(f"\n1. Searching {len(sources)} guideline sources...")
    
    for source_name, search_function, description in sources:
        print(f"   Searching {source_name} ({description})...")
        
        try:
            # Use enhanced query for better results
            search_query = (enhanced_query if source_name in
                           ["PubMed", "EuropePMC", "OpenAlex", "TRIP"] else query)
            
            # Prepare arguments based on tool requirements
            if source_name == "PubMed":
                guidelines = search_function(
                    query=search_query,
                    limit=max_results_per_source,
                    api_key=""  # Use empty string as default
                )
            elif source_name == "OpenAlex":
                guidelines = search_function(
                    query=search_query,
                    limit=max_results_per_source,
                    year_from=2020,
                    year_to=2024
                )
            elif source_name == "TRIP":
                guidelines = search_function(
                    query=search_query,
                    limit=max_results_per_source,
                    search_type="guideline"
                )
            else:
                guidelines = search_function(
                    query=search_query,
                    limit=max_results_per_source
                )
            
            if guidelines:
                # Handle different response formats
                if isinstance(guidelines, list):
                    guideline_list = guidelines
                elif isinstance(guidelines, dict) and 'data' in guidelines:
                    # Sources that publish a match count return
                    # {"status", "data", "metadata"}; the rest return a list.
                    guideline_list = guidelines['data']
                elif isinstance(guidelines, dict) and 'guidelines' in guidelines:
                    guideline_list = guidelines['guidelines']
                elif isinstance(guidelines, dict) and 'results' in guidelines:
                    guideline_list = guidelines['results']
                else:
                    guideline_list = [guidelines] if guidelines else []
                
                # Filter for valid guidelines only
                valid_guidelines = [g for g in guideline_list
                                   if is_valid_guideline(g)]
                
                results["sources"][source_name] = {
                    "description": description,
                    "guidelines": valid_guidelines,
                    "count": len(valid_guidelines),
                    "total_found": len(guideline_list),
                    "filtered_out": len(guideline_list) - len(valid_guidelines)
                }
                results["total_guidelines"] += len(valid_guidelines)
                print(f"     Found {len(guideline_list)} results, "
                      f"{len(valid_guidelines)} valid guidelines")
            else:
                results["sources"][source_name] = {
                    "description": description,
                    "guidelines": [],
                    "count": 0
                }
                print(f"     No guidelines found")
                
        except Exception as e:
            print(f"     Error searching {source_name}: {str(e)}")
            results["sources"][source_name] = {
                "description": description,
                "guidelines": [],
                "count": 0,
                "error": str(e)
            }

    # Step 2: Analyze results by source
    print("\n2. Analyzing results by source...")
    for source_name, source_data in results["sources"].items():
        count = source_data["count"]
        results["source_summary"][source_name] = {
            "count": count,
            "description": source_data["description"],
            "success": count > 0 and "error" not in source_data
        }
        print(f"   {source_name}: {count} guidelines")

    # Step 3: Compile and deduplicate guidelines
    print("\n3. Compiling and deduplicating guidelines...")
    all_guidelines = []
    seen_titles = set()
    seen_dois = set()
    
    for source_name, source_data in results["sources"].items():
        for guideline in source_data["guidelines"]:
            # Standardize guideline format
            standardized = {
                "title": guideline.get("title", "Unknown Title"),
                "authors": guideline.get("authors", []),
                "year": guideline.get("year", "Unknown"),
                "doi": guideline.get("doi", ""),
                "url": guideline.get("url", ""),
                "source": source_name,
                "abstract": guideline.get("abstract", ""),
                "summary": guideline.get("summary", ""),
                "description": guideline.get("description", ""),
                "content": guideline.get("content", ""),
                "cited_by_count": guideline.get("cited_by_count", 0),
                "publication_type": guideline.get("publication_type", ""),
                "is_guideline": guideline.get("is_guideline", False),
                "key_recommendations": guideline.get("key_recommendations", []),
                "evidence_strength": guideline.get("evidence_strength", []),
            }
            
            # Simple deduplication based on title similarity and DOI
            title_lower = standardized["title"].lower()
            doi = standardized["doi"]
            
            # Check for duplicates
            is_duplicate = False
            if doi and doi in seen_dois:
                is_duplicate = True
            else:
                # Check for similar titles (basic similarity)
                for seen_title in seen_titles:
                    if _titles_similar(title_lower, seen_title):
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                all_guidelines.append(standardized)
                seen_titles.add(title_lower)
                if doi:
                    seen_dois.add(doi)

    # Sort by quality indicators: official source, guideline type, citations, year
    def guideline_quality_score(guideline):
        score = 0
        
        # Official sources get higher priority
        if guideline["source"] in ["NICE", "WHO"]:
            score += 80
        elif guideline["source"] in ["PubMed", "TRIP"]:
            score += 60
        elif guideline["source"] in ["EuropePMC", "OpenAlex"]:
            score += 30
        
        # Explicitly marked guidelines get bonus
        if guideline.get("is_guideline", False):
            score += 30

        # Publication type bonus
        pub_type = guideline.get("publication_type", "").lower()
        if "guideline" in pub_type:
            score += 20

        # Citation count (normalized)
        citations = guideline.get("cited_by_count", 0)
        score += min(citations, 50)  # Cap at 50 to avoid outliers

        # Structured recommendation bonus
        if guideline.get("key_recommendations"):
            score += 25
        if guideline.get("evidence_strength"):
            score += 10

        # Recent guidelines get slight bonus
        try:
            year = int(guideline.get("year", 0))
            if year >= 2020:
                score += 10
            elif year >= 2015:
                score += 5
        except (ValueError, TypeError):
            pass
            
        return score

    all_guidelines.sort(key=guideline_quality_score, reverse=True)
    
    results["top_guidelines"] = all_guidelines[:10]  # Top 10
    print(f"   Compiled {len(all_guidelines)} total guidelines")
    print(f"   Selected top {len(results['top_guidelines'])} guidelines")

    # Step 4: Generate summary statistics
    print("\n4. Generating summary statistics...")
    
    # Count by year
    year_counts = {}
    for guideline in all_guidelines:
        year = guideline["year"]
        if year != "Unknown":
            year_counts[year] = year_counts.get(year, 0) + 1
    
    # Count by source
    source_counts = {}
    for guideline in all_guidelines:
        source = guideline["source"]
        source_counts[source] = source_counts.get(source, 0) + 1
    
    results["summary_stats"] = {
        "total_guidelines": len(all_guidelines),
        "sources_used": len([s for s in results["sources"].values() if s["count"] > 0]),
        "year_distribution": dict(sorted(year_counts.items(), reverse=True)[:5]),
        "source_distribution": source_counts,
        "avg_citations": sum(g["cited_by_count"] for g in all_guidelines) / len(all_guidelines) if all_guidelines else 0
    }

    print(f"   Total guidelines: {results['summary_stats']['total_guidelines']}")
    print(f"   Sources with results: {results['summary_stats']['sources_used']}")
    print(f"   Average citations: {results['summary_stats']['avg_citations']:.1f}")

    print("\n=== Clinical Guidelines Search Workflow Complete ===")
    return results


if __name__ == "__main__":
    # Example usage
    results = clinical_guidelines_search_workflow(
        query="diabetes management",
        max_results_per_source=3
    )
    
    print("\nResults summary:")
    print(f"- Original query: {results['query']}")
    print(f"- Enhanced query: {results['enhanced_query']}")
    print(f"- Total guidelines found: {results['total_guidelines']}")
    print(f"- Sources searched: {len(results['sources'])}")
    print(f"- Top guidelines: {len(results['top_guidelines'])}")
    
    # Show filtering statistics
    total_found = sum(source.get('total_found', 0)
                      for source in results['sources'].values())
    total_filtered = sum(source.get('filtered_out', 0)
                         for source in results['sources'].values())
    print(f"- Total results before filtering: {total_found}")
    print(f"- Results filtered out: {total_filtered}")
    if total_found > 0:
        print(f"- Filtering rate: {(total_filtered/total_found*100):.1f}%")
    else:
        print("- Filtering rate: N/A")
    
    print("\nTop 3 guidelines:")
    for i, guideline in enumerate(results['top_guidelines'][:3], 1):
        print(f"{i}. {guideline['title']} ({guideline['source']}, "
              f"{guideline['year']})")
        snippet = (
            guideline.get('summary')
            or guideline.get('abstract')
            or guideline.get('description')
            or guideline.get('content')
        )
        if isinstance(snippet, str) and snippet:
            cleaned_snippet = snippet.replace('\n', ' ')
            print(f"   Summary: {cleaned_snippet[:180]}...")

        key_recs = guideline.get('key_recommendations') or []
        if key_recs:
            print("   Key recommendations:")
            for rec in key_recs[:2]:
                if isinstance(rec, dict):
                    rec_title = rec.get('title') or 'Recommendation'
                    rec_summary = (rec.get('summary') or '').replace('\n', ' ')
                    print(f"     - {rec_title}: {rec_summary[:160]}...")
                elif isinstance(rec, str):
                    print(f"     - {rec[:160]}...")

        strengths = guideline.get('evidence_strength') or []
        if strengths:
            strength_entries = []
            for item in strengths[:2]:
                if isinstance(item, dict):
                    strength_entries.append(item.get('strength') or item.get('section'))
                elif isinstance(item, str):
                    strength_entries.append(item)
            strength_entries = [entry for entry in strength_entries if entry]
            if strength_entries:
                print("   Evidence strength: " + "; ".join(strength_entries))
        print()
