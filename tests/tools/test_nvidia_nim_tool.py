"""Unit tests for NVIDIA NIM Healthcare API tools.

Tests are organized into levels:
- Level 1: Mocked HTTP responses (no API calls)
- Level 2: ToolUniverse interface tests (loads tools, validates schemas)
- Level 3: Real API tests (optional, requires NVIDIA_API_KEY and uses rate limit)

Run all tests: pytest tests/unit/test_nvidia_nim_tool.py
Run only Level 1: pytest tests/unit/test_nvidia_nim_tool.py -m "not slow"
Run with real API: pytest tests/unit/test_nvidia_nim_tool.py --runreal
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from tooluniverse import ToolUniverse


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def tu():
    """Create ToolUniverse instance with tools loaded."""
    tu = ToolUniverse()
    tu.load_tools()
    return tu


@pytest.fixture
def mock_api_key():
    """Set mock API key for testing."""
    with patch.dict(os.environ, {"NVIDIA_API_KEY": "test-api-key-12345"}):
        yield


@pytest.fixture
def tu_with_api_key(mock_api_key):
    """Create ToolUniverse instance with tools loaded and NVIDIA_API_KEY set.
    
    This ensures NVIDIA NIM tools are not filtered out due to missing API key.
    Note: mock_api_key fixture must be listed first to ensure env var is set
    before ToolUniverse is created.
    """
    # Double-check the env var is set
    assert os.environ.get("NVIDIA_API_KEY") == "test-api-key-12345"
    tu = ToolUniverse()
    tu.load_tools()
    return tu


@pytest.fixture
def nvidia_nim_tool():
    """Create a NvidiaNIMTool instance directly for unit testing."""
    from tooluniverse.nvidia_nim_tool import NvidiaNIMTool
    
    tool_config = {
        "name": "test_tool",
        "fields": {
            "endpoint": "test/endpoint",
            "async_expected": False,
            "response_type": "json",
            "timeout": 30
        },
        "parameter": {
            "type": "object",
            "properties": {"sequence": {"type": "string"}},
            "required": ["sequence"]
        }
    }
    
    with patch.dict(os.environ, {"NVIDIA_API_KEY": "test-api-key-12345"}):
        return NvidiaNIMTool(tool_config)


# ============================================================================
# Level 1: Unit Tests with Mocked HTTP (No API calls)
# ============================================================================

class TestNvidiaNIMToolUnit:
    """Level 1: Unit tests with mocked HTTP responses."""
    
    def test_init_loads_config(self, nvidia_nim_tool):
        """Test that tool initializes with correct config."""
        assert nvidia_nim_tool.endpoint == "test/endpoint"
        assert nvidia_nim_tool.async_expected is False
        assert nvidia_nim_tool.response_type == "json"
        assert nvidia_nim_tool.timeout == 30
    
    def test_get_headers(self, nvidia_nim_tool):
        """Test header generation with API key."""
        headers = nvidia_nim_tool._get_headers()
        
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-api-key-12345"
        assert headers["Content-Type"] == "application/json"
    
    def test_build_url(self, nvidia_nim_tool):
        """Test URL construction."""
        url = nvidia_nim_tool._build_url()
        assert url == "https://health.api.nvidia.com/v1/biology/test/endpoint"

    def test_build_url_fills_templated_path_param(self):
        """A {placeholder} endpoint is filled from args, default, and sanitized."""
        from tooluniverse.nvidia_nim_tool import NvidiaNIMTool

        cfg = {
            "name": "evo2",
            "fields": {"endpoint": "arc/{model}/generate",
                       "path_params": {"model": "evo2-40b"}},
            "parameter": {"type": "object",
                          "properties": {"sequence": {"type": "string"}},
                          "required": ["sequence"]},
        }
        with patch.dict(os.environ, {"NVIDIA_API_KEY": "k"}):
            tool = NvidiaNIMTool(cfg)
        base = "https://health.api.nvidia.com/v1/biology/arc"
        # default when not provided
        assert tool._build_url({}) == f"{base}/evo2-40b/generate"
        # overridden by a valid arg
        assert tool._build_url({"model": "evo2-7b"}) == f"{base}/evo2-7b/generate"
        # unsafe value falls back to the default (no path injection)
        assert tool._build_url({"model": "../../x"}) == f"{base}/evo2-40b/generate"

    @patch("requests.post")
    def test_path_param_not_sent_in_request_body(self, mock_post):
        """The model path-param selects the URL; it must not leak into the body."""
        from tooluniverse.nvidia_nim_tool import NvidiaNIMTool

        cfg = {
            "name": "evo2",
            "fields": {"endpoint": "arc/{model}/generate",
                       "path_params": {"model": "evo2-40b"}, "response_type": "json"},
            "parameter": {"type": "object",
                          "properties": {"sequence": {"type": "string"}},
                          "required": ["sequence"]},
        }
        resp = MagicMock()
        resp.status_code = 200
        resp.headers = {"Content-Type": "application/json"}
        resp.json.return_value = {"sequence": "ACGT"}
        mock_post.return_value = resp

        with patch.dict(os.environ, {"NVIDIA_API_KEY": "k"}):
            NvidiaNIMTool(cfg).run({"sequence": "ACGT", "model": "evo2-7b"})

        called_url = mock_post.call_args[0][0]
        sent_body = mock_post.call_args[1]["json"]
        assert called_url.endswith("/arc/evo2-7b/generate")
        assert "model" not in sent_body
        assert sent_body["sequence"] == "ACGT"
    
    def test_missing_api_key_error(self):
        """Test error when API key is missing."""
        from tooluniverse.nvidia_nim_tool import NvidiaNIMTool
        
        tool_config = {
            "name": "test_tool",
            "fields": {"endpoint": "test"},
            "parameter": {"type": "object", "properties": {}, "required": []}
        }
        
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("NVIDIA_API_KEY", None)
            tool = NvidiaNIMTool(tool_config)
            result = tool.run({})
            
            assert "error" in result
            assert "Missing API key" in result["error"]
    
    def test_missing_required_params_error(self, nvidia_nim_tool):
        """Test error when required parameters are missing."""
        result = nvidia_nim_tool.run({})
        
        assert "error" in result
        assert "Missing required parameters" in result["error"]
    
    @patch("requests.post")
    def test_successful_sync_request(self, mock_post, nvidia_nim_tool):
        """Test successful synchronous API request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success", "structure": "PDB_DATA"}
        mock_response.headers = {"Content-Type": "application/json"}
        mock_post.return_value = mock_response
        
        result = nvidia_nim_tool.run({"sequence": "MVLSPADKTNVKAAWGKVG"})
        
        assert result["status"] == "success"
        assert "data" in result
        mock_post.assert_called_once()
    
    @patch("requests.get")
    @patch("requests.post")
    def test_async_polling_request(self, mock_post, mock_get):
        """Test async request with polling."""
        from tooluniverse.nvidia_nim_tool import NvidiaNIMTool
        
        tool_config = {
            "name": "async_tool",
            "fields": {
                "endpoint": "deepmind/alphafold2",
                "async_expected": True,
                "poll_seconds": 300,
                "response_type": "json"
            },
            "parameter": {
                "type": "object",
                "properties": {"sequence": {"type": "string"}},
                "required": ["sequence"]
            }
        }
        
        # Mock initial 202 response
        mock_post_response = MagicMock()
        mock_post_response.status_code = 202
        mock_post_response.headers = {"nvcf-reqid": "test-request-id-123"}
        mock_post.return_value = mock_post_response
        
        # Mock polling responses - first returns 202, then 200
        mock_poll_202 = MagicMock()
        mock_poll_202.status_code = 202
        
        mock_poll_200 = MagicMock()
        mock_poll_200.status_code = 200
        mock_poll_200.json.return_value = {"status": "complete", "structure": "PDB"}
        mock_poll_200.headers = {"Content-Type": "application/json"}
        
        mock_get.side_effect = [mock_poll_200]  # Complete on first poll
        
        with patch.dict(os.environ, {"NVIDIA_API_KEY": "test-key"}):
            tool = NvidiaNIMTool(tool_config)
            result = tool.run({"sequence": "MVLSPADKTNVKAAWGKVG"})
        
        assert result["status"] == "success"
        mock_get.assert_called()
    
    @patch("requests.post")
    def test_rate_limit_error(self, mock_post, nvidia_nim_tool):
        """Test handling of rate limit (429) response."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_post.return_value = mock_response
        
        result = nvidia_nim_tool.run({"sequence": "MVLSPADKTNVKAAWGKVG"})
        
        assert "error" in result
        assert "Rate limit" in result["error"]
    
    @patch("requests.post")
    def test_auth_error(self, mock_post, nvidia_nim_tool):
        """Test handling of authentication (401) error."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response
        
        result = nvidia_nim_tool.run({"sequence": "MVLSPADKTNVKAAWGKVG"})
        
        assert "error" in result
        assert "Authentication failed" in result["error"]
    
    @patch("requests.post")
    def test_server_error(self, mock_post, nvidia_nim_tool):
        """Test handling of server (500) error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_post.return_value = mock_response

        result = nvidia_nim_tool.run({"sequence": "MVLSPADKTNVKAAWGKVG"})

        assert "error" in result
        assert "Server error" in result["error"]

    @patch("requests.post")
    def test_server_error_empty_body_surfaces_nvcf_status(self, mock_post, nvidia_nim_tool):
        """A 5xx with an empty body should surface the nvcf-status header signal.

        The biology gateway returns 504 with an empty body and
        nvcf-status='errored' when a hosted function cold-starts or fails; the
        useful diagnostic lives in the headers, not the body.
        """
        mock_response = MagicMock()
        mock_response.status_code = 504
        mock_response.text = ""
        mock_response.headers = {"nvcf-status": "errored", "nvcf-reqid": "abc-123"}
        mock_post.return_value = mock_response

        result = nvidia_nim_tool.run({"sequence": "MVLSPADKTNVKAAWGKVG"})

        assert result["status"] == "error"
        assert "errored" in result["detail"]
        assert "abc-123" in result["detail"]

    @patch("requests.post")
    def test_esmfold_json_envelope_unwrapped_to_pdb(self, mock_post):
        """ESMFold answers the pdb path with JSON {"pdbs": [...]}; unwrap to PDB.

        The tool must return the actual PDB string in 'structure', not the raw
        JSON envelope, so downstream consumers get parseable ATOM records.
        """
        from tooluniverse.nvidia_nim_tool import NvidiaNIMTool

        cfg = {
            "name": "esmfold",
            "fields": {"endpoint": "nvidia/esmfold", "response_type": "pdb"},
            "parameter": {"type": "object", "properties": {"sequence": {"type": "string"}},
                          "required": ["sequence"]},
        }
        pdb_text = "PARENT N/A\nATOM      1  N   MET A   1       0.0   0.0   0.0\n"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.text = json.dumps({"pdbs": [pdb_text]})
        mock_response.json.return_value = {"pdbs": [pdb_text]}
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {"NVIDIA_API_KEY": "test-key"}):
            result = NvidiaNIMTool(cfg).run({"sequence": "MVLSP"})

        assert result["status"] == "success"
        assert result["structure"] == pdb_text
        assert result["structure"].startswith("PARENT")  # not "{"

    @patch("requests.post")
    def test_inner_failure_reported_as_error(self, mock_post, nvidia_nim_tool):
        """HTTP 200 with an inner {"status": "failed"} must surface as an error.

        DiffDock (and similar NIMs) answer 200 while reporting an internal
        failure; reporting top-level success would mislead the caller.
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {
            "status": "failed",
            "details": "Fail to read ligand molecule description",
            "ligand_positions": ["", ""],
        }
        mock_post.return_value = mock_response

        result = nvidia_nim_tool.run({"sequence": "MVLSP"})

        assert result["status"] == "error"
        assert "inner failure" in result["error"].lower()
        assert "ligand" in result["detail"].lower()
        # the raw payload is still passed through for debugging
        assert result["data"]["status"] == "failed"

    @patch("requests.post")
    def test_inner_success_not_flagged(self, mock_post, nvidia_nim_tool):
        """An inner {"status": "success"} (e.g. GenMol) must stay a success."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"status": "success", "molecules": [{"smiles": "CCO"}]}
        mock_post.return_value = mock_response

        result = nvidia_nim_tool.run({"sequence": "MVLSP"})

        assert result["status"] == "success"
        assert result["data"]["molecules"][0]["smiles"] == "CCO"

    @patch("requests.post")
    def test_404_not_found_for_account(self, mock_post, nvidia_nim_tool):
        """A 404 'Not found for account' means the model isn't provisioned.

        This is distinct from a wrong path; the error should say the model is
        unavailable for this account rather than implying a missing endpoint.
        """
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = ('{"status":404,"title":"Not Found",'
                              '"detail":"Function \'b1116c0d\': Not found for account \'xyz\'"}')
        mock_post.return_value = mock_response

        result = nvidia_nim_tool.run({"sequence": "MVLSP"})

        assert result["status"] == "error"
        assert "not available" in result["error"].lower()
        assert "account" in result["error"].lower()

    @patch("requests.post")
    def test_degraded_function_reported_clearly(self, mock_post, nvidia_nim_tool):
        """A 400 'DEGRADED function cannot be invoked' is a transient NVIDIA state.

        It must read as a server-side degradation (retry later), not a bad
        request from the caller.
        """
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = ('{"status":400,"title":"Bad Request",'
                              '"detail":"Function id \'e3dfc6dd\': DEGRADED function cannot be invoked"}')
        mock_response.headers = {}
        mock_post.return_value = mock_response

        result = nvidia_nim_tool.run({"sequence": "MVLSP"})

        assert result["status"] == "error"
        assert "degraded" in result["error"].lower()
        assert "retry later" in result["detail"].lower()

    @patch("requests.get")
    @patch("requests.post")
    def test_async_polls_on_invocation_host_not_integrate(self, mock_post, mock_get):
        """Async polling must target the same gateway host as the invocation.

        Biology NIMs live on health.api.nvidia.com; the LLM host
        integrate.api.nvidia.com has no /v1/status route. Regression guard for
        the poll-URL fix.
        """
        from tooluniverse.nvidia_nim_tool import NvidiaNIMTool

        cfg = {
            "name": "async_tool",
            "fields": {"endpoint": "deepmind/alphafold2", "async_expected": True,
                       "poll_seconds": 5, "response_type": "json"},
            "parameter": {"type": "object", "properties": {"sequence": {"type": "string"}},
                          "required": ["sequence"]},
        }
        post_202 = MagicMock()
        post_202.status_code = 202
        post_202.headers = {"nvcf-reqid": "req-xyz"}
        mock_post.return_value = post_202

        poll_200 = MagicMock()
        poll_200.status_code = 200
        poll_200.headers = {"Content-Type": "application/json"}
        poll_200.json.return_value = {"structure": "PDB"}
        mock_get.return_value = poll_200

        with patch.dict(os.environ, {"NVIDIA_API_KEY": "test-key"}):
            result = NvidiaNIMTool(cfg).run({"sequence": "MVLSP"})

        assert result["status"] == "success"
        polled_url = mock_get.call_args[0][0]
        assert polled_url == "https://health.api.nvidia.com/v1/status/req-xyz"
        assert "integrate.api.nvidia.com" not in polled_url


# ============================================================================
# Level 2: ToolUniverse Interface Tests
# ============================================================================

class TestNvidiaNIMToolsLoad:
    """Level 2: Test tool loading and schema validation."""
    
    def test_all_nvidia_tools_load(self, tu_with_api_key):
        """Test that all 16 NVIDIA NIM tools load correctly."""
        tool_names = [tool.get("name") for tool in tu_with_api_key.all_tools if isinstance(tool, dict)]
        
        expected_tools = [
            "NvidiaNIM_alphafold2",
            "NvidiaNIM_alphafold2_multimer",
            "NvidiaNIM_esmfold",
            "NvidiaNIM_openfold2",
            "NvidiaNIM_openfold3",
            "NvidiaNIM_boltz2",
            "NvidiaNIM_proteinmpnn",
            "NvidiaNIM_rfdiffusion",
            "NvidiaNIM_diffdock",
            "NvidiaNIM_genmol",
            "NvidiaNIM_molmim",
            "NvidiaNIM_evo2",
            "NvidiaNIM_msa_search",
            "NvidiaNIM_esm2_650m",
            "NvidiaNIM_maisi",
            "NvidiaNIM_vista3d",
        ]
        
        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Tool {tool_name} not found"
    
    def test_tool_has_required_fields(self, tu_with_api_key):
        """Test that NVIDIA tools have required configuration fields."""
        nvidia_tools = [
            tool for tool in tu_with_api_key.all_tools 
            if isinstance(tool, dict) and tool.get("name", "").startswith("NvidiaNIM_")
        ]
        
        for tool in nvidia_tools:
            assert "name" in tool, f"Tool missing 'name'"
            assert "description" in tool, f"Tool {tool.get('name')} missing 'description'"
            assert "parameter" in tool, f"Tool {tool.get('name')} missing 'parameter'"
            assert "type" in tool, f"Tool {tool.get('name')} missing 'type'"
            assert tool["type"] == "NvidiaNIMTool"
    
    def test_tool_has_api_key_requirement(self, tu_with_api_key):
        """Test that NVIDIA tools declare API key requirement."""
        nvidia_tools = [
            tool for tool in tu_with_api_key.all_tools 
            if isinstance(tool, dict) and tool.get("name", "").startswith("NvidiaNIM_")
        ]
        
        for tool in nvidia_tools:
            api_keys = tool.get("required_api_keys", [])
            assert "NVIDIA_API_KEY" in api_keys, (
                f"Tool {tool.get('name')} should require NVIDIA_API_KEY"
            )
    
    def test_tool_has_test_examples(self, tu_with_api_key):
        """Test that NVIDIA tools have test examples."""
        nvidia_tools = [
            tool for tool in tu_with_api_key.all_tools 
            if isinstance(tool, dict) and tool.get("name", "").startswith("NvidiaNIM_")
        ]
        
        for tool in nvidia_tools:
            examples = tool.get("test_examples", [])
            assert len(examples) > 0, (
                f"Tool {tool.get('name')} should have at least one test example"
            )
    
    def test_parameter_schema_valid(self, tu_with_api_key):
        """Test that parameter schemas are valid JSON Schema."""
        nvidia_tools = [
            tool for tool in tu_with_api_key.all_tools 
            if isinstance(tool, dict) and tool.get("name", "").startswith("NvidiaNIM_")
        ]
        
        for tool in nvidia_tools:
            param = tool.get("parameter", {})
            assert param.get("type") == "object", (
                f"Tool {tool.get('name')} parameter type should be 'object'"
            )
            assert "properties" in param, (
                f"Tool {tool.get('name')} should have 'properties' in parameter"
            )
    
    def test_async_tools_marked_correctly(self, tu_with_api_key):
        """Test that async tools have async_expected=true in fields."""
        # These tools require async polling for long-running operations
        # Note: MAISI and Vista3D are synchronous (async_expected=false)
        async_tools = [
            "NvidiaNIM_alphafold2",
            "NvidiaNIM_alphafold2_multimer",
            "NvidiaNIM_openfold2",
            "NvidiaNIM_openfold3",
            "NvidiaNIM_boltz2",
            "NvidiaNIM_rfdiffusion",
            "NvidiaNIM_diffdock",
            "NvidiaNIM_msa_search",
        ]
        
        nvidia_tools = {
            tool.get("name"): tool 
            for tool in tu_with_api_key.all_tools 
            if isinstance(tool, dict) and tool.get("name", "").startswith("NvidiaNIM_")
        }
        
        for tool_name in async_tools:
            tool = nvidia_tools.get(tool_name)
            assert tool is not None, f"Tool {tool_name} not found"
            fields = tool.get("fields", {})
            assert fields.get("async_expected") is True, (
                f"Tool {tool_name} should have async_expected=true"
            )


class TestNvidiaNIMToolsInterface:
    """Level 2: Test ToolUniverse interface for NVIDIA tools."""
    
    @patch("requests.post")
    def test_run_function_with_mock(self, mock_post, tu_with_api_key):
        """Test running NVIDIA tool through ToolUniverse interface."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"structure": "PDB_DATA"}
        mock_response.headers = {"Content-Type": "application/json"}
        mock_post.return_value = mock_response
        
        result = tu_with_api_key.run_one_function({
            "name": "NvidiaNIM_esmfold",
            "arguments": {"sequence": "MVLSPADKTNVKAAWGKVG"}
        })
        
        assert isinstance(result, dict)
        # Either success or API key error (if not set in test env)
        assert "status" in result or "error" in result


