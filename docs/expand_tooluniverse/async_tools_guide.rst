=====================================================
Creating Async Tools with AsyncPollingTool
=====================================================

.. meta::
   :description: Complete guide to creating async tools in ToolUniverse using AsyncPollingTool base class
   :keywords: async tools, long-running operations, polling, MCP tasks, ToolUniverse

.. contents:: Table of Contents
   :local:
   :depth: 2

Overview
========

Many scientific operations take minutes or hours to complete—protein docking, molecular dynamics simulations, large-scale data processing. ToolUniverse provides the **AsyncPollingTool** base class to handle these long-running operations elegantly:

✅ **Automatic polling** - No manual loops needed
✅ **Progress reporting** - Built-in status updates
✅ **Non-blocking** - Server remains responsive
✅ **MCP Tasks compatible** - Works with Model Context Protocol
✅ **Consistent patterns** - All async tools behave the same way

When to Use AsyncPollingTool
============================

Use AsyncPollingTool when your tool:

✅ **Takes >30 seconds** to complete
✅ **Polls external APIs** for job status
✅ **Returns job IDs** that require status checking
✅ **Has multiple processing stages** (submit → poll → retrieve)

**Examples**:
   - Protein structure prediction (5-60 minutes)
   - Molecular docking (10-30 minutes)
   - Large-scale sequence alignment (minutes to hours)
   - Complex simulations (hours to days)

**Don't use** for:
   - Quick API calls (<30 seconds)
   - Synchronous operations
   - Database queries
   - Simple lookups

Quick Start
===========

Here's a minimal async tool:

.. code-block:: python

   from tooluniverse.async_base import AsyncPollingTool
   from tooluniverse.tool_registry import register_tool
   import requests
   from typing import Dict, Any

   @register_tool("MyAsyncTool")
   class MyAsyncTool(AsyncPollingTool):
       """Tool for long-running operations."""

       # Configuration
       poll_interval = 10  # seconds between status checks
       max_duration = 1800  # 30 minutes maximum

       def __init__(self, tool_config: Dict[str, Any]):
           self.name = tool_config["name"]
           self.api_url = "https://api.example.com"
           super().__init__()  # Must call after setting name

       def submit_job(self, arguments: Dict[str, Any]) -> str:
           """Submit job and return job ID."""
           response = requests.post(
               f"{self.api_url}/submit",
               json=arguments
           )
           return response.json()["job_id"]

       def check_status(self, job_id: str) -> Dict[str, Any]:
           """Check job status and return result if done."""
           response = requests.get(
               f"{self.api_url}/status/{job_id}"
           )
           data = response.json()

           if data["status"] == "completed":
               return {"done": True, "result": data["result"]}
           elif data["status"] == "failed":
               return {"done": False, "error": data["error"]}
           else:
               return {"done": False, "progress": 50}

That's it! The base class handles polling, timeouts, and progress reporting.

How It Works
============

The Workflow
------------

.. code-block:: text

   User calls tool
        ↓
   1. submit_job()
      - Submit to external API
      - Return job_id
        ↓
   2. Automatic polling loop (handled by base class)
      - Call check_status(job_id) every poll_interval seconds
      - Report progress if available
      - Continue until done=True or timeout
        ↓
   3. format_result()
      - Format final result
      - Return to user

**Your responsibilities**: Implement 2-3 methods
**Base class handles**: Polling loop, timeouts, progress, error handling

What You Implement
------------------

Required Methods
~~~~~~~~~~~~~~~~

1. **submit_job(arguments) → job_id**

   Submit the job to the external service.

   .. code-block:: python

      def submit_job(self, arguments: Dict[str, Any]) -> str:
          """Submit job and return job ID for polling."""
          # Validate arguments
          if "required_param" not in arguments:
              raise ValueError("Missing required_param")

          # Call external API
          response = requests.post(
              f"{self.api_url}/jobs",
              json=arguments,
              timeout=60
          )

          # Extract job ID
          job_id = response.json()["id"]
          return job_id

2. **check_status(job_id) → status dict**

   Check if job is complete and return results.

   .. code-block:: python

      def check_status(self, job_id: str) -> Dict[str, Any]:
          """Check status and return done/result/error/progress."""
          response = requests.get(
              f"{self.api_url}/jobs/{job_id}/status"
          )
          data = response.json()

          # Job completed successfully
          if data["status"] == "completed":
              return {
                  "done": True,
                  "result": data["output"],
                  "progress": 100
              }

          # Job failed
          if data["status"] == "failed":
              return {
                  "done": False,
                  "error": data["error_message"]
              }

          # Still running
          return {
              "done": False,
              "progress": data.get("percent_complete", 50)
          }

