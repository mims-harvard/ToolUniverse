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

    # MedicalLiteratureReviewer is an AgenticTool, so it is skipped at load time when
    # no LLM API key is configured. Calling it anyway returns the string
    # "Invalid function call: ..." which the caller cannot distinguish from a real
    # review -- the tool reported success while producing nothing. Check first and
    # return the literature that was actually retrieved instead of discarding it.
    reviewer = "MedicalLiteratureReviewer"
    if reviewer not in tooluniverse.all_tool_dict:
        return {
            "success": False,
            "error": (
                f"Summarization step unavailable: '{reviewer}' is not loaded. It is an "
                "AgenticTool and requires an LLM API key (AZURE_OPENAI_API_KEY, "
                "OPENAI_API_KEY, OPENROUTER_API_KEY, GEMINI_API_KEY, or VLLM_SERVER_URL). "
                "The raw literature retrieved from EuropePMC, OpenAlex and PubTator is "
                "returned under 'literature' so the search results are not lost."
            ),
            "literature": literature,
        }

    summary = call_tool(
        reviewer,
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
