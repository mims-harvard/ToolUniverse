"""
Integration tests for Profile system.
"""

import pytest
import tempfile
import yaml
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from tooluniverse import ToolUniverse
from tooluniverse.profile import ProfileLoader, validate_profile_config, validate_with_schema
# Note: toolspace_schema has been removed, using JSON Schema validation instead


class TestProfileIntegration:
    """Integration tests for Profile system."""
    
    def setup_method(self):
        """Set up test environment."""
        # Clear environment variables
        env_vars_to_clear = [
            "TOOLUNIVERSE_LLM_DEFAULT_PROVIDER",
            "TOOLUNIVERSE_LLM_MODEL_DEFAULT",
            "TOOLUNIVERSE_LLM_TEMPERATURE",
            "TOOLUNIVERSE_LLM_CONFIG_MODE",
        ]
        for var in env_vars_to_clear:
            if var in os.environ:
                del os.environ[var]
    
    def teardown_method(self):
        """Clean up test environment."""
        self.setup_method()
    
    def test_toolspace_loading_integration(self):
        """Test complete Profile loading integration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml_content = """
name: Integration Test Config
version: 1.0.0
description: Test integration
tools:
  include_tools: [BioThings_Explorer, EuropePMC_Guideline_Search]
llm_config:
  mode: default
  default_provider: CHATGPT
  models:
    default: gpt-4o
  temperature: 0.7
"""
            f.write(yaml_content)
            f.flush()
            
            # Test loading with ProfileLoader
            loader = ProfileLoader()
            config = loader.load(f.name)
            
            assert config['name'] == 'Integration Test Config'
            assert config['version'] == '1.0.0'
            assert 'tools' in config
            assert 'llm_config' in config
            assert config['llm_config']['default_provider'] == 'CHATGPT'
        
        # Clean up
        Path(f.name).unlink()
    
    def test_toolspace_with_tooluniverse(self):
        """Test Profile integration with ToolUniverse."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml_content = """
name: ToolUniverse Integration Test
version: 1.0.0
description: Test ToolUniverse integration
tools:
  include_tools: [ArXiv_search_papers, EuropePMC_search_articles]
llm_config:
  mode: default
  default_provider: CHATGPT
  temperature: 0.7
"""
            f.write(yaml_content)
            f.flush()
            
            # Test ToolUniverse with Profile
            tu = ToolUniverse()
            try:
                # Load Profile configuration
                config = tu.load_profile(f.name)
                
                # Verify configuration is loaded
                assert config['name'] == 'ToolUniverse Integration Test'
                assert config['version'] == '1.0.0'
                assert 'tools' in config
                assert 'llm_config' in config
                
                # Verify tools are actually loaded in ToolUniverse
                assert len(tu.all_tools) > 0
                
                # Verify LLM configuration is applied
                assert os.environ.get('TOOLUNIVERSE_LLM_DEFAULT_PROVIDER') == 'CHATGPT'
                assert os.environ.get('TOOLUNIVERSE_LLM_TEMPERATURE') == '0.7'
            finally:
                tu.close()
        
        # Clean up
        Path(f.name).unlink()
    
    def test_profile_llm_config_integration(self):
        """Test Profile LLM configuration integration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml_content = """
name: LLM Config Test
version: 1.0.0
description: Test LLM configuration
tools:
  include_tools: [BioThings_Explorer]
llm_config:
  mode: default
  default_provider: CHATGPT
  models:
    default: gpt-4o
  temperature: 0.8
"""
            f.write(yaml_content)
            f.flush()
            
            # Test LLM configuration application
            tu = ToolUniverse()
            try:
                _ = tu.load_profile(f.name)
                
                # Verify environment variables are set
                assert os.environ.get('TOOLUNIVERSE_LLM_DEFAULT_PROVIDER') == 'CHATGPT'
                assert os.environ.get('TOOLUNIVERSE_LLM_TEMPERATURE') == '0.8'
                assert os.environ.get('TOOLUNIVERSE_LLM_MODEL_DEFAULT') == 'gpt-4o'
            finally:
                tu.close()
        
        # Clean up
        Path(f.name).unlink()
    
    def test_toolspace_validation_integration(self):
        """Test Profile validation integration."""
        # Test valid configuration
        valid_yaml = """
name: Validation Test
version: 1.0.0
description: Test validation
tools:
  include_tools: [tool1, tool2]
llm_config:
  mode: default
  default_provider: CHATGPT
"""
        
        is_valid, errors, config = validate_with_schema(valid_yaml, fill_defaults_flag=True)
        assert is_valid
        assert len(errors) == 0
        assert config['name'] == 'Validation Test'
        assert config['tags'] == []  # Default value filled
        
        # Test invalid configuration (missing required 'version')
        invalid_yaml = """
name: Invalid Test
llm_config:
  mode: not_a_valid_mode_value
"""

        is_valid, errors, config = validate_with_schema(invalid_yaml, fill_defaults_flag=False)
        assert not is_valid
        assert len(errors) > 0
    
    def test_toolspace_hooks_integration(self):
        """Test Profile hooks integration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml_content = """
name: Hooks Test
version: 1.0.0
description: Test hooks integration
tools:
  include_tools: [BioThings_Explorer]
hooks:
  - type: output_summarization
    enabled: true
    config:
      max_length: 100
"""
            f.write(yaml_content)
            f.flush()
            
            # Test ToolUniverse with hooks
            tu = ToolUniverse()
            try:
                tools = tu.load_profile(f.name)
                
                # Verify hooks are configured
                assert len(tools) > 0
                # Note: Hook verification would require checking ToolUniverse's internal state
            finally:
                tu.close()
        
        # Clean up
        Path(f.name).unlink()
    
    def test_toolspace_required_env_integration(self):
        """Test Profile required_env integration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml_content = """
name: Required Env Test
version: 1.0.0
description: Test required_env integration
tools:
  include_tools: [BioThings_Explorer]
required_env:
  - OPENAI_API_KEY
  - GEMINI_API_KEY
"""
            f.write(yaml_content)
            f.flush()
            
            # Test ToolUniverse with required_env
            tu = ToolUniverse()
            try:
                tools = tu.load_profile(f.name)
                
                # Verify tools are loaded (required_env is for documentation only)
                assert len(tools) > 0
            finally:
                tu.close()
        
        # Clean up
        Path(f.name).unlink()
    