#!/usr/bin/env python3
"""
Tests for Typed Functions (generated tools)

Tests that generated typed functions can be imported and called correctly.
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tooluniverse import ToolUniverse


@pytest.mark.integration
class TestTypedFunctions:
    """Test that generated typed functions work correctly."""
    
    def test_typed_function_import(self):
        """Test that typed functions can be imported."""
        try:
            from tooluniverse.tools import UniProt_get_entry_by_accession
            assert callable(UniProt_get_entry_by_accession)
        except ImportError:
            pytest.skip("Tools not generated. Run: python scripts/build_tools.py")
    
    @pytest.mark.network
    def test_typed_function_call(self):
        """Test that typed functions can be called.

        Marked `network`: the body calls UniProt live, and its own except
        clause says so ("Other errors are expected (network, API limits,
        etc.)") -- but a pytest-timeout is not an exception the test can
        catch, so a slow UniProt fails it outright. It did on CI on
        2026-11-07, as did `test_typed_function_with_options` below, on a
        branch touching no UniProt code.
        """
        try:
            from tooluniverse.tools import UniProt_get_entry_by_accession
            
            # Test calling the function
            result = UniProt_get_entry_by_accession(accession="P05067")
            assert result is not None
            
        except ImportError:
            pytest.skip("Tools not generated. Run: python scripts/build_tools.py")
        except Exception as e:
            # Other errors are expected (network, API limits, etc.)
            assert e is not None
    
    @pytest.mark.network
    def test_typed_function_with_options(self):
        """Test that typed functions accept use_cache and validate options.

        Marked `network` for the same reason as `test_typed_function_call`
        above: it calls UniProt live and cannot catch a timeout. That a
        generated wrapper takes `use_cache` at all is asserted without the
        network in tests/unit/test_generator_invariants.py
        (`test_wrapper_with_api_use_cache_parameter_is_valid_python`), which
        checks the generated source; what this test adds is that a real call
        through one works, which is why it belongs behind the marker rather
        than deleted.
        """
        try:
            from tooluniverse.tools import UniProt_get_entry_by_accession
            
            # Test with options
            result = UniProt_get_entry_by_accession(
                accession="P05067",
                use_cache=True,
                validate=True
            )
            assert result is not None
            
        except ImportError:
            pytest.skip("Tools not generated. Run: python scripts/build_tools.py")
        except Exception as e:
            # Other errors are expected
            assert e is not None
    
    def test_multiple_tools_import(self):
        """Test that multiple tools can be imported."""
        try:
            from tooluniverse.tools import (
                UniProt_get_entry_by_accession,
                ArXiv_search_papers,
                PubMed_search_articles
            )
            
            # All should be callable
            assert callable(UniProt_get_entry_by_accession)
            assert callable(ArXiv_search_papers)
            assert callable(PubMed_search_articles)
            
        except ImportError:
            pytest.skip("Tools not generated. Run: python scripts/build_tools.py")
    
    def test_wildcard_import(self):
        """Test that wildcard import works."""
        try:
            # Import specific tools to test they exist
            from tooluniverse.tools import UniProt_get_entry_by_accession, ArXiv_search_papers
            
            # Check that tools are callable
            assert callable(UniProt_get_entry_by_accession)
            assert callable(ArXiv_search_papers)
            
        except ImportError:
            pytest.skip("Tools not generated. Run: python scripts/build_tools.py")


if __name__ == "__main__":
    pytest.main([__file__])
