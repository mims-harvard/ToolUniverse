"""
Tests for AsyncPollingTool and AsyncStreamingTool base classes.
"""
import pytest
import asyncio
from unittest.mock import Mock
from tooluniverse.async_base import AsyncPollingTool, AsyncStreamingTool


# ============================================================================
# Test AsyncPollingTool
# ============================================================================

class MockPollingTool(AsyncPollingTool):
    """Mock tool for testing AsyncPollingTool base class."""

    name = "Mock_Polling_Tool"
    description = "Mock tool for testing"
    poll_interval = 0.1  # Fast polling for tests
    max_duration = 10

    parameter = {
        "type": "object",
        "properties": {
            "input": {"type": "string"}
        },
        "required": ["input"]
    }

    def __init__(self):
        super().__init__()
        self.submit_called = False
        self.check_count = 0
        self.status_sequence = []  # List of statuses to return

    def submit_job(self, arguments):
        """Mock job submission."""
        self.submit_called = True
        return "test_job_123"

    def check_status(self, job_id):
        """Mock status check with configurable sequence."""
        self.check_count += 1

        # Use sequence if available
        if len(self.status_sequence) > 0:
            return self.status_sequence.pop(0)

        # Default: complete immediately
        return {
            "done": True,
            "result": {"answer": 42},
            "progress": 100
        }