Optional Methods
~~~~~~~~~~~~~~~~

3. **format_result(result) → formatted dict**

   Format the final result (optional, has default).

   .. code-block:: python

      def format_result(self, result: Any) -> Dict[str, Any]:
          """Format result into standard ToolUniverse format."""
          return {
              "data": result,
              "metadata": {
                  "tool": self.name,
                  "timestamp": datetime.now().isoformat()
              }
          }

What the Base Class Provides
-----------------------------

✅ **Automatic polling loop** - Calls ``check_status()`` repeatedly
✅ **Non-blocking async** - Uses ``await asyncio.sleep()``
✅ **Timeout handling** - Stops after ``max_duration`` seconds
✅ **Progress reporting** - Updates via ``TaskProgress``
✅ **Error handling** - Catches exceptions, returns error dicts
✅ **Return schema** - Auto-generates oneOf structure
✅ **run() method** - Orchestrates the entire workflow

Configuration
=============

Class Attributes
----------------

Set these in your tool class:

.. code-block:: python

   class MyAsyncTool(AsyncPollingTool):
       # Polling configuration
       poll_interval = 15    # Seconds between status checks (default: 10)
       max_duration = 3600   # Maximum wait time in seconds (default: 1800)

       # Optional: Custom return schema (usually auto-generated)
       return_schema = {
           "oneOf": [
               {"properties": {"data": {...}, "metadata": {...}}},
               {"properties": {"error": {...}}}
           ]
       }

JSON Configuration
------------------

In your ``*_tools.json`` file:

.. code-block:: json

   {
     "type": "MyAsyncTool",
     "name": "MyTool_analyze_data",
     "description": "Analyze large dataset (may take 10-30 minutes)",
     "parameter": {
       "type": "object",
       "properties": {
         "dataset_id": {
           "type": "string",
           "description": "ID of dataset to analyze"
         }
       },
       "required": ["dataset_id"]
     },
     "fields": {
       "is_async": true,
       "poll_interval": 20,
       "max_wait_time": 1800
     }
   }

Real-World Examples
===================

Example 1: ProteinsPlus (Simple Polling)
-----------------------------------------

ProteinsPlus API returns a status URL that we poll:

.. code-block:: python

   @register_tool("ProteinsPlusRESTTool")
   class ProteinsPlusRESTTool(AsyncPollingTool):
       """Protein structure analysis."""

       poll_interval = 15
       max_duration = 1800

       def submit_job(self, arguments: Dict[str, Any]) -> str:
           """Submit PDB structure for analysis."""
           pdb_id = arguments["pdb_id"]

           # Build request
           request_data = {
               "dogsite": {
                   "pdbCode": pdb_id,
                   "analysisDetail": "1"
               }
           }

           # Submit to ProteinsPlus
           response = requests.post(
               "https://proteins.plus/api/dogsite_rest",
               json=request_data
           )

           # Return status URL as job_id
           return response.json()["location"]

       def check_status(self, job_id: str) -> Dict[str, Any]:
           """Check if analysis is complete."""
           response = requests.get(job_id)

           # HTTP 202 = still processing
           if response.status_code == 202:
               return {"done": False, "progress": 30}

           # HTTP 200 = complete
           if response.status_code == 200:
               results = response.json()
               return {"done": True, "result": results, "progress": 100}

           # Error
           return {"done": False, "error": f"HTTP {response.status_code}"}

Example 2: SwissDock (Multi-Step Workflow)
-------------------------------------------

SwissDock requires multiple API calls before polling:

.. code-block:: python

   @register_tool("SwissDockTool")
   class SwissDockTool(AsyncPollingTool):
       """Molecular docking simulation."""

       poll_interval = 30
       max_duration = 3600

       def submit_job(self, arguments: Dict[str, Any]) -> str:
           """Multi-step job submission."""
           # Step 1: Generate session ID
           session_id = str(uuid.uuid4())

           # Step 2: Prepare ligand
           self._prepare_ligand(session_id, arguments["ligand_smiles"])

           # Step 3: Prepare target protein
           self._prepare_target(session_id, arguments["pdb_id"])

           # Step 4: Set docking parameters
           self._set_parameters(session_id, arguments)

           # Step 5: Start docking
           self._start_docking(session_id)

           return session_id

       def check_status(self, job_id: str) -> Dict[str, Any]:
           """Check docking progress."""
           response = requests.get(
               f"{self.base_url}/checkstatus",
               params={"sessionNumber": job_id}
           )

           status = response.text.strip().upper()

           if "FINISHED" in status:
               results = self._retrieve_results(job_id)
               return {"done": True, "result": results}

           if "ERROR" in status or "FAIL" in status:
               return {"done": False, "error": "Docking failed"}

           # Still running
           return {"done": False, "progress": 50}

       def _prepare_ligand(self, session_id, smiles):
           """Helper: prepare ligand from SMILES."""
           requests.get(f"{self.base_url}/preplig",
                       params={"mySMILES": smiles})

       # ... more helper methods ...

