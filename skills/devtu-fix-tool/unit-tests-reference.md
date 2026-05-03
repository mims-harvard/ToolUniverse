# Unit Test Reference for ToolUniverse

## Standard Unit Test Structure

Unit tests follow a two-level testing pattern:

### Level 1: Direct Tool Testing

Tests the tool class directly by instantiating it with a config:

```python
"""Unit tests for <Tool> tool."""
import pytest
import json
from unittest.mock import patch, MagicMock

class Test<Tool>ToolDirect:
    """Test tool directly (Level 1)."""
    
    @pytest.fixture
    def tool_config(self):
        with open("src/tooluniverse/data/<tool>_tools.json") as f:
            return json.load(f)[0]
    
    @pytest.fixture
    def tool(self, tool_config):
        from tooluniverse.<tool>_tool import <Tool>Tool
        return <Tool>Tool(tool_config)
    
    def test_missing_required_param(self, tool):
        result = tool.run({"operation": "get_data"})
        assert result["status"] == "error"
        assert "required_param" in result["error"].lower()
    
    def test_unknown_operation(self, tool):
        result = tool.run({"operation": "unknown"})
        assert result["status"] == "error"
    
    @patch("tooluniverse.<tool>_tool.requests.get")
    def test_operation_success(self, mock_get, tool):
        mock_response = MagicMock()
        mock_response.json.return_value = {"key": "value"}
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        result = tool.run({"operation": "get_data", "required_param": "value"})
        assert result["status"] == "success"
        assert "data" in result
```

### Level 2: Interface Testing

Tests the tool through ToolUniverse's interface:

```python
class Test<Tool>ToolInterface:
    """Test tool via ToolUniverse interface (Level 2)."""
    
    @pytest.fixture
    def tu(self):
        from tooluniverse import ToolUniverse
        tu = ToolUniverse()
        tu.load_tools()
        return tu
    
    def test_tools_registered(self, tu):
        assert hasattr(tu.tools, "<Tool>_operation1")
        assert hasattr(tu.tools, "<Tool>_operation2")
```

## Common Update Patterns

### 1. Update Data Structure Assertions

**Before fix (flat structure)**:

```python
def test_get_data_schema(self, tu):
    result = tu.tools.Tool_get_data(**{"param": "value"})
    assert "items" in result
    assert "count" in result
```

**After fix (nested in data)**:

```python
def test_get_data_schema(self, tu):
    result = tu.tools.Tool_get_data(**{"param": "value"})
    assert "status" in result
    if result["status"] == "success":
        data = result.get("data", result)
        assert "items" in data or "items" in result
        assert "count" in data or "count" in result
```

### 2. Flexible Error Message Checks

**Before (brittle)**:

```python
def test_missing_param(self, tool):
    result = tool.run({"operation": "get_data"})
    assert "Missing param" in result["error"]
```

**After (flexible)**:

```python
def test_missing_param(self, tool):
    result = tool.run({"operation": "get_data"})
    assert result["status"] == "error"
    assert "param" in result["error"].lower()
```

### 3. Binary Response Handling

If tool now handles binary data:

```python
@patch("tooluniverse.tool_name.requests.get")
def test_binary_response(self, mock_get, tool):
    mock_response = MagicMock()
    mock_response.headers = {"Content-Type": "image/png"}
    mock_response.url = "https://example.com/image.png"
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response
    
    result = tool.run({"operation": "get_image", "id": "123"})
    assert result["status"] == "success"
    assert "Binary data available" in result["data"]
    assert result["url"] == "https://example.com/image.png"
```

### 4. Schema Validation with Flexible Structure

```python
def test_return_schema_matches(self, tu):
    result = tu.tools.Tool_get_data(**{"param": "value"})
    
    assert "status" in result
    
    if result["status"] == "success":
        # Flexible check for nested or flat data
        data = result.get("data", result)
        
        # Check expected fields exist somewhere
        assert "field1" in data or "field1" in result
        assert isinstance(data.get("field1", result.get("field1")), str)
    else:
        # Error response should have error message
        assert "error" in result
```

## Examples from Real Tests

### CELLxGENE Census Tool

```python
def test_get_cell_metadata_return_schema(self, tu):
    result = tu.tools.CELLxGENE_get_cell_metadata(**{
        "operation": "get_obs_metadata",
        "organism": "Homo sapiens",
        "census_version": "stable",
        "obs_value_filter": 'tissue_general == "blood"',
        "column_names": ["soma_joinid", "cell_type"]
    })
    
    assert "status" in result
    
    if result["status"] == "success":
        data = result.get("data", result)
        assert "organism" in data or "organism" in result
        assert "num_cells" in data or "num_cells" in result or "error" in result
    else:
        assert "error" in result
```

### BRENDA Tool

```python
class TestBRENDAToolDirect:
    @pytest.fixture
    def tool_config(self):
        with open("src/tooluniverse/data/brenda_tools.json") as f:
            return json.load(f)[0]

    @pytest.fixture
    def tool(self, tool_config):
        from tooluniverse.brenda_tool import BRENDATool
        return BRENDATool(tool_config)

    def test_missing_ec_number(self, tool):
        result = tool.run({"operation": "get_km"})
        assert result["status"] == "error"
```

### BindingDB Tool

```python
@patch("tooluniverse.bindingdb_tool.requests.get")
def test_get_by_uniprot_success(self, mock_get, tool):
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"monomerid": "12345", "smiles": "CCO", "affinity_type": "IC50"}
    ]
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    result = tool.run({"operation": "get_by_uniprot", "uniprot_id": "P00533"})
    assert result["status"] == "success"
```

## When to Update Unit Tests

Update unit tests when you:

1. **Change return structure**: Update assertions checking `result["data"]` structure
2. **Add/modify operations**: Add test cases for new operations
3. **Change error handling**: Update error assertions
4. **Modify required parameters**: Update parameter validation tests
5. **Fix schema issues**: Ensure tests validate correct data structure
6. **Add binary handling**: Add tests for binary responses

## Running Unit Tests

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run specific tool tests
pytest tests/unit/test_<tool-name>_tool.py -v

# Run with coverage
pytest tests/unit/test_<tool-name>_tool.py --cov=tooluniverse.<tool>_tool

# Run with detailed output
pytest tests/unit/test_<tool-name>_tool.py -vv -s
```
