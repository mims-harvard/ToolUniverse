"""
Output Summarization Composer Script

This script handles the intelligent summarization of tool outputs by:
1. Chunking large outputs into manageable pieces
2. Processing each chunk with AI-powered summarization
3. Merging the summarized chunks into a coherent final summary

The script leverages ToolUniverse's AgenticTool infrastructure to provide
intelligent, context-aware summarization that focuses on information
relevant to the original query.
"""

import logging
from typing import Dict, Any, List

# Set up logger for this module
logger = logging.getLogger("tooluniverse.output_summarizer")


def compose(arguments: Dict[str, Any], tooluniverse, call_tool) -> Dict[str, Any]:
    """
    Main composition function for output summarization.

    This function orchestrates the complete summarization workflow:
    - Chunks the input text into manageable pieces
    - Summarizes each chunk using AI
    - Merges the summaries into a final coherent result

    Args:
        arguments (Dict[str, Any]): Dictionary containing:
            - tool_output (str): The original tool output to be summarized
            - query_context (str): Context about the original query
            - tool_name (str): Name of the tool that generated the output
            - chunk_size (int, optional): Size of each chunk for processing
            - focus_areas (str, optional): Areas to focus on in summarization
            - max_summary_length (int, optional): Maximum length of final
              summary
        tooluniverse: ToolUniverse instance for tool execution
        call_tool: Function to call other tools within the composition

    Returns
        Dict[str, Any]: Dictionary containing:
            - success (bool): Whether summarization was successful
            - original_length (int): Length of original output
            - summary_length (int): Length of final summary
            - chunks_processed (int): Number of chunks processed
            - summary (str): The summarized output
            - tool_name (str): Name of the original tool
            - error (str, optional): Error message if summarization failed
    """
    try:
        # Extract and validate arguments
        tool_output = arguments.get("tool_output", "")
        query_context = arguments.get("query_context", "")
        tool_name = arguments.get("tool_name", "")
        chunk_size = arguments.get("chunk_size", 32000)
        focus_areas = arguments.get("focus_areas", "key_findings_and_results")
        max_summary_length = arguments.get("max_summary_length", 3000)

        # Basic numeric validation (be defensive: composer can be called directly)
        try:
            chunk_size = int(chunk_size)
        except Exception:
            chunk_size = 32000
        if chunk_size <= 0:
            chunk_size = 32000
        try:
            max_summary_length = int(max_summary_length)
        except Exception:
            max_summary_length = 3000
        if max_summary_length <= 0:
            max_summary_length = 3000

        # Validate required arguments
        if not tool_output:
            return {
                "success": False,
                "error": "tool_output is required",
                "original_output": "",
            }

        logger.info(f"🔍 Starting output summarization for {tool_name}")
        logger.info(f"📊 Original output length: {len(tool_output)} characters")

        # Decide whether summarization is needed based on summary budget, not chunking.
        # chunk_size controls chunking strategy; max_summary_length controls whether we
        # should compress at all.
        if len(tool_output) <= max_summary_length:
            logger.info(
                f"📝 Text fits within max_summary_length ({max_summary_length}), "
                f"no summarization needed"
            )
            return {
                "success": True,
                "original_length": len(tool_output),
                "summary_length": len(tool_output),
                "chunks_processed": 0,
                "summary": tool_output,
                "tool_name": tool_name,
            }

        # If the text is too long for the summary budget but still smaller than the
        # chunking threshold, summarize it in a single call (no chunking needed).
        if len(tool_output) <= chunk_size:
            logger.info(
                f"📝 Text shorter than chunk_size ({chunk_size}) but exceeds "
                f"max_summary_length ({max_summary_length}); summarizing in one shot"
            )
            one_shot = _summarize_chunk(
                tool_output,
                query_context,
                tool_name,
                focus_areas,
                call_tool,
                max_length=max_summary_length,
            )
            if one_shot:
                return {
                    "success": True,
                    "original_length": len(tool_output),
                    "summary_length": len(one_shot),
                    "chunks_processed": 1,
                    "summary": one_shot,
                    "tool_name": tool_name,
                }
            return {
                "success": False,
                "error": "One-shot summarization failed",
                "original_length": len(tool_output),
                "chunks_processed": 1,
                "original_output": tool_output,
                "tool_name": tool_name,
            }

        # Step 1: Chunk the output
        chunks = _chunk_output(tool_output, chunk_size)
        logger.info(f"📝 Split into {len(chunks)} chunks")

        # Step 2: Summarize each chunk
        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            logger.info(f"🤖 Processing chunk {i + 1}/{len(chunks)}")
            summary = _summarize_chunk(
                chunk, query_context, tool_name, focus_areas, call_tool
            )
            if summary:
                chunk_summaries.append(summary)
                logger.info(f"✅ Chunk {i + 1} summarized successfully")
            else:
                logger.warning(f"❌ Chunk {i + 1} summarization failed")

        # Step 3: Merge summaries (or gracefully fall back)
        if chunk_summaries:
            final_summary = _merge_summaries(
                chunk_summaries,
                query_context,
                tool_name,
                max_summary_length,
                call_tool,
            )
            logger.info(
                f"✅ Summarization completed. Final length: "
                f"{len(final_summary)} characters"
            )
            return {
                "success": True,
                "original_length": len(tool_output),
                "summary_length": len(final_summary),
                "chunks_processed": len(chunks),
                "summary": final_summary,
                "tool_name": tool_name,
            }
        else:
            # Treat as a non-fatal failure so upstream falls back to original
            # output
            logger.warning(
                "❌ No chunk summaries were generated. This usually indicates:"
            )
            logger.warning("   1. ToolOutputSummarizer tool is not available")
            logger.warning("   2. The output_summarization tools are not loaded")
            logger.warning("   3. There was an error in the summarization process")
            logger.warning(
                "   Please check that the SMCP server is started with hooks enabled."
            )
            return {
                "success": False,
                "error": "No chunk summaries generated",
                "original_length": len(tool_output),
                "chunks_processed": len(chunks),
                "original_output": tool_output,
                "tool_name": tool_name,
            }

    except Exception as e:
        error_msg = f"Error in output summarization: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {
            "success": False,
            "error": error_msg,
            "original_output": tool_output,
        }


