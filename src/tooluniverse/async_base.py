"""
Base classes for async tool development.

Provides simplified base classes that handle common patterns like job polling,
progress reporting, and error handling automatically.
"""
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from .task_progress import TaskProgress
from .exceptions import ToolError


class AsyncPollingTool(ABC):
    """
    Base class for async tools that submit jobs and poll for completion.

    This class handles all the boilerplate: polling logic, progress reporting,
    timeout management, and error handling. Subclass and implement just 3 methods:

    1. submit_job() - Submit job and return job_id
    2. check_status() - Check if job is done and return result
    3. format_result() - Format the final result (optional)

    Example:
        class MyAPITool(AsyncPollingTool):
            name = "My_API_Tool"
            description = "Analyzes data (5-30 minutes)"
            poll_interval = 10
            max_duration = 3600

            parameter = {
                "type": "object",
                "properties": {
                    "input": {"type": "string"}
                },
                "required": ["input"]
            }

            def submit_job(self, arguments):
                response = requests.post("https://api.example.com/jobs", json=arguments)
                return response.json()["job_id"]

            def check_status(self, job_id):
                response = requests.get(f"https://api.example.com/jobs/{job_id}")
                data = response.json()
                return {
                    "done": data["status"] == "completed",
                    "result": data.get("result"),
                    "progress": data.get("progress", 0)
                }
    """

    # Subclass MUST set these
    name: str
    description: str
    parameter: dict

    # Optional configuration (subclass can override)
    poll_interval: int = 10  # seconds between status checks
    max_duration: int = 3600  # max seconds before timeout
    fields: dict = {"type": "REST"}

    def __init__(self):
        """Initialize tool with auto-generated return schema."""
        # Auto-generate return_schema following ToolUniverse conventions
        self.return_schema = self._generate_return_schema()

    @abstractmethod
    def submit_job(self, arguments: Dict[str, Any]) -> str:
        """
        Submit job to API and return job identifier.

        This is the only API-specific code you need to write!

        Args:
            arguments: Tool arguments dict

        Returns:
            job_id as string

        Example:
            def submit_job(self, arguments):
                response = requests.post(
                    "https://api.example.com/jobs",
                    json=arguments
                )
                return response.json()["job_id"]
        """
        pass

    @abstractmethod
    def check_status(self, job_id: str) -> Dict[str, Any]:
        """
        Check job status and return result if complete.

        This is the only polling-specific code you need to write!

        Args:
            job_id: Job identifier returned by submit_job()

        Returns:
            Dict with keys:
                - done (bool): True if job is complete
                - result (any): Job result if done (required if done=True)
                - progress (int): Progress percentage 0-100 (optional)
                - error (str): Error message if failed (optional)

        Example:
            def check_status(self, job_id):
                response = requests.get(f"https://api.example.com/jobs/{job_id}")
                data = response.json()
                return {
                    "done": data["status"] == "completed",
                    "result": data.get("result"),
                    "progress": data.get("progress", 0),
                    "error": data.get("error")
                }
        """
        pass

    def format_result(self, result: Any) -> Dict[str, Any]:
        """
        Format final result into ToolUniverse response format.

        Default implementation wraps result in {"data": {...}}.
        Override to customize result formatting.

        Args:
            result: Raw result from check_status()

        Returns:
            Formatted dict with {"data": {...}} structure

        Example:
            def format_result(self, result):
                return {
                    "data": {
                        "analysis": result["analysis"],
                        "score": result["score"]
                    },
                    "metadata": {
                        "tool": self.name,
                        "version": "1.0"
                    }
                }
        """
        if isinstance(result, dict):
            return {"data": result}
        return {"data": {"result": result}}

    async def run(
        self,
        arguments: Dict[str, Any],
        progress: Optional[TaskProgress] = None
    ) -> Dict[str, Any]:
        """
        Execute tool asynchronously (automatically implemented!).

        This method is automatically implemented by the base class.
        You don't need to write any of this code!

        It handles:
        1. Job submission
        2. Polling until complete
        3. Progress reporting
        4. Error handling
        5. Timeout management
        6. Result formatting

        Args:
            arguments: Tool arguments
            progress: Optional progress reporter

        Returns:
            Result dict with {"data": {...}} or {"error": {...}}
        """
        try:
            # Step 1: Submit job
            if progress:
                await progress.set_message("Submitting job...")

            job_id = self.submit_job(arguments)

            if progress:
                await progress.set_message(f"Job {job_id} submitted, waiting for completion...")

            # Step 2: Poll until complete
            result = await self._poll_until_complete(job_id, progress)

            # Step 3: Format and return
            return self.format_result(result)

        except Exception as e:
            return self.handle_error(e)

    async def _poll_until_complete(
        self,
        job_id: str,
        progress: Optional[TaskProgress]
    ) -> Any:
        """
        Poll job status until complete (internal implementation).

        This is automatically implemented - you don't write this code!
        """
        max_attempts = int(self.max_duration // self.poll_interval)

        for attempt in range(max_attempts):
            # Check status
            status = self.check_status(job_id)

            # Check for errors
            if status.get("error"):
                raise RuntimeError(f"Job failed: {status['error']}")

            # Check if done
            if status.get("done"):
                result = status.get("result")
                if result is None:
                    raise ValueError("Job completed but no result returned")
                return result

            # Update progress
            if progress:
                percent = status.get("progress", 0)
                elapsed = attempt * self.poll_interval
                remaining_estimate = self.max_duration - elapsed

                if percent > 0:
                    msg = f"Processing... {percent}% complete ({elapsed}s elapsed)"
                else:
                    msg = f"Processing... ({elapsed}s elapsed, ~{remaining_estimate}s remaining)"

                await progress.set_message(msg)

            # Wait before next poll
            await asyncio.sleep(self.poll_interval)

        # Timeout
        raise TimeoutError(
            f"Job {job_id} timed out after {self.max_duration} seconds "
            f"({max_attempts} attempts)"
        )

    def _generate_return_schema(self) -> dict:
        """
        Auto-generate return schema following ToolUniverse conventions.

        This is automatically implemented - you don't write this code!
        """
        return {
            "oneOf": [
                {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "object",
                            "description": "Successful result data"
                        },
                        "metadata": {
                            "type": "object",
                            "description": "Optional metadata"
                        }
                    },
                    "required": ["data"]
                },
                {
                    "type": "object",
                    "properties": {
                        "error": {
                            "type": "object",
                            "properties": {
                                "message": {"type": "string"},
                                "error_type": {"type": "string"},
                                "details": {"type": "object"}
                            },
                            "required": ["message", "error_type"]
                        }
                    },
                    "required": ["error"]
                }
            ]
        }

    def get_batch_concurrency_limit(self) -> int:
        """
        Get maximum number of parallel executions for this tool.

        Default is 3 for long-running operations. Override if needed.

        Returns:
            Maximum concurrent executions (0 = unlimited)
        """
        return 3

    def handle_error(self, exception: Exception) -> dict:
        """
        Handle exceptions and return error dict.

        Default implementation converts exception to ToolUniverse error format.
        Override to customize error handling.

        Args:
            exception: Exception that occurred

        Returns:
            Error dict with {"error": {...}}
        """
        return {
            "error": {
                "message": str(exception),
                "error_type": type(exception).__name__,
                "details": {
                    "exception_class": exception.__class__.__name__,
                    "tool": self.name
                }
            }
        }


