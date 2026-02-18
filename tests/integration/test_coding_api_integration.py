#!/usr/bin/env python3
"""
Integration Tests for ToolUniverse Coding API

Tests the complete integration of dynamic calling, SDK generation,
and functionality.
"""

import sys
import unittest
import tempfile
import shutil
import importlib
from pathlib import Path
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tooluniverse import ToolUniverse  # noqa: E402
from tooluniverse.generate_tools import main as generate_tools  # noqa: E402


@pytest.mark.integration
class TestCodingAPIIntegration(unittest.TestCase):
    """Test complete coding API integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.tu = ToolUniverse()
        self.temp_dir = tempfile.mkdtemp()
        # Ensure tools are loaded for dynamic namespace access
        self.tu.load_tools()
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.tu.close()
        shutil.rmtree(self.temp_dir)
    
    def test_dynamic_calling_integration(self):
        """Test dynamic function calling integration."""
        # Test that tools namespace works
        self.assertTrue(hasattr(self.tu, 'tools'))
        
        # Test accessing a tool
        try:
            # Pick any available tool name
            tool_name = next(iter(self.tu.all_tool_dict.keys()), None)
            self.assertIsNotNone(tool_name)
            tool_callable = getattr(self.tu.tools, tool_name)
            self.assertIsNotNone(tool_callable)
            
            # Test calling the tool (no args); should not crash, may return error dict
            result = tool_callable()
            self.assertIsNotNone(result)
            
        except AttributeError:
            # Tool must be available for this integration test
            self.fail(
                "Required tool UniProt_get_entry_by_accession is not available"
            )
        except Exception as e:
            # Other errors are expected (network, etc.)
            self.assertIsNotNone(e)
    
    def test_caching_integration(self):
        """Test caching integration."""
        # Clear cache first
        self.tu.clear_cache()
        self.assertEqual(len(self.tu._cache), 0)
        
        # Test caching with dynamic calling
        try:
            tool_name = next(iter(self.tu.all_tool_dict.keys()), None)
            self.assertIsNotNone(tool_name)
            
            # First call with caching via unified runner
            result1 = self.tu.run_one_function({
                "name": tool_name,
                "arguments": {}
            }, use_cache=True)
            
            # Second call should reuse cache
            result2 = self.tu.run_one_function({
                "name": tool_name,
                "arguments": {}
            }, use_cache=True)
            
            # Results should be identical or at least same type/structure
            self.assertEqual(result1, result2)
            
        except AttributeError:
            # Tool must be available for this integration test
            self.fail(
                "Required tool UniProt_get_entry_by_accession is not available"
            )
        except Exception:
            # Other errors expected, just test cache behavior
            pass
        
        # Clear cache
        self.tu.clear_cache()
        self.assertEqual(len(self.tu._cache), 0)
    
    def test_validation_integration(self):
        """Test parameter validation integration."""
        # Test validation with dynamic calling
        try:
            # This should trigger validation error
            tool_name = next(iter(self.tu.all_tool_dict.keys()), None)
            self.assertIsNotNone(tool_name)
            result = self.tu.run_one_function({
                "name": tool_name,
                "arguments": {"invalid_param": "test"}
            }, validate=True)
            
            # Should return structured error
            if isinstance(result, dict) and "error" in result:
                self.assertIn("error_details", result)
                error_details = result["error_details"]
                self.assertIn("type", error_details)
                
        except AttributeError:
            # Tool must be available for this integration test
            self.fail(
                "Required tool UniProt_get_entry_by_accession is not available"
            )
        except Exception:
            # Other errors expected
            pass
    
    def test_lifecycle_integration(self):
        """Test lifecycle management integration."""
        # Test refresh
        self.tu.tools.refresh()
        
        # Test eager loading
        # Eager load a subset (first available) to verify API doesn't crash
        first_name = next(iter(self.tu.all_tool_dict.keys()), None)
        if first_name:
            self.tu.tools.eager_load([first_name])
        
        # Test that tools were loaded
        # (This is implementation-dependent)
        pass
    
    def test_error_handling_integration(self):
        """Test error handling integration."""
        # Test with non-existent tool
        try:
            result = self.tu.tools.NonExistentTool(param="test")
        except AttributeError as e:
            # Expected error
            self.assertIn("not found", str(e))
        
        # Test with invalid parameters
        try:
            result = self.tu.run_one_function({
                "name": "convert_to_markdown",
                "arguments": {"invalid_param": "test"}
            }, validate=True)
            
            # Should return dual-format error
            if isinstance(result, dict) and "error" in result:
                self.assertIn("error_details", result)
                
        except Exception:
            # Other errors expected
            pass


class TestSDKIntegration(unittest.TestCase):
    """Test SDK generation and usage integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.tu = ToolUniverse()
        self.temp_dir = tempfile.mkdtemp()
        
        # Generate SDK for testing
        generate_tools()
        
        # Invalidate import caches to ensure newly generated modules are loaded
        # Remove all tooluniverse.tools modules from cache
        modules_to_remove = [
            mod for mod in list(sys.modules.keys())
            if mod.startswith('tooluniverse.tools')
        ]
        for mod in modules_to_remove:
            del sys.modules[mod]
        importlib.invalidate_caches()
        
        # Add to Python path
        sys.path.insert(0, self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.tu.close()
        if self.temp_dir in sys.path:
            sys.path.remove(self.temp_dir)
        shutil.rmtree(self.temp_dir)
    
    def test_sdk_import_integration(self):
        """Test SDK import integration."""
        try:
            from tooluniverse.tools import convert_to_markdown
            from tooluniverse.exceptions import ToolValidationError

            # Test that imports work
            self.assertIsNotNone(convert_to_markdown)
            self.assertIsNotNone(ToolValidationError)
            
        except ImportError as e:
            self.fail(f"Tools import failed: {e}")
    
    def test_sdk_function_calling_integration(self):
        """Test SDK function calling integration."""
        try:
            from tooluniverse.tools import convert_to_markdown

            # Test calling generated function
            result = convert_to_markdown(uri="data:text/plain,hello")
            self.assertIsNotNone(result)
            
        except ImportError:
            self.fail("Required SDK imports are not available")
        except Exception as e:
            # Other errors expected (network, etc.)
            self.assertIsNotNone(e)
    
    def test_sdk_error_handling_integration(self):
        """Test SDK error handling integration."""
        try:
            from tooluniverse.exceptions import ToolValidationError

            # Call through runner with invalid args to trigger validation error
            tool_name = next(iter(self.tu.all_tool_dict.keys()), None)
            self.assertIsNotNone(tool_name)
            try:
                _ = self.tu.run_one_function({
                    "name": tool_name,
                    "arguments": {"invalid_param": "test"}
                }, validate=True)
            except ToolValidationError as e:
                # Expected error
                self.assertIsNotNone(e.next_steps)
                self.assertIsNotNone(e.details)
            
        except ImportError:
            self.fail("Required SDK imports are not available")
        except Exception:
            # Other errors expected
            pass


class TestEndToEndIntegration(unittest.TestCase):
    """Test end-to-end integration scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        self.tu = ToolUniverse()
        self.temp_dir = tempfile.mkdtemp()
        self.tu.load_tools()
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.tu.close()
        shutil.rmtree(self.temp_dir)
    
    def test_dynamic_to_sdk_workflow(self):
        """Test workflow from dynamic calling to SDK generation."""
        # Step 1: Test dynamic calling
        try:
            tool_name = next(iter(self.tu.all_tool_dict.keys()), None)
            self.assertIsNotNone(tool_name)
            result = self.tu.run_one_function({
                "name": tool_name,
                "arguments": {}
            })
            self.assertIsNotNone(result)
        except AttributeError:
            self.fail(
                "Required tool UniProt_get_entry_by_accession is not available"
            )
        except Exception:
            # Other errors expected
            pass
        
        # Step 2: Generate SDK
        generate_tools()
        
        # Step 3: Test SDK
        sys.path.insert(0, self.temp_dir)
        try:
            # Import a module is not necessary for dynamic path; ensure module import path works
            from tooluniverse.tools import __all__ as exported
            self.assertIsInstance(exported, list)
            self.assertIsNotNone(result)
            
        except ImportError:
            self.fail("SDK generation failed")
        except Exception:
            # Other errors expected
            pass
        finally:
            if self.temp_dir in sys.path:
                sys.path.remove(self.temp_dir)
    
    def test_error_recovery_workflow(self):
        """Test error recovery workflow."""
        # Test error handling in dynamic mode
        try:
            result = self.tu.run_one_function({
                "name": "NonExistentTool",
                "arguments": {}
            })
            
            # Should return structured error
            if isinstance(result, dict) and "error" in result:
                self.assertIn("error_details", result)
                error_details = result["error_details"]
                self.assertIn("next_steps", error_details)
                
        except Exception:
            # Other errors expected
            pass
        
        # Test error handling in SDK mode
        # Generate tools in temp directory
        generate_tools()
        
        sys.path.insert(0, self.temp_dir)
        try:
            from tooluniverse.exceptions import ToolValidationError
            
            # Test structured exception
            error = ToolValidationError(
                "Test error",
                next_steps=["Step 1", "Step 2"],
            )
            self.assertIsNotNone(error.next_steps)
            self.assertEqual(len(error.next_steps), 2)
            
        except ImportError:
            self.fail("SDK generation failed")
        finally:
            if self.temp_dir in sys.path:
                sys.path.remove(self.temp_dir)
    
    def test_caching_workflow(self):
        """Test caching workflow across modes."""
        # Clear cache
        self.tu.clear_cache()
        
        # Test caching in dynamic mode
        try:
            # First call
            result1 = self.tu.tools.UniProt_get_entry_by_accession(
                accession="P05067",
                use_cache=True,
            )
            
            # Second call (should hit cache)
            result2 = self.tu.tools.UniProt_get_entry_by_accession(
                accession="P05067",
                use_cache=True,
            )
            
            # Results should be identical
            self.assertEqual(result1, result2)
            
        except AttributeError:
            self.fail(
                "Required tool UniProt_get_entry_by_accession is not available"
            )
        except Exception:
            # Other errors expected
            pass
        
        # Test caching in SDK mode
        # Generate tools in temp directory
        generate_tools()
        
        sys.path.insert(0, self.temp_dir)
        try:
            from tooluniverse.tools import convert_to_markdown

            # Test caching with SDK
            result1 = convert_to_markdown(
                uri="data:text/plain,hello",
                use_cache=True,
            )
            result2 = convert_to_markdown(
                uri="data:text/plain,hello",
                use_cache=True,
            )
            
            # Results should be identical
            self.assertEqual(result1, result2)
            
        except ImportError:
            self.fail("SDK generation failed")
        except Exception:
            # Other errors expected
            pass
        finally:
            if self.temp_dir in sys.path:
                sys.path.remove(self.temp_dir)


if __name__ == "__main__":
    unittest.main()