class TestAsyncPollingTool:
    """Test suite for AsyncPollingTool base class."""

    @pytest.mark.asyncio
    async def test_basic_execution(self):
        """Test basic successful execution."""
        tool = MockPollingTool()

        result = await tool.run({"input": "test"})

        print(f"Result: {result}")
        print(f"Submit called: {tool.submit_called}")
        print(f"Check count: {tool.check_count}")

        assert tool.submit_called
        assert tool.check_count >= 1
        assert "data" in result
        assert result["data"]["answer"] == 42

    @pytest.mark.asyncio
    async def test_polling_sequence(self):
        """Test multiple polling iterations."""
        tool = MockPollingTool()

        # Set up sequence: processing → processing → complete
        tool.status_sequence = [
            {"done": False, "progress": 30},
            {"done": False, "progress": 60},
            {"done": True, "result": {"answer": 42}, "progress": 100}
        ]

        result = await tool.run({"input": "test"})

        assert tool.check_count == 3
        assert result["data"]["answer"] == 42

    @pytest.mark.asyncio
    async def test_progress_reporting(self):
        """Test progress updates are called."""
        tool = MockPollingTool()
        tool.status_sequence = [
            {"done": False, "progress": 50},
            {"done": True, "result": {"answer": 42}, "progress": 100}
        ]

        # Mock progress
        mock_progress = Mock()
        progress_messages = []

        async def capture_progress(msg):
            progress_messages.append(msg)

        mock_progress.set_message = capture_progress

        _ = await tool.run({"input": "test"}, progress=mock_progress)

        # Should have progress updates
        assert len(progress_messages) >= 2
        assert any("Submitting" in msg for msg in progress_messages)
        assert any("Processing" in msg for msg in progress_messages)

    @pytest.mark.asyncio
    async def test_timeout(self):
        """Test timeout when job doesn't complete."""
        tool = MockPollingTool()
        tool.max_duration = 1  # 1 second timeout
        tool.poll_interval = 0.2

        # Always return not done
        tool.status_sequence = [{"done": False, "progress": 0}] * 100

        result = await tool.run({"input": "test"})

        # Should return error
        assert "error" in result
        assert "timed out" in result["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_job_error(self):
        """Test handling of job errors."""
        tool = MockPollingTool()
        tool.status_sequence = [
            {"done": False, "progress": 50},
            {"done": False, "progress": 75, "error": "Something went wrong"}
        ]

        result = await tool.run({"input": "test"})

        assert "error" in result
        assert "Something went wrong" in result["error"]["message"]

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test exception during execution."""
        tool = MockPollingTool()

        # Make submit_job raise exception
        def raise_error(arguments):
            raise ValueError("Invalid input")

        tool.submit_job = raise_error

        result = await tool.run({"input": "test"})

        assert "error" in result
        assert "Invalid input" in result["error"]["message"]
        assert result["error"]["error_type"] == "ValueError"

    @pytest.mark.asyncio
    async def test_custom_format_result(self):
        """Test custom result formatting."""

        class CustomFormattingTool(MockPollingTool):
            def format_result(self, result):
                return {
                    "data": {
                        "custom_field": result["answer"] * 2
                    },
                    "metadata": {
                        "tool": self.name
                    }
                }

        tool = CustomFormattingTool()
        result = await tool.run({"input": "test"})

        assert result["data"]["custom_field"] == 84
        assert result["metadata"]["tool"] == "Mock_Polling_Tool"

    def test_auto_generated_return_schema(self):
        """Test that return_schema is auto-generated."""
        tool = MockPollingTool()

        assert "oneOf" in tool.return_schema
        assert len(tool.return_schema["oneOf"]) == 2

        # Check success schema
        success_schema = tool.return_schema["oneOf"][0]
        assert "data" in success_schema["properties"]

        # Check error schema
        error_schema = tool.return_schema["oneOf"][1]
        assert "error" in error_schema["properties"]

    def test_batch_concurrency_limit(self):
        """Test default batch concurrency limit."""
        tool = MockPollingTool()
        assert tool.get_batch_concurrency_limit() == 3

    @pytest.mark.asyncio
    async def test_no_result_in_completion(self):
        """Test error when job completes without result."""
        tool = MockPollingTool()
        tool.status_sequence = [
            {"done": True}  # Done but no result!
        ]

        result = await tool.run({"input": "test"})

        assert "error" in result
        assert "no result" in result["error"]["message"].lower()


# ============================================================================
# Test AsyncStreamingTool
# ============================================================================

class MockStreamingTool(AsyncStreamingTool):
    """Mock tool for testing AsyncStreamingTool base class."""

    name = "Mock_Streaming_Tool"
    description = "Mock streaming tool"
    chunk_interval = 0.1
    max_duration = 10

    parameter = {
        "type": "object",
        "properties": {
            "query": {"type": "string"}
        },
        "required": ["query"]
    }

    def __init__(self):
        super().__init__()
        self.stream_started = False
        self.fetch_count = 0
        self.chunks_to_return = []  # List of chunks to return

    def start_stream(self, arguments):
        """Mock stream start."""
        self.stream_started = True
        return "stream_abc_123"

    def fetch_chunk(self, stream_id):
        """Mock chunk fetch."""
        self.fetch_count += 1

        if self.chunks_to_return:
            return self.chunks_to_return.pop(0)

        # Default: return final chunk
        return {"data": "final", "done": True}

    def is_complete(self, chunk):
        """Check if chunk indicates completion."""
        return chunk.get("done", False)


class TestAsyncStreamingTool:
    """Test suite for AsyncStreamingTool base class."""

    @pytest.mark.asyncio
    async def test_basic_streaming(self):
        """Test basic streaming execution."""
        tool = MockStreamingTool()

        result = await tool.run({"query": "test"})

        assert tool.stream_started
        assert tool.fetch_count >= 1
        assert "data" in result
        assert "chunks" in result["data"]

    @pytest.mark.asyncio
    async def test_multiple_chunks(self):
        """Test streaming multiple chunks."""
        tool = MockStreamingTool()
        tool.chunks_to_return = [
            {"data": "chunk1", "done": False},
            {"data": "chunk2", "done": False},
            {"data": "chunk3", "done": True}
        ]

        result = await tool.run({"query": "test"})

        assert tool.fetch_count == 3
        assert len(result["data"]["chunks"]) == 3
        assert result["data"]["total"] == 3

    @pytest.mark.asyncio
    async def test_streaming_with_progress(self):
        """Test progress updates during streaming."""
        tool = MockStreamingTool()
        tool.chunks_to_return = [
            {"data": "chunk1", "done": False},
            {"data": "chunk2", "done": False},
            {"data": "chunk3", "done": True}
        ]

        # Mock progress
        mock_progress = Mock()
        progress_messages = []

        async def capture_progress(msg):
            progress_messages.append(msg)

        mock_progress.set_message = capture_progress

        _ = await tool.run({"query": "test"}, progress=mock_progress)

        # Should have progress updates
        assert len(progress_messages) >= 2
        assert any("Starting" in msg for msg in progress_messages)
        assert any("chunks" in msg.lower() for msg in progress_messages)

    @pytest.mark.asyncio
    async def test_streaming_timeout(self):
        """Test timeout for long streams."""
        tool = MockStreamingTool()
        tool.max_duration = 0.5
        tool.chunk_interval = 0.2

        # Never complete
        tool.chunks_to_return = [{"data": f"chunk{i}", "done": False} for i in range(100)]

        result = await tool.run({"query": "test"})

        assert "error" in result
        assert "timed out" in result["error"]["message"].lower()


# ============================================================================
# Integration Tests
# ============================================================================

class TestBaseClassIntegration:
    """Integration tests for base classes."""

    @pytest.mark.asyncio
    async def test_multiple_parallel_executions(self):
        """Test running multiple instances in parallel."""
        tools = [MockPollingTool() for _ in range(3)]

        # Each tool returns different result
        for i, tool in enumerate(tools):
            tool.status_sequence = [
                {"done": True, "result": {"answer": i * 10}, "progress": 100}
            ]

        # Run all in parallel
        results = await asyncio.gather(
            tools[0].run({"input": "test1"}),
            tools[1].run({"input": "test2"}),
            tools[2].run({"input": "test3"})
        )

        assert len(results) == 3
        assert results[0]["data"]["answer"] == 0
        assert results[1]["data"]["answer"] == 10
        assert results[2]["data"]["answer"] == 20

    @pytest.mark.asyncio
    async def test_exception_in_parallel_execution(self):
        """Test one failure doesn't affect others."""
        tool1 = MockPollingTool()
        tool2 = MockPollingTool()
        tool3 = MockPollingTool()

        # Tool 2 will fail
        def raise_error(arguments):
            raise RuntimeError("Tool 2 failed")

        tool2.submit_job = raise_error

        # Run all in parallel with exception handling
        results = await asyncio.gather(
            tool1.run({"input": "test1"}),
            tool2.run({"input": "test2"}),
            tool3.run({"input": "test3"}),
            return_exceptions=False  # Let exceptions become error dicts
        )

        # Tool 1 and 3 succeeded
        assert "data" in results[0]
        assert results[0]["data"]["answer"] == 42

        # Tool 2 failed
        assert "error" in results[1]
        assert "Tool 2 failed" in results[1]["error"]["message"]

        # Tool 3 succeeded
        assert "data" in results[2]
        assert results[2]["data"]["answer"] == 42


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