def _chunk_output(text: str, chunk_size: int) -> List[str]:
    """
    Split text into chunks of specified size with intelligent boundary
    detection.

    This function attempts to break text at natural boundaries (sentences)
    to maintain coherence within chunks while respecting the size limit.

    Args:
        text (str): The text to be chunked
        chunk_size (int): Maximum size of each chunk

    Returns
        List[str]: List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings within the last 100 characters
            search_start = max(start + chunk_size - 100, start)
            for i in range(end, search_start, -1):
                if text[i] in ".!?":
                    end = i + 1
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end

    return chunks


def _summarize_chunk(
    chunk: str,
    query_context: str,
    tool_name: str,
    focus_areas: str,
    call_tool,
    max_length: int = 500,
) -> str:
    """
    Summarize a single chunk using the AgenticTool summarizer.

    Args:
        chunk (str): The text chunk to summarize
        query_context (str): Context about the original query
        tool_name (str): Name of the tool that generated the output
        focus_areas (str): Areas to focus on during summarization
        call_tool: Function to call the summarizer tool

    Returns
        str: Summarized chunk text, or empty string if summarization fails
    """
    try:
        logger.debug(
            f"🔍 Attempting to call ToolOutputSummarizer with chunk length: "
            f"{len(chunk)}"
        )
        result = call_tool(
            "ToolOutputSummarizer",
            {
                "tool_output": chunk,
                "query_context": query_context,
                "tool_name": tool_name,
                "focus_areas": focus_areas,
                "max_length": max_length,
            },
        )

        logger.debug(
            f"🔍 ToolOutputSummarizer returned: {type(result)} - {str(result)[:100]}..."
        )

        # Handle different result formats
        if isinstance(result, dict):
            if result.get("success"):
                return result.get("result", "")
            elif "result" in result and isinstance(result["result"], str):
                # ComposeTool._call_tool returns {'result': 'content'} format
                return result["result"]
            elif "error" in result and isinstance(result["error"], str):
                # Backward compatibility: ComposeTool._call_tool used to put
                # string results in error field. This workaround handles both
                # old and new behavior
                return result["error"]
            else:
                logger.warning(f"⚠️ ToolOutputSummarizer returned error: {result}")
                return ""
        elif isinstance(result, str):
            # When return_metadata=False and successful, AgenticTool returns
            # the string directly
            return result
        else:
            logger.warning(
                f"⚠️ ToolOutputSummarizer returned unexpected result format: "
                f"{type(result)}"
            )
            return ""

    except Exception as e:
        error_msg = str(e)
        logger.warning(f"⚠️ Error summarizing chunk: {error_msg}")

        # Check if the error is due to missing tool
        if "not found" in error_msg.lower() or "ToolOutputSummarizer" in error_msg:
            logger.warning(
                "❌ ToolOutputSummarizer tool is not available. This indicates "
                "the output_summarization tools are not loaded."
            )
            logger.warning(
                "   Please ensure the SMCP server is started with hooks "
                "enabled and the output_summarization category is loaded."
            )

        return ""


def _merge_summaries(
    chunk_summaries: List[str],
    query_context: str,
    tool_name: str,
    max_length: int,
    call_tool,
) -> str:
    """
    Merge chunk summaries into a final coherent summary.

    If the combined summaries exceed the maximum length, they are further
    summarized to create a concise final result.

    Args:
        chunk_summaries (List[str]): List of summarized chunks
        query_context (str): Context about the original query
        tool_name (str): Name of the tool that generated the output
        max_length (int): Maximum length of final summary
        call_tool: Function to call the summarizer tool

    Returns
        str: Final merged summary
    """
    if not chunk_summaries:
        return ""

    # If only one chunk, return it directly
    if len(chunk_summaries) == 1:
        return chunk_summaries[0]

    # Combine all chunk summaries
    combined_summaries = "\n\n".join(chunk_summaries)

    # If combined length is within limit, return as is
    if len(combined_summaries) <= max_length:
        return combined_summaries

    # Otherwise, summarize the combined summaries
    try:
        result = call_tool(
            "ToolOutputSummarizer",
            {
                "tool_output": combined_summaries,
                "query_context": query_context,
                "tool_name": tool_name,
                "focus_areas": "consolidate_and_prioritize",
                "max_length": max_length,
            },
        )

        # Handle different result formats
        if isinstance(result, dict) and result.get("success"):
            return result.get("result", combined_summaries)
        elif isinstance(result, str):
            return result
        else:
            return combined_summaries

    except Exception as e:
        logger.warning(f"⚠️ Error merging summaries: {str(e)}")
        return combined_summaries
