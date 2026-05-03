"""
Multi-Agent Literature Search Compose Function
==============================================

This module implements the compose function for the multi-agent literature search system.
"""

import json
from datetime import datetime


def _format_papers_for_summary_v2(papers):
    """Format papers for summary generation"""
    if not papers:
        return "No papers found."

    formatted_papers = []
    for i, paper in enumerate(papers[:10], 1):  # Limit to first 10 papers
        title = paper.get("title", "No title")
        abstract = paper.get("abstract", "No abstract available")
        authors = paper.get("authors", [])
        year = paper.get("year", "Unknown year")
        venue = paper.get("venue", paper.get("journal", "Unknown venue"))

        authors_str = ", ".join(authors) if authors else "Unknown authors"

        formatted_paper = f"""
{i}. **{title}**
   Authors: {authors_str}
   Year: {year}
   Venue: {venue}
   Abstract: {abstract[:200]}{"..." if len(abstract) > 200 else ""}
"""
        formatted_papers.append(formatted_paper)

    return "\n".join(formatted_papers)


def compose(arguments, tooluniverse, call_tool, stream_callback=None):
    """
    Multi-agent literature search compose function

    Args:
        arguments (dict): Input parameters from the tool call
        tooluniverse (ToolUniverse): Reference to the ToolUniverse instance
        call_tool (function): Function to call other tools
        stream_callback (callable, optional): Callback function for streaming output

    Returns
        dict: The result of the multi-agent search
    """
    query = arguments.get("query", "")
    max_iterations = arguments.get("max_iterations", 3)
    quality_threshold = arguments.get("quality_threshold", 0.7)

    # 确保工具已加载
    print("🔧 确保工具已加载...")
    try:
        if hasattr(tooluniverse, "force_full_discovery"):
            tooluniverse.force_full_discovery()
        if hasattr(tooluniverse, "load_tools"):
            tooluniverse.load_tools()
        print("✅ 工具加载完成")
    except Exception as e:
        print(f"⚠️ 工具加载失败: {e}")

    if not query:
        return {"success": False, "error": "Query parameter is required"}

    # Helper function to emit stream events
    def emit_event(event_type, data=None):
        if stream_callback:
            event = {
                "type": event_type,
                "timestamp": datetime.now().isoformat(),
                "data": data or {},
            }
            stream_callback(json.dumps(event) + "\n")

    print(f"🚀 Starting Multi-Agent Literature Search for: '{query}'")
    print("=" * 60)

    # Emit start event
    emit_event("search_start", {"query": query, "max_iterations": max_iterations})

    try:
        # Step 1: Analyze intent and create search plans
        print("🤖 Step 1: Analyzing user intent...")
        emit_event(
            "agent_start", {"agent": "IntentAnalyzerAgent", "step": "intent_analysis"}
        )

        intent_result = call_tool("IntentAnalyzerAgent", {"user_query": query})

        print(f"🔍 IntentAnalyzerAgent raw result: {intent_result}")
        print(f"🔍 IntentAnalyzerAgent result type: {type(intent_result)}")

        # Handle both string and dict results
        if isinstance(intent_result, str):
            print(f"🔍 Parsing string result: {intent_result[:200]}...")
            try:
                intent_result = json.loads(intent_result)
                print(f"🔍 Parsed successfully: {intent_result}")
            except json.JSONDecodeError as e:
                print(f"❌ JSON parse error: {e}")
                emit_event(
                    "agent_error",
                    {"agent": "IntentAnalyzerAgent", "error": "Invalid JSON response"},
                )
                return {
                    "success": False,
                    "error": f"Intent analysis failed: Invalid JSON response - {intent_result}",
                }

        print(f"🔍 Final intent_result: {intent_result}")

        if not intent_result.get("success"):
            print(
                f"❌ Intent analysis failed: {intent_result.get('error', 'Unknown error')}"
            )
            emit_event(
                "agent_error",
                {
                    "agent": "IntentAnalyzerAgent",
                    "error": intent_result.get("error", "Unknown error"),
                },
            )
            return {
                "success": False,
                "error": f"Intent analysis failed: {intent_result.get('error', 'Unknown error')}",
            }

        content = intent_result.get("result", "{}")
        print(f"🔍 Content to parse: {content}")

        try:
            analysis = json.loads(content)
            print(f"🔍 Parsed analysis: {analysis}")
        except json.JSONDecodeError as e:
            print(f"❌ Analysis JSON parse error: {e}")
            analysis = {}

        user_intent = analysis.get("user_intent", "")
        search_plans_data = analysis.get("search_plans", [])

        print(f"🔍 User intent: '{user_intent}'")
        print(f"🔍 Search plans data: {search_plans_data}")

        print(f"✅ User Intent: {user_intent}")
        print(f"📋 Created {len(search_plans_data)} search plans")

        emit_event(
            "agent_complete",
            {
                "agent": "IntentAnalyzerAgent",
                "user_intent": user_intent,
                "plans_count": len(search_plans_data),
            },
        )

        # Initialize search plans
        search_plans = []
        for i, plan_data in enumerate(search_plans_data):
            plan = {
                "plan_id": f"plan_{i + 1}",
                "title": plan_data.get("title", ""),
                "description": plan_data.get("description", ""),
                "keywords": plan_data.get("keywords", []),
                "priority": plan_data.get("priority", 1),
                "status": "pending",
                "results": [],
                "summary": "",
                "quality_score": 0.0,
            }
            search_plans.append(plan)

        # Iterative search process
        current_iteration = 0
        is_complete = False

        emit_event(
            "plans_created",
            {
                "plans": [
                    {"id": p["plan_id"], "title": p["title"]} for p in search_plans
                ]
            },
        )

        while not is_complete and current_iteration < max_iterations:
            current_iteration += 1
            print(f"\n🔄 Iteration {current_iteration}")
            print("-" * 40)

            emit_event(
                "iteration_start",
                {"iteration": current_iteration, "max_iterations": max_iterations},
            )

            # Step 2: Extract keywords for pending plans
            pending_plans = [p for p in search_plans if p["status"] == "pending"]
            for plan in pending_plans:
                print(f"🔍 Extracting keywords for '{plan['title']}'")

                emit_event(
                    "agent_start",
                    {
                        "agent": "KeywordExtractorAgent",
                        "plan_id": plan["plan_id"],
                        "plan_title": plan["title"],
                    },
                )

                keywords_result = call_tool(
                    "KeywordExtractorAgent",
                    {
                        "plan_title": plan["title"],
                        "plan_description": plan["description"],
                        "current_keywords": ", ".join(plan["keywords"]),
                    },
                )

                # Handle both string and dict results
                if isinstance(keywords_result, str):
                    try:
                        keywords_result = json.loads(keywords_result)
                    except json.JSONDecodeError:
                        emit_event(
                            "agent_error",
                            {
                                "agent": "KeywordExtractorAgent",
                                "plan_id": plan["plan_id"],
                                "error": "Invalid JSON response",
                            },
                        )
                        continue

                if keywords_result.get("success"):
                    refined_data = json.loads(keywords_result.get("result", "{}"))
                    plan["keywords"] = refined_data.get(
                        "refined_keywords", plan["keywords"]
                    )
                    print(f"✅ Refined keywords: {plan['keywords']}")

                    emit_event(
                        "agent_complete",
                        {
                            "agent": "KeywordExtractorAgent",
                            "plan_id": plan["plan_id"],
                            "keywords": plan["keywords"],
                        },
                    )
                else:
                    emit_event(
                        "agent_error",
                        {
                            "agent": "KeywordExtractorAgent",
                            "plan_id": plan["plan_id"],
                            "error": "Keyword extraction failed",
                        },
                    )

            # Step 3: Execute parallel searches
            print("🔎 Executing parallel searches...")
            emit_event("search_start", {"plans_count": len(pending_plans)})

            for plan in pending_plans:
                plan["status"] = "in_progress"
                all_results = []

                emit_event(
                    "plan_search_start",
                    {"plan_id": plan["plan_id"], "plan_title": plan["title"]},
                )

                # Search each keyword
                for keyword in plan["keywords"]:
                    print(f"  Searching: {keyword}")

                    # Try multiple literature search tools
                    search_tools = [
                        "ArXiv_search_papers",
                        "PubMed_search_articles",
                        "EuropePMC_search_articles",
                        "SemanticScholar_search_papers",
                        "openalex_literature_search",
                    ]

                    for tool_name in search_tools:
                        try:
                            emit_event(
                                "tool_search_start",
                                {
                                    "tool": tool_name,
                                    "keyword": keyword,
                                    "plan_id": plan["plan_id"],
                                },
                            )

                            search_result = call_tool(
                                tool_name, {"query": keyword, "limit": 2}
                            )

                            print(
                                f"    🔍 {tool_name} result type: {type(search_result)}"
                            )
                            print(f"    🔍 {tool_name} result: {search_result}")

                            # Handle different return formats
                            papers = []
                            if isinstance(search_result, list):
                                # Most literature search tools return arrays directly
                                papers = search_result
                            elif isinstance(search_result, dict):
                                if search_result.get("success"):
                                    papers = search_result.get("papers", [])
                                elif search_result.get("results"):
                                    papers = search_result.get("results", [])
                                elif "error" in search_result:
                                    print(
                                        f"    ⚠️ {tool_name} returned error: {search_result.get('error')}"
                                    )
                                    papers = []
                            elif isinstance(search_result, str):
                                try:
                                    parsed = json.loads(search_result)
                                    if isinstance(parsed, list):
                                        papers = parsed
                                    elif isinstance(parsed, dict):
                                        papers = parsed.get(
                                            "papers", parsed.get("results", [])
                                        )
                                except json.JSONDecodeError:
                                    print(
                                        f"    ⚠️ {tool_name} returned invalid JSON string"
                                    )
                                    papers = []

                            if papers:
                                all_results.extend(papers[:2])  # Limit per tool

                                # Emit individual paper events for real-time display
                                for paper in papers[:2]:
                                    emit_event(
                                        "paper",
                                        {
                                            "paper": paper,
                                            "tool": tool_name,
                                            "keyword": keyword,
                                            "plan_id": plan["plan_id"],
                                        },
                                    )

                                emit_event(
                                    "tool_search_complete",
                                    {
                                        "tool": tool_name,
                                        "keyword": keyword,
                                        "plan_id": plan["plan_id"],
                                        "papers_found": len(papers[:2]),
                                    },
                                )
                                break  # Found results, move to next keyword
                            else:
                                emit_event(
                                    "tool_search_complete",
                                    {
                                        "tool": tool_name,
                                        "keyword": keyword,
                                        "plan_id": plan["plan_id"],
                                        "papers_found": 0,
                                    },
                                )
                        except Exception as e:
                            print(f"    ⚠️ {tool_name} failed: {e}")
                            emit_event(
                                "tool_search_error",
                                {
                                    "tool": tool_name,
                                    "keyword": keyword,
                                    "plan_id": plan["plan_id"],
                                    "error": str(e),
                                },
                            )
                            continue

                plan["results"] = all_results
                plan["status"] = "completed"
                print(f"✅ Found {len(all_results)} results for '{plan['title']}'")

                emit_event(
                    "plan_search_complete",
                    {
                        "plan_id": plan["plan_id"],
                        "plan_title": plan["title"],
                        "papers_found": len(all_results),
                    },
                )

            # Step 4: Summarize results
            print("📝 Summarizing results...")
            emit_event(
                "summarization_start",
                {
                    "plans_count": len(
                        [
                            p
                            for p in search_plans
                            if p["status"] == "completed" and not p["summary"]
                        ]
                    )
                },
            )

            for plan in search_plans:
                if plan["status"] == "completed" and not plan["summary"]:
                    papers_text = _format_papers_for_summary_v2(plan["results"])

                    emit_event(
                        "agent_start",
                        {
                            "agent": "ResultSummarizerAgent",
                            "plan_id": plan["plan_id"],
                            "plan_title": plan["title"],
                        },
                    )

                    summary_result = call_tool(
                        "ResultSummarizerAgent",
                        {
                            "plan_title": plan["title"],
                            "plan_description": plan["description"],
                            "paper_count": str(len(plan["results"])),
                            "papers_text": papers_text,
                        },
                    )

                    # Handle both string and dict results
                    if isinstance(summary_result, str):
                        # ResultSummarizerAgent returns string directly when return_json=false
                        plan["summary"] = summary_result
                        print(f"✅ Generated summary for '{plan['title']}'")

                        emit_event(
                            "agent_complete",
                            {
                                "agent": "ResultSummarizerAgent",
                                "plan_id": plan["plan_id"],
                                "summary_length": len(plan["summary"]),
                            },
                        )
                    elif isinstance(summary_result, dict):
                        if summary_result.get("success"):
                            plan["summary"] = summary_result.get(
                                "result", "Summary generation failed."
                            )
                            print(f"✅ Generated summary for '{plan['title']}'")

                            emit_event(
                                "agent_complete",
                                {
                                    "agent": "ResultSummarizerAgent",
                                    "plan_id": plan["plan_id"],
                                    "summary_length": len(plan["summary"]),
                                },
                            )
                        else:
                            emit_event(
                                "agent_error",
                                {
                                    "agent": "ResultSummarizerAgent",
                                    "plan_id": plan["plan_id"],
                                    "error": "Summary generation failed",
                                },
                            )
                    else:
                        emit_event(
                            "agent_error",
                            {
                                "agent": "ResultSummarizerAgent",
                                "plan_id": plan["plan_id"],
                                "error": "Unexpected result type",
                            },
                        )

            # Step 5: Check quality and decide next steps
            print("🔍 Checking result quality...")
            emit_event("quality_check_start", {"iteration": current_iteration})

            # Calculate quality scores
            for plan in search_plans:
                plan["quality_score"] = _calculate_quality_score(plan)

            avg_quality = (
                sum(plan["quality_score"] for plan in search_plans) / len(search_plans)
                if search_plans
                else 0.0
            )
            print(f"📊 Average quality score: {avg_quality:.2f}")

            emit_event(
                "quality_check_complete",
                {
                    "avg_quality": avg_quality,
                    "quality_threshold": quality_threshold,
                    "iteration": current_iteration,
                },
            )

            if avg_quality >= quality_threshold:
                is_complete = True
                print("✅ Quality threshold met. Search complete!")
                emit_event(
                    "search_complete",
                    {"reason": "quality_threshold_met", "avg_quality": avg_quality},
                )
            else:
                if current_iteration < max_iterations:
                    print("🔄 Quality below threshold. Planning next iteration...")

                    emit_event(
                        "agent_start",
                        {"agent": "QualityCheckerAgent", "step": "quality_improvement"},
                    )

                    # Get improvement suggestions
                    plans_analysis = _format_plans_for_analysis(search_plans)
                    improvement_result = call_tool(
                        "QualityCheckerAgent", {"plans_analysis": plans_analysis}
                    )

                    # Handle both string and dict results
                    if isinstance(improvement_result, str):
                        try:
                            improvement_result = json.loads(improvement_result)
                        except json.JSONDecodeError:
                            emit_event(
                                "agent_error",
                                {
                                    "agent": "QualityCheckerAgent",
                                    "error": "Invalid JSON response",
                                },
                            )
                            continue

                    if improvement_result.get("success"):
                        improvement_data = json.loads(
                            improvement_result.get("result", "{}")
                        )
                        _apply_improvements(search_plans, improvement_data)

                        emit_event(
                            "agent_complete",
                            {
                                "agent": "QualityCheckerAgent",
                                "improvements_applied": len(
                                    improvement_data.get("improvements", [])
                                ),
                                "new_plans": len(improvement_data.get("new_plans", [])),
                            },
                        )
                    else:
                        emit_event(
                            "agent_error",
                            {
                                "agent": "QualityCheckerAgent",
                                "error": "Quality improvement failed",
                            },
                        )
                else:
                    print(
                        "⚠️ Max iterations reached. Search complete with current results."
                    )
                    is_complete = True
                    emit_event(
                        "search_complete",
                        {
                            "reason": "max_iterations_reached",
                            "avg_quality": avg_quality,
                        },
                    )

        # Step 6: Generate overall summary
        print("\n📊 Generating overall summary...")
        emit_event(
            "overall_summary_start",
            {"total_papers": sum(len(plan["results"]) for plan in search_plans)},
        )

        plan_summaries = _format_plan_summaries(search_plans)
        total_papers = sum(len(plan["results"]) for plan in search_plans)

        emit_event(
            "agent_start", {"agent": "OverallSummaryAgent", "step": "overall_summary"}
        )

        overall_summary_result = call_tool(
            "OverallSummaryAgent",
            {
                "user_query": query,
                "user_intent": user_intent,
                "total_papers": str(total_papers),
                "total_plans": str(len(search_plans)),
                "iterations": str(current_iteration),
                "plan_summaries": plan_summaries,
            },
        )

        # Handle both string and dict results
        if isinstance(overall_summary_result, str):
            try:
                overall_summary_result = json.loads(overall_summary_result)
            except json.JSONDecodeError:
                emit_event(
                    "agent_error",
                    {"agent": "OverallSummaryAgent", "error": "Invalid JSON response"},
                )
                overall_summary_result = {
                    "success": False,
                    "error": "Invalid JSON response",
                }

        overall_summary = ""
        if overall_summary_result.get("success"):
            overall_summary = overall_summary_result.get(
                "result", "Overall summary generation failed."
            )
            emit_event(
                "agent_complete",
                {
                    "agent": "OverallSummaryAgent",
                    "summary_length": len(overall_summary),
                },
            )
        else:
            emit_event(
                "agent_error",
                {
                    "agent": "OverallSummaryAgent",
                    "error": "Overall summary generation failed",
                },
            )

        print("\n" + "=" * 60)
        print("🎉 Multi-Agent Search Complete!")
        print(f"📊 Total Papers Found: {total_papers}")
        print(f"📋 Plans Executed: {len(search_plans)}")
        print(f"🔄 Iterations: {current_iteration}")

        emit_event(
            "search_final_complete",
            {
                "total_papers": total_papers,
                "total_plans": len(search_plans),
                "iterations": current_iteration,
                "avg_quality": avg_quality,
            },
        )

        # Format final results
        all_papers = []
        for plan in search_plans:
            all_papers.extend(plan["results"])

        return {
            "success": True,
            "results": {
                "papers": all_papers,
                "total_papers": total_papers,
                "plan_summaries": _create_plan_summaries(search_plans),
                "overall_summary": overall_summary,
                "search_metadata": {
                    "user_intent": user_intent,
                    "total_plans": len(search_plans),
                    "iterations": current_iteration,
                    "is_complete": is_complete,
                    "avg_quality_score": avg_quality,
                },
            },
        }

    except Exception as e:
        return {"success": False, "error": f"Multi-agent search failed: {str(e)}"}


