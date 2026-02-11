"""
Example: Building async tools with AsyncPollingTool base class.

This demonstrates how the base class reduces code from 150 lines to ~20 lines!
"""
import requests
from tooluniverse.async_base import AsyncPollingTool


# ============================================================================
# EXAMPLE 1: Minimal async tool (just 20 lines!)
# ============================================================================

class SimpleAsyncTool(AsyncPollingTool):
    """
    Example async tool using AsyncPollingTool base class.

    This tool would normally require 150+ lines of boilerplate.
    With AsyncPollingTool, it's just 20 lines focused on YOUR API logic!
    """

    # Configuration (4 lines)
    name = "Simple_Async_Tool"
    description = "Example async tool (5-30 minutes)"
    poll_interval = 10  # Check status every 10 seconds
    max_duration = 3600  # Timeout after 1 hour

    # Parameters (7 lines)
    parameter = {
        "type": "object",
        "properties": {
            "input_data": {
                "type": "string",
                "description": "Data to process"
            }
        },
        "required": ["input_data"]
    }

    def __init__(self):
        super().__init__()
        self.api_url = "https://api.example.com"

    def submit_job(self, arguments):
        """Submit job - just implement YOUR API call!"""
        response = requests.post(
            f"{self.api_url}/jobs",
            json={"data": arguments["input_data"]}
        )
        response.raise_for_status()
        return response.json()["job_id"]

    def check_status(self, job_id):
        """Check status - just implement YOUR status check!"""
        response = requests.get(f"{self.api_url}/jobs/{job_id}")
        response.raise_for_status()
        data = response.json()

        return {
            "done": data["status"] == "completed",
            "result": data.get("result"),
            "progress": data.get("progress", 0),
            "error": data.get("error")
        }


# ============================================================================
# EXAMPLE 2: Custom result formatting
# ============================================================================

class CustomFormattingTool(AsyncPollingTool):
    """Example with custom result formatting."""

    name = "Custom_Formatting_Tool"
    description = "Example with custom output format"
    poll_interval = 10
    max_duration = 1800

    parameter = {
        "type": "object",
        "properties": {
            "query": {"type": "string"}
        },
        "required": ["query"]
    }

    def __init__(self):
        super().__init__()
        self.api_url = "https://api.example.com"

    def submit_job(self, arguments):
        response = requests.post(
            f"{self.api_url}/analyze",
            json=arguments
        )
        return response.json()["analysis_id"]

    def check_status(self, job_id):
        response = requests.get(f"{self.api_url}/analyze/{job_id}")
        data = response.json()
        return {
            "done": data["complete"],
            "result": data,
            "progress": data.get("percent_done", 0)
        }

    def format_result(self, result):
        """Custom formatting - extract specific fields."""
        return {
            "data": {
                "score": result["final_score"],
                "classification": result["class"],
                "confidence": result["confidence"]
            },
            "metadata": {
                "tool": self.name,
                "version": result.get("version", "1.0"),
                "processing_time": result.get("time_seconds")
            }
        }


# ============================================================================
# EXAMPLE 3: Tool with custom error handling
# ============================================================================