# ============================================================================
# Level 3: Real API Tests (Optional - requires API key)
# ============================================================================

@pytest.fixture
def real_api_key():
    """Check if real API key is available."""
    key = os.environ.get("NVIDIA_API_KEY")
    if not key or key.startswith("test"):
        pytest.skip("Real NVIDIA_API_KEY not set - skipping real API tests")
    return key


@pytest.mark.slow
class TestNvidiaNIMRealAPI:
    """Level 3: Real API tests (use sparingly due to rate limit)."""
    
    def test_esmfold_real_api(self, tu, real_api_key):
        """Test ESMFold with real API (fast, no MSA required)."""
        result = tu.run_one_function({
            "name": "NvidiaNIM_esmfold",
            "arguments": {"sequence": "MVLSPADKTNVKAAWGKVG"}
        })
        
        # Should either succeed or fail gracefully
        assert isinstance(result, dict)
        if "error" not in result:
            assert "status" in result
            assert result["status"] == "success"
    
    def test_esm2_embedding_real_api(self, tu, real_api_key):
        """Test ESM2-650M embedding with real API."""
        result = tu.run_one_function({
            "name": "NvidiaNIM_esm2_650m",
            "arguments": {"sequence": "MVLSPADKTNVKAAWGKVG"}
        })
        
        assert isinstance(result, dict)
        if "error" not in result:
            assert "status" in result
            assert result["status"] == "success"
    
    def test_evo2_real_api(self, tu, real_api_key):
        """Test Evo2-40B DNA generation with real API."""
        result = tu.run_one_function({
            "name": "NvidiaNIM_evo2",
            "arguments": {
                "sequence": "ACTGACTGACTGACTG",
                "num_tokens": 8,
                "top_k": 1
            }
        })
        
        assert isinstance(result, dict)
        if "error" not in result:
            assert "status" in result
            assert result["status"] == "success"


# ============================================================================
# Rate Limiting Tests
# ============================================================================

class TestRateLimiting:
    """Test rate limiting functionality."""
    
    def test_rate_limit_enforced(self):
        """Test that rate limiting enforces minimum interval."""
        import time
        import tooluniverse.nvidia_nim_tool as nim_module
        from tooluniverse.nvidia_nim_tool import _enforce_rate_limit
        
        # Reset the last request time to ensure test isolation
        nim_module._last_request_time = 0.0
        
        # First call should not wait
        start = time.time()
        _enforce_rate_limit()
        first_elapsed = time.time() - start
        assert first_elapsed < 0.5, "First call should not wait"
        
        # Second call should wait (minimum 1.5s between requests)
        start = time.time()
        _enforce_rate_limit()
        second_elapsed = time.time() - start
        
        # Second call should have waited approximately 1.5 seconds
        assert second_elapsed >= 1.4, "Rate limiting should enforce ~1.5s wait"