def _calculate_quality_score(plan):
    """Calculate quality score for a search plan"""
    if not plan["results"]:
        return 0.0

    result_count = len(plan["results"])
    has_recent_papers = any(paper.get("year", 0) >= 2020 for paper in plan["results"])
    has_abstracts = any(paper.get("abstract") for paper in plan["results"])

    score = 0.0

    # Result count score (0-0.4)
    if result_count >= 10:
        score += 0.4
    elif result_count >= 5:
        score += 0.3
    elif result_count >= 2:
        score += 0.2
    else:
        score += 0.1

    # Recent papers score (0-0.3)
    if has_recent_papers:
        score += 0.3

    # Abstract availability score (0-0.3)
    if has_abstracts:
        score += 0.3

    return min(score, 1.0)


def _format_plans_for_analysis(plans):
    """Format plans for quality analysis"""
    formatted = []
    for plan in plans:
        formatted.append(
            f"""
Plan: {plan["title"]}
Quality Score: {plan["quality_score"]:.2f}
Results Count: {len(plan["results"])}
Status: {plan["status"]}
"""
        )
    return "\n".join(formatted)


def _apply_improvements(plans, improvement_data):
    """Apply improvements to existing plans and add new plans"""
    # Apply improvements to existing plans
    for improvement in improvement_data.get("improvements", []):
        plan_id = improvement.get("plan_id")
        suggestions = improvement.get("suggestions", [])

        for plan in plans:
            if plan["plan_id"] == plan_id:
                # Add suggestions as new keywords
                plan["keywords"].extend(suggestions)
                plan["status"] = "pending"  # Reset status for re-search
                break

    # Add new plans
    for new_plan_data in improvement_data.get("new_plans", []):
        new_plan = {
            "plan_id": f"plan_{len(plans) + 1}",
            "title": new_plan_data.get("title", ""),
            "description": new_plan_data.get("description", ""),
            "keywords": new_plan_data.get("keywords", []),
            "priority": new_plan_data.get("priority", 1),
            "status": "pending",
            "results": [],
            "summary": "",
            "quality_score": 0.0,
        }
        plans.append(new_plan)


def _format_plan_summaries(plans):
    """Format plan summaries for overall summary generation"""
    summaries = []
    for plan in plans:
        if plan["summary"]:
            summaries.append(
                f"""
Plan: {plan["title"]}
Description: {plan["description"]}
Quality Score: {plan["quality_score"]:.2f}
Results: {len(plan["results"])} papers
Summary: {plan["summary"]}
"""
            )
    return "\n".join(summaries)


def _create_plan_summaries(plans):
    """Create structured plan summaries for return"""
    plan_summaries = []
    for plan in plans:
        if plan["summary"]:
            plan_summaries.append(
                {
                    "plan_title": plan["title"],
                    "plan_description": plan["description"],
                    "quality_score": plan["quality_score"],
                    "results_count": len(plan["results"]),
                    "summary": plan["summary"],
                }
            )
    return plan_summaries