Progress Reporting
==================

Automatic Progress
------------------

The base class automatically reports progress through the ``TaskProgress`` system:

.. code-block:: python

   # Your check_status returns progress percentage:
   return {"done": False, "progress": 45}

   # Users see:
   # "🔄 Running MyTool_analyze_data (45% complete)"

Custom Messages
---------------

For more detailed progress updates:

.. code-block:: python

   async def run(self, arguments, progress=None):
       """Override run() for custom progress messages."""
       if progress:
           await progress.set_message("Validating input...")

       job_id = self.submit_job(arguments)

       if progress:
           await progress.set_message(f"Job {job_id} submitted")

       # Let base class handle polling
       return await super().run(arguments, progress)

Error Handling
==============

In submit_job
-------------

Raise exceptions for validation errors:

.. code-block:: python

   def submit_job(self, arguments):
       # Validate required parameters
       if "pdb_id" not in arguments:
           raise ValueError("pdb_id parameter is required")

       if len(arguments["pdb_id"]) != 4:
           raise ValueError("pdb_id must be 4 characters")

       # Raise for API errors
       response = requests.post(url, json=data)
       if response.status_code == 400:
           raise RuntimeError(f"API error: {response.text}")

       return response.json()["job_id"]

In check_status
---------------

Return error dicts for job failures:

.. code-block:: python

   def check_status(self, job_id):
       response = requests.get(f"{url}/status/{job_id}")

       # Job failed on server
       if response.json()["status"] == "failed":
           return {
               "done": False,
               "error": "Job execution failed on server"
           }

       # Network/API error
       if response.status_code == 404:
           return {
               "done": False,
               "error": "Job not found (may have expired)"
           }

MCP Tasks Integration
=====================

Your AsyncPollingTool automatically works with MCP Tasks protocol for non-blocking execution.

How It Works
------------

.. code-block:: text

   MCP Client → SMCP Server → TaskManager → Your AsyncPollingTool
                    ↓              ↓              ↓
                Returns         Creates       Executes
                taskId       Background         Job
                immediately     Task          Async

The TaskManager handles:
   - Creating background tasks
   - Polling your tool's status
   - Reporting progress to client
   - Managing timeouts and cleanup

You don't need to do anything special—just inherit from AsyncPollingTool!

Testing Async Tools
===================

Unit Testing
------------

Test components individually:

.. code-block:: python

   import pytest
   from unittest.mock import Mock, patch

   def test_submit_job():
       """Test job submission."""
       tool = MyAsyncTool(config)

       with patch('requests.post') as mock_post:
           mock_post.return_value.json.return_value = {"job_id": "123"}

           job_id = tool.submit_job({"param": "value"})

           assert job_id == "123"
           assert mock_post.called

   def test_check_status_complete():
       """Test status check when job is done."""
       tool = MyAsyncTool(config)

       with patch('requests.get') as mock_get:
           mock_get.return_value.json.return_value = {
               "status": "completed",
               "result": {"data": "output"}
           }

           status = tool.check_status("123")

           assert status["done"] == True
           assert "result" in status

   def test_check_status_running():
       """Test status check while still running."""
       tool = MyAsyncTool(config)

       with patch('requests.get') as mock_get:
           mock_get.return_value.json.return_value = {
               "status": "running",
               "progress": 75
           }

           status = tool.check_status("123")

           assert status["done"] == False
           assert status["progress"] == 75

Integration Testing
-------------------

Test with real API (when available):

.. code-block:: python

   @pytest.mark.integration
   @pytest.mark.asyncio
   async def test_full_workflow():
       """Test complete async workflow."""
       from tooluniverse import ToolUniverse

       tu = ToolUniverse()
       tu.load_tools()

       # Run async tool (will use TaskManager if available)
       result = await tu.run_async(
           '{"name": "MyTool_analyze_data", "arguments": {"dataset_id": "test123"}}'
       )

       assert "data" in result
       assert result["data"] is not None