class AsyncStreamingTool(ABC):
    """
    Base class for async tools that stream results incrementally.

    Use this for tools that return results progressively (e.g., log streaming,
    real-time data feeds, incremental computations).

    Subclass and implement:
    1. start_stream() - Initialize stream and return stream_id
    2. fetch_chunk() - Get next chunk of data
    3. is_complete() - Check if stream is done

    Example:
        class MyStreamingTool(AsyncStreamingTool):
            name = "My_Streaming_Tool"
            description = "Streams data in real-time"
            chunk_interval = 1

            def start_stream(self, arguments):
                response = requests.post("https://api.example.com/stream", json=arguments)
                return response.json()["stream_id"]

            def fetch_chunk(self, stream_id):
                response = requests.get(f"https://api.example.com/stream/{stream_id}")
                return response.json()

            def is_complete(self, chunk):
                return chunk.get("done", False)
    """

    # Subclass MUST set these
    name: str
    description: str
    parameter: dict

    # Optional configuration
    chunk_interval: int = 1  # seconds between chunk fetches
    max_duration: int = 3600
    fields: dict = {"type": "REST"}

    def __init__(self):
        """Initialize tool with auto-generated return schema."""
        self.return_schema = self._generate_return_schema()

    @abstractmethod
    def start_stream(self, arguments: Dict[str, Any]) -> str:
        """
        Start streaming and return stream identifier.

        Args:
            arguments: Tool arguments

        Returns:
            stream_id as string
        """
        pass

    @abstractmethod
    def fetch_chunk(self, stream_id: str) -> Dict[str, Any]:
        """
        Fetch next chunk of data.

        Args:
            stream_id: Stream identifier

        Returns:
            Chunk data dict
        """
        pass

    @abstractmethod
    def is_complete(self, chunk: Dict[str, Any]) -> bool:
        """
        Check if stream is complete.

        Args:
            chunk: Latest chunk data

        Returns:
            True if streaming is complete
        """
        pass

    async def run(
        self,
        arguments: Dict[str, Any],
        progress: Optional[TaskProgress] = None
    ) -> Dict[str, Any]:
        """Execute streaming tool (automatically implemented!)."""
        try:
            if progress:
                await progress.set_message("Starting stream...")

            stream_id = self.start_stream(arguments)
            chunks = []

            max_chunks = int(self.max_duration // self.chunk_interval)

            for chunk_num in range(max_chunks):
                chunk = self.fetch_chunk(stream_id)
                chunks.append(chunk)

                if self.is_complete(chunk):
                    break

                if progress:
                    await progress.set_message(
                        f"Streaming... ({chunk_num + 1} chunks received)"
                    )

                await asyncio.sleep(self.chunk_interval)
            else:
                raise TimeoutError(f"Stream timed out after {self.max_duration} seconds")

            return {"data": {"chunks": chunks, "total": len(chunks)}}

        except Exception as e:
            return self.handle_error(e)

    def _generate_return_schema(self) -> dict:
        """Auto-generate return schema."""
        return {
            "oneOf": [
                {
                    "type": "object",
                    "properties": {
                        "data": {"type": "object"},
                        "metadata": {"type": "object"}
                    },
                    "required": ["data"]
                },
                {
                    "type": "object",
                    "properties": {
                        "error": {"type": "object"}
                    },
                    "required": ["error"]
                }
            ]
        }

    def get_batch_concurrency_limit(self) -> int:
        """Default concurrency limit for streaming tools."""
        return 5

    def handle_error(self, exception: Exception) -> dict:
        """Handle errors."""
        return {
            "error": {
                "message": str(exception),
                "error_type": type(exception).__name__,
                "details": {"tool": self.name}
            }
        }
