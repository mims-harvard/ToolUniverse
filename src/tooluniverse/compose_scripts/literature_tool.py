"""
Literature Search & Summary Tool
Minimal compose tool perfect for paper screenshots
"""


def compose(arguments, tooluniverse, call_tool):
    """Search literature and generate summary"""
    topic = arguments["research_topic"]

    literature = {}
    literature["pmc"] = call_tool(
        "EuropePMC_search_articles", {"query": topic, "limit": 5}
    )
    literature["openalex"] = call_tool(
        "openalex_literature_search", {"search_keywords": topic, "max_results": 5}
    )
    literature["pubtator"] = call_tool(
        "PubTator3_LiteratureSearch", {"query": topic, "page_size": 5}
    )

    summary = call_tool(
        "MedicalLiteratureReviewer",
        {
            "research_topic": topic,
            "literature_content": str(literature),
            "focus_area": "key findings",
            "study_types": "all studies",
            "quality_level": "all evidence",
            "review_scope": "rapid review",
        },
    )

    return summary
