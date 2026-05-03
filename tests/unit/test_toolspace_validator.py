"""
Unit tests for Profile validator.
"""

import pytest
import tempfile
import yaml
from pathlib import Path

from tooluniverse.profile import (
    validate_profile_config,
    validate_with_schema,
    validate_yaml_file_with_schema,
    validate_yaml_format_by_template,
    PROFILE_SCHEMA
)


class TestValidateProfileConfig:
    """Test validate_profile_config function."""

    def test_valid_config(self):
        """Test validating a valid configuration."""
        config = {
            "name": "Test Config",
            "version": "1.0.0",
            "tools": {
                "categories": ["ChEMBL"]
            },
            "llm_config": {
                "mode": "default",
                "default_provider": "CHATGPT"
            }
        }

        is_valid, errors = validate_profile_config(config)
        assert is_valid
        assert len(errors) == 0

    def test_missing_required_fields(self):
        """Test validation with missing required fields."""
        config = {
            "version": "1.0.0"
            # Missing name (the only required field)
        }

        is_valid, errors = validate_profile_config(config)
        assert not is_valid
        assert "name" in str(errors)

    def test_invalid_llm_mode(self):
        """Test validation with invalid LLM mode."""
        config = {
            "name": "Test Config",
            "version": "1.0.0",
            "llm_config": {
                "mode": "invalid_mode"
            }
        }

        is_valid, errors = validate_profile_config(config)
        assert not is_valid
        assert "mode" in str(errors)


class TestValidateWithSchema:
    """Test validate_with_schema function."""

    def test_valid_yaml_with_defaults(self):
        """Test validating YAML with default value filling."""
        yaml_content = """
name: Test Config
version: 1.0.0
description: Test description
tools:
  include_tools: [tool1, tool2]
"""

        is_valid, errors, config = validate_with_schema(yaml_content, fill_defaults_flag=True)
        assert is_valid
        assert len(errors) == 0
        assert config['name'] == 'Test Config'
        assert config['tags'] == []  # Default value filled
        assert 'tools' in config

    def test_invalid_yaml_structure(self):
        """Test validation with truly invalid field values (not just unknown fields)."""
        yaml_content = """
name: Test Config
version: 1.0.0
llm_config:
  mode: not_a_valid_mode_value
"""

        is_valid, errors, config = validate_with_schema(yaml_content, fill_defaults_flag=False)
        assert not is_valid
        assert len(errors) > 0

    def test_missing_required_fields(self):
        """Test validation with missing required fields."""
        yaml_content = """
version: "1.0.0"
# Missing name (the only required field)
"""

        is_valid, errors, config = validate_with_schema(yaml_content, fill_defaults_flag=False)
        assert not is_valid
        assert "name" in str(errors)


class TestValidateYamlFileWithSchema:
    """Test validate_yaml_file_with_schema function."""

    def test_valid_file(self):
        """Test validating a valid YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml_content = """
name: Test Config
version: 1.0.0
description: Test description
tools:
  include_tools: [tool1, tool2]
"""
            f.write(yaml_content)
            f.flush()

            is_valid, errors, config = validate_yaml_file_with_schema(f.name, fill_defaults_flag=True)
            assert is_valid
            assert len(errors) == 0
            assert config['name'] == 'Test Config'

        # Clean up
        Path(f.name).unlink()

    def test_nonexistent_file(self):
        """Test validation with nonexistent file."""
        is_valid, errors, config = validate_yaml_file_with_schema("nonexistent.yaml")
        assert not is_valid
        assert "File not found" in str(errors)


class TestValidateYamlFormatByTemplate:
    """Test validate_yaml_format_by_template function."""

    def test_valid_yaml_format(self):
        """Test validating valid YAML format."""
        yaml_content = """
name: Test Config
version: 1.0.0
description: Test description
tools:
  include_tools: [tool1, tool2]
"""

        is_valid, errors = validate_yaml_format_by_template(yaml_content)
        assert is_valid
        assert len(errors) == 0

    def test_invalid_yaml_format(self):
        """Test validating invalid YAML format (bad enum value)."""
        yaml_content = """
name: Test Config
version: 1.0.0
llm_config:
  mode: not_a_valid_mode_value
"""

        is_valid, errors = validate_yaml_format_by_template(yaml_content)
        assert not is_valid
        assert len(errors) > 0


class TestProfileSchema:
    """Test PROFILE_SCHEMA definition."""

    def test_schema_structure(self):
        """Test that PROFILE_SCHEMA has correct structure."""
        assert PROFILE_SCHEMA['type'] == 'object'
        assert 'name' in PROFILE_SCHEMA['properties']
        assert 'version' in PROFILE_SCHEMA['properties']
        assert 'tools' in PROFILE_SCHEMA['properties']
        assert 'llm_config' in PROFILE_SCHEMA['properties']
        assert 'hooks' in PROFILE_SCHEMA['properties']
        assert 'required_env' in PROFILE_SCHEMA['properties']

    def test_schema_required_fields(self):
        """Test that required fields are correctly defined."""
        assert 'name' in PROFILE_SCHEMA['required']
        assert 'version' not in PROFILE_SCHEMA['required']  # version is optional, defaults to "1.0.0"

    def test_schema_default_values(self):
        """Test that default values are correctly defined."""
        assert PROFILE_SCHEMA['properties']['version']['default'] == '1.0.0'
        assert PROFILE_SCHEMA['properties']['tags']['default'] == []
        assert PROFILE_SCHEMA['properties']['llm_config']['properties']['mode']['default'] == 'default'
        assert PROFILE_SCHEMA['properties']['hooks']['items']['properties']['enabled']['default'] is True