Best Practices
==============

Do's
----

✅ **Keep submit_job lightweight** - Just submit and return ID
✅ **Handle all status cases** - completed, failed, running, unknown
✅ **Validate inputs early** - Fail fast in submit_job
✅ **Use appropriate intervals** - 10-30s for most APIs
✅ **Set realistic timeouts** - Consider actual job duration
✅ **Return progress when available** - Better UX
✅ **Use helper methods** - Keep methods focused and clean
✅ **Test with mocks first** - Don't hit real APIs in unit tests

Don'ts
------

❌ **Don't do work in submit_job** - Just submit to external service
❌ **Don't block in check_status** - Should be a quick status check
❌ **Don't poll too frequently** - Respect API rate limits (<10s is usually too much)
❌ **Don't set infinite timeouts** - Always have max_duration
❌ **Don't swallow errors** - Return {"error": "..."} or raise exception
❌ **Don't use time.sleep()** - Use asyncio.sleep() or let base class handle it
❌ **Don't return raw API responses** - Format consistently

Common Patterns
===============

Pattern 1: Status URL
---------------------

API returns a URL to poll:

.. code-block:: python

   def submit_job(self, arguments):
       response = requests.post(api_url, json=arguments)
       return response.json()["status_url"]  # URL is the job_id

   def check_status(self, job_id):
       response = requests.get(job_id)  # job_id IS the URL
       # ... check response ...

Pattern 2: Separate Endpoints
------------------------------

Different endpoints for submit and status:

.. code-block:: python

   def submit_job(self, arguments):
       response = requests.post(f"{self.base_url}/jobs", json=arguments)
       return response.json()["job_id"]

   def check_status(self, job_id):
       response = requests.get(f"{self.base_url}/jobs/{job_id}/status")
       # ... check response ...

Pattern 3: Polling with Authentication
---------------------------------------

Need auth token for status checks:

.. code-block:: python

   def __init__(self, tool_config):
       super().__init__()
       self.api_key = os.getenv("API_KEY")
       self._headers = {"Authorization": f"Bearer {self.api_key}"}

   def submit_job(self, arguments):
       response = requests.post(url, json=arguments, headers=self._headers)
       return response.json()["job_id"]

   def check_status(self, job_id):
       response = requests.get(url, headers=self._headers)
       # ... check response ...

Pattern 4: Multi-Stage Pipeline
--------------------------------

Job has multiple stages:

.. code-block:: python

   def check_status(self, job_id):
       response = requests.get(f"{url}/status/{job_id}")
       data = response.json()

       # Map stages to progress
       stage_progress = {
           "queued": 10,
           "preprocessing": 25,
           "processing": 50,
           "postprocessing": 75,
           "completed": 100
       }

       stage = data["current_stage"]

       if stage == "completed":
           return {"done": True, "result": data["output"]}
       elif stage == "failed":
           return {"done": False, "error": data["error"]}
       else:
           return {"done": False, "progress": stage_progress.get(stage, 50)}

Migration Guide
===============

Converting Existing Async Tools
--------------------------------

If you have an existing async tool with manual polling:

**Before** (286 lines with manual polling):

.. code-block:: python

   class OldAsyncTool(BaseTool):
       def run(self, arguments):
           # Submit job
           job_id = self._submit_job(arguments)

           # Manual polling loop (70+ lines!)
           start_time = time.time()
           while True:
               elapsed = time.time() - start_time
               if elapsed > 1800:
                   return {"error": "Timeout"}

               status = self._check_status(job_id)
               if status["done"]:
                   return status["result"]

               time.sleep(10)  # Blocks!

**After** (356 lines, but cleaner with automatic polling):

.. code-block:: python

   class NewAsyncTool(AsyncPollingTool):
       poll_interval = 10
       max_duration = 1800

       def submit_job(self, arguments):
           return self._submit_job(arguments)

       def check_status(self, job_id):
           return self._check_status(job_id)

**Result**:
   - Eliminated 70+ lines of polling boilerplate
   - Non-blocking async execution
   - Automatic progress reporting
   - MCP Tasks compatible

Troubleshooting
===============

Tool Never Completes
--------------------

**Symptoms**: Tool runs forever, never returns result

**Causes**:
   - ``check_status()`` never returns ``done=True``
   - Wrong job_id format
   - API endpoint changed

**Debug**:

.. code-block:: python

   def check_status(self, job_id):
       response = requests.get(f"{url}/status/{job_id}")
       print(f"DEBUG: Status response: {response.json()}")  # Add logging

       # Make sure you return done=True at some point!
       if response.json()["status"] == "completed":
           return {"done": True, "result": response.json()}

