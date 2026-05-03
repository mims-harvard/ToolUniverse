#!/usr/bin/env python3
"""
Enhanced Multi-Agent Literature Search System
Uses MemoryManager for session-based memory management
"""

import json


def compose(
    arguments, tooluniverse, call_tool, stream_callback, emit_event, memory_manager
):
    """使用MemoryManager的enhanced multi-agent系统"""

    # 1. 创建或获取会话
    user_id = arguments.get("user_id", "anonymous")
    session_id = arguments.get("session_id")

    if not session_id:
        # 创建新会话
        session_id = memory_manager.create_session(
            user_id=user_id,
            session_name=f"Literature Search - {arguments['query'][:50]}",
        )
        emit_event("session_created", {"session_id": session_id, "user_id": user_id})
    else:
        # 使用现有会话
        session = memory_manager.get_session(session_id)
        if not session:
            # 会话不存在，创建新会话
            session_id = memory_manager.create_session(
                user_id=user_id,
                session_name=f"Literature Search - {arguments['query'][:50]}",
            )
            emit_event(
                "session_created", {"session_id": session_id, "user_id": user_id}
            )
        else:
            emit_event(
                "session_resumed", {"session_id": session_id, "user_id": user_id}
            )

    # 2. 更新会话上下文
    memory_manager.update_session_context(
        session_id,
        {"user_query": arguments["query"], "current_phase": "intent_analysis"},
    )

    # 3. 意图分析
    emit_event("phase_start", {"phase": "intent_analysis", "session_id": session_id})
    memory_manager.set_current_phase(session_id, "intent_analysis")

    intent_result = call_tool(
        "IntentAnalyzerAgent",
        {
            "user_query": arguments["query"],
            "context": memory_manager.get_context_for_agent(
                session_id, "IntentAnalyzerAgent"
            ),
        },
    )

    # 添加结果到记忆
    intent_data = _parse_result(intent_result)
    memory_manager.add_agent_result(
        session_id, "IntentAnalyzerAgent", intent_data, "intent_analysis"
    )

    user_intent = intent_data.get("user_intent", "")
    search_plans = intent_data.get("search_plans", [])

    emit_event(
        "intent_analysis_complete",
        {
            "user_intent": user_intent,
            "search_plans_count": len(search_plans),
            "session_id": session_id,
        },
    )

    # 4. 关键词提取和搜索
    emit_event("phase_start", {"phase": "parallel_search", "session_id": session_id})
    memory_manager.set_current_phase(session_id, "parallel_search")

    all_results = []
    for plan in search_plans:
        plan_id = f"plan_{len(all_results) + 1}"
        plan["plan_id"] = plan_id

        emit_event(
            "plan_search_start",
            {"plan_id": plan_id, "plan_title": plan["title"], "session_id": session_id},
        )

        # 关键词提取
        keywords_result = call_tool(
            "KeywordExtractorAgent",
            {
                "plan_title": plan["title"],
                "plan_description": plan["description"],
                "current_keywords": ", ".join(plan["keywords"]),
                "context": memory_manager.get_context_for_agent(
                    session_id, "KeywordExtractorAgent"
                ),
            },
        )

        keywords_data = _parse_result(keywords_result)
        memory_manager.add_agent_result(
            session_id, "KeywordExtractorAgent", keywords_data, "parallel_search"
        )

        refined_keywords = keywords_data.get("refined_keywords", plan["keywords"])

        # 搜索多个工具
        search_tools = [
            "ArXiv_search_papers",
            "PubMed_search_articles",
            "SemanticScholar_search_papers",
        ]
        plan_papers = []

        for i, tool_name in enumerate(search_tools):
            if i < len(refined_keywords):
                keyword = refined_keywords[i]
            else:
                keyword = refined_keywords[0]

            emit_event(
                "tool_search_start",
                {
                    "tool": tool_name,
                    "keyword": keyword,
                    "plan_id": plan_id,
                    "session_id": session_id,
                },
            )

            try:
                search_result = call_tool(tool_name, {"query": keyword})

                if isinstance(search_result, dict) and search_result.get("success"):
                    papers = search_result.get("result", [])
                    for paper in papers[:2]:
                        emit_event(
                            "paper_found",
                            {
                                "paper": paper,
                                "tool": tool_name,
                                "keyword": keyword,
                                "plan_id": plan_id,
                                "session_id": session_id,
                            },
                        )
                        plan_papers.append(paper)

                emit_event(
                    "tool_search_complete",
                    {
                        "tool": tool_name,
                        "keyword": keyword,
                        "papers_found": len(plan_papers),
                        "plan_id": plan_id,
                        "session_id": session_id,
                    },
                )

            except Exception as e:
                emit_event(
                    "tool_search_error",
                    {
                        "tool": tool_name,
                        "error": str(e),
                        "plan_id": plan_id,
                        "session_id": session_id,
                    },
                )

        # 结果总结
        if plan_papers:
            papers_text = _format_papers_for_summary(plan_papers)

            summary_result = call_tool(
                "ResultSummarizerAgent",
                {
                    "plan_title": plan["title"],
                    "plan_description": plan["description"],
                    "paper_count": str(len(plan_papers)),
                    "papers_text": papers_text,
                    "context": memory_manager.get_context_for_agent(
                        session_id, "ResultSummarizerAgent"
                    ),
                },
            )

            plan["summary"] = _parse_result(summary_result)
            memory_manager.add_agent_result(
                session_id, "ResultSummarizerAgent", plan["summary"], "parallel_search"
            )

        plan["results"] = plan_papers
        all_results.extend(plan_papers)

        emit_event(
            "plan_search_complete",
            {
                "plan_id": plan_id,
                "papers_found": len(plan_papers),
                "session_id": session_id,
            },
        )

    # 5. 生成总体总结
    emit_event("phase_start", {"phase": "overall_summary", "session_id": session_id})
    memory_manager.set_current_phase(session_id, "overall_summary")

    plan_summaries = "\n\n".join(
        [
            f"## {plan['title']}\n{plan.get('summary', 'No summary available.')}"
            for plan in search_plans
            if plan.get("summary")
        ]
    )

    overall_summary_result = call_tool(
        "OverallSummaryAgent",
        {
            "user_query": arguments["query"],
            "user_intent": user_intent,
            "total_papers": str(len(all_results)),
            "total_plans": str(len(search_plans)),
            "iterations": "1",
            "plan_summaries": plan_summaries,
            "context": memory_manager.get_context_for_agent(
                session_id, "OverallSummaryAgent"
            ),
        },
    )

    overall_summary = _parse_result(overall_summary_result)
    memory_manager.add_agent_result(
        session_id, "OverallSummaryAgent", overall_summary, "overall_summary"
    )

    # 6. 完成事件
    emit_event(
        "search_complete",
        {
            "total_papers": len(all_results),
            "total_plans": len(search_plans),
            "overall_summary": overall_summary,
            "session_id": session_id,
        },
    )

    return {
        "success": True,
        "session_id": session_id,
        "results": {
            "user_intent": user_intent,
            "search_plans": search_plans,
            "overall_summary": overall_summary,
            "total_papers": len(all_results),
        },
    }


def _parse_result(result):
    """Parse tool result into a dict, unwrapping nested JSON strings."""
    if isinstance(result, str):
        try:
            parsed = json.loads(result)
            return parsed if isinstance(parsed, dict) else {"result": parsed}
        except Exception:
            return {"result": result}
    if isinstance(result, dict):
        # Unwrap nested JSON in "result" key (e.g. from agent tools)
        inner = result.get("result")
        if isinstance(inner, str):
            try:
                parsed = json.loads(inner)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
        return result
    return {"result": str(result)}


def _format_papers_for_summary(papers):
    """格式化论文用于总结"""
    if not papers:
        return "No papers found."

    formatted_papers = []
    for i, paper in enumerate(papers[:10], 1):
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