class RobustAsyncTool(AsyncPollingTool):
    """Example with robust error handling."""

    name = "Robust_Async_Tool"
    description = "Example with enhanced error handling"
    poll_interval = 5
    max_duration = 3600

    parameter = {
        "type": "object",
        "properties": {
            "file_url": {"type": "string"}
        },
        "required": ["file_url"]
    }

    def __init__(self):
        super().__init__()
        self.api_url = "https://api.example.com"

    def submit_job(self, arguments):
        """Submit with validation."""
        if not arguments["file_url"].startswith("http"):
            raise ValueError("file_url must be a valid HTTP/HTTPS URL")

        response = requests.post(
            f"{self.api_url}/process",
            json=arguments,
            timeout=30
        )
        response.raise_for_status()
        return response.json()["job_id"]

    def check_status(self, job_id):
        """Status check with retries on network errors."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    f"{self.api_url}/status/{job_id}",
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()

                return {
                    "done": data["state"] in ["completed", "failed"],
                    "result": data.get("output"),
                    "progress": data.get("progress", 0),
                    "error": data.get("error_message")
                }
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise
                # Retry on network error
                continue

    def handle_error(self, exception):
        """Enhanced error handling with more details."""
        error_details = {
            "exception_class": exception.__class__.__name__,
            "tool": self.name,
            "api_url": self.api_url
        }

        # Add context for specific error types
        if isinstance(exception, requests.exceptions.Timeout):
            error_details["hint"] = "API request timed out. The service may be overloaded."
        elif isinstance(exception, requests.exceptions.HTTPError):
            error_details["hint"] = f"API returned error: {exception.response.status_code}"
        elif isinstance(exception, TimeoutError):
            error_details["hint"] = f"Job exceeded maximum duration of {self.max_duration}s"

        return {
            "error": {
                "message": str(exception),
                "error_type": type(exception).__name__,
                "details": error_details
            }
        }


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

async def main():
    """Example usage of async tools with base class."""
    from tooluniverse import ToolUniverse

    # Initialize ToolUniverse
    tu = ToolUniverse()

    # Register our simple tool
    tool = SimpleAsyncTool()
    tu.all_tool_dict["SimpleAsyncTool"] = {
        "type": "SimpleAsyncTool",
        "name": tool.name,
        "description": tool.description,
        "parameter": tool.parameter,
        "return_schema": tool.return_schema,
        "fields": tool.fields
    }
    tu.callable_functions["SimpleAsyncTool"] = tool

    # Use the tool
    print("Running async tool...")
    result = await tu.tools.Simple_Async_Tool(input_data="test data")

    print(f"Result: {result}")

    # The base class handled:
    # ✅ Job submission
    # ✅ Polling logic
    # ✅ Progress reporting
    # ✅ Error handling
    # ✅ Timeout management
    # ✅ Result formatting

    # You only wrote YOUR API logic!


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())


# ============================================================================
# COMPARISON: Before vs After
# ============================================================================

"""
BEFORE (without base class): ~150 lines

class SimpleAsyncTool:
    def __init__(self):
        self.name = "Simple_Async_Tool"
        self.description = "..."
        self.parameter = {...}  # 20 lines
        self.return_schema = {...}  # 30 lines
        self.fields = {"type": "REST"}

    async def run(self, arguments, progress=None):
        try:
            if progress:
                await progress.set_message("Submitting...")

            response = requests.post(...)
            job_id = response.json()["job_id"]

            if progress:
                await progress.set_message(f"Job {job_id} submitted...")

            # Polling loop
            max_attempts = 360
            for attempt in range(max_attempts):
                response = requests.get(...)
                data = response.json()

                if data["status"] == "completed":
                    return {"data": data["result"]}

                if data["status"] == "failed":
                    raise RuntimeError(data.get("error"))

                if progress:
                    percent = data.get("progress", 0)
                    await progress.set_message(f"Processing... {percent}%")

                await asyncio.sleep(10)

            raise TimeoutError("Job timed out")

        except Exception as e:
            return {
                "error": {
                    "message": str(e),
                    "error_type": type(e).__name__
                }
            }

    def get_batch_concurrency_limit(self):
        return 3

    def handle_error(self, exception):
        return {...}


AFTER (with base class): ~20 lines!

class SimpleAsyncTool(AsyncPollingTool):
    name = "Simple_Async_Tool"
    description = "..."
    poll_interval = 10
    max_duration = 3600

    parameter = {...}  # 7 lines

    def submit_job(self, arguments):
        response = requests.post(...)
        return response.json()["job_id"]

    def check_status(self, job_id):
        response = requests.get(...)
        data = response.json()
        return {
            "done": data["status"] == "completed",
            "result": data.get("result"),
            "progress": data.get("progress", 0)
        }

REDUCTION: 150 lines → 20 lines = 87% less code!
"""