Job Times Out
-------------

**Symptoms**: Tool returns timeout error

**Causes**:
   - ``max_duration`` too short
   - Job actually takes longer than expected
   - API is slow

**Fix**:

.. code-block:: python

   class MyTool(AsyncPollingTool):
       max_duration = 3600  # Increase timeout to 1 hour
       poll_interval = 20   # Poll less frequently

Progress Not Showing
--------------------

**Symptoms**: No progress updates visible

**Causes**:
   - Not returning ``progress`` in ``check_status()``
   - Progress not changing between calls

**Fix**:

.. code-block:: python

   def check_status(self, job_id):
       response = requests.get(f"{url}/status/{job_id}")
       data = response.json()

       # Always return progress when not done
       if not data["is_complete"]:
           return {
               "done": False,
               "progress": data.get("percent_complete", 50)  # Include progress!
           }

Tool Returns Error Dict
-----------------------

**Symptoms**: Tool returns ``{"error": "..."}`` unexpectedly

**Causes**:
   - Exception in ``submit_job()``
   - API returns error status
   - Network error

**Debug**:

.. code-block:: python

   def submit_job(self, arguments):
       try:
           response = requests.post(url, json=arguments, timeout=60)
           response.raise_for_status()  # Raises for 4xx/5xx
           return response.json()["job_id"]
       except requests.Timeout:
           raise RuntimeError("API timeout during job submission")
       except requests.HTTPError as e:
           raise RuntimeError(f"API error: {e.response.text}")
       except KeyError:
           raise RuntimeError("API response missing job_id field")

API Reference
=============

AsyncPollingTool Class
----------------------

.. code-block:: python

   class AsyncPollingTool(ABC):
       """Base class for async tools with automatic polling.

       Attributes:
           poll_interval (int): Seconds between status checks (default: 10)
           max_duration (int): Maximum wait time in seconds (default: 1800)
           return_schema (dict): Tool return schema (auto-generated if not set)
       """

       @abstractmethod
       def submit_job(self, arguments: Dict[str, Any]) -> str:
           """Submit job to external service.

           Args:
               arguments: Tool parameters from user

           Returns:
               job_id: Identifier for polling (string)

           Raises:
               ValueError: Invalid parameters
               RuntimeError: API/submission error
           """
           pass

       @abstractmethod
       def check_status(self, job_id: str) -> Dict[str, Any]:
           """Check job status and return result if complete.

           Args:
               job_id: Job identifier from submit_job()

           Returns:
               Dictionary with:
                   - done (bool): True if job complete
                   - result (any): Final result (if done=True)
                   - error (str): Error message (if failed)
                   - progress (int): Progress percentage 0-100 (optional)
           """
           pass

       def format_result(self, result: Any) -> Dict[str, Any]:
           """Format final result (optional override).

           Args:
               result: Raw result from check_status()

           Returns:
               Formatted result dictionary
           """
           return {
               "data": result,
               "metadata": {"tool": self.name}
           }

       async def run(
           self,
           arguments: Dict[str, Any],
           progress: Optional["TaskProgress"] = None
       ) -> Dict[str, Any]:
           """Execute tool with automatic polling (do not override unless needed).

           Args:
               arguments: Tool parameters
               progress: Optional progress reporter

           Returns:
               Final formatted result
           """
           # Implemented by base class - handles polling automatically

Further Reading
===============

- :doc:`/expand_tooluniverse/comprehensive_tool_guide` - Complete tool development guide
- :doc:`/expand_tooluniverse/local_tools/index` - Creating local tools
- :doc:`/guide/building_ai_scientists/mcp_support` - MCP integration
- :doc:`/api/tooluniverse.async_base` - API documentation

Examples
--------

- ``src/tooluniverse/proteinsplus_tool.py`` - Simple polling example
- ``src/tooluniverse/swissdock_tool.py`` - Complex multi-step workflow
- ``examples/proteinsplus_tools_example.py`` - Usage examples
- ``tests/test_async_base.py`` - Test examples

Changelog
=========

- **v0.4.0** (2024-02): Added AsyncPollingTool base class
- **v0.4.1** (2024-02): Added MCP Tasks integration
- **v0.4.2** (2024-02): Converted ProteinsPlus and SwissDock tools

.. note::
   AsyncPollingTool is production-ready and recommended for all new async tools.
   It eliminates 70-100 lines of boilerplate per tool and ensures consistent behavior.
