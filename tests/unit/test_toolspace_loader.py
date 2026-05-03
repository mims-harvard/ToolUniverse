"""
Unit tests for Profile loader.
"""

import pytest
import tempfile
import yaml
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from tooluniverse.profile import ProfileLoader


class TestProfileLoader:
    """Test ProfileLoader class."""

    def test_profile_loader_initialization(self):
        """Test ProfileLoader can be initialized."""
        loader = ProfileLoader()
        assert loader is not None

    def test_load_local_file(self):
        """Test loading a local YAML file."""
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

            loader = ProfileLoader()
            config = loader.load(f.name)

            assert config['name'] == 'Test Config'
            assert config['version'] == '1.0.0'
            assert config['description'] == 'Test description'
            assert 'tools' in config

        # Clean up
        Path(f.name).unlink()

    def test_load_invalid_yaml_file(self):
        """Test loading a YAML file that fails schema validation (bad enum value)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            invalid_yaml = """
name: Test Config
version: 1.0.0
llm_config:
  mode: not_a_valid_mode_value
"""
            f.write(invalid_yaml)
            f.flush()

            loader = ProfileLoader()

            with pytest.raises(ValueError, match="Configuration validation failed"):
                loader.load(f.name)

        # Clean up
        Path(f.name).unlink()

    def test_load_missing_file(self):
        """Test loading a missing file."""
        loader = ProfileLoader()

        with pytest.raises(ValueError, match="Profile file not found"):
            loader.load("nonexistent.yaml")

    @patch('tooluniverse.profile.loader.hf_hub_download')
    def test_load_huggingface_repo(self, mock_hf_download):
        """Test loading from HuggingFace repository."""
        # Mock HuggingFace download
        mock_hf_download.return_value = str(Path(__file__).parent / "test_data" / "test_config.yaml")

        # Create test file
        test_file = Path(__file__).parent / "test_data" / "test_config.yaml"
        test_file.parent.mkdir(exist_ok=True)
        with open(test_file, 'w') as f:
            yaml.dump({
                'name': 'HF Test Config',
                'version': '1.0.0',
                'description': 'Test from HuggingFace',
                'tools': {'include_tools': ['tool1']}
            }, f)

        loader = ProfileLoader()
        config = loader.load("hf://test-user/test-repo")

        assert config['name'] == 'HF Test Config'
        assert config['version'] == '1.0.0'

        # Clean up
        test_file.unlink()
        test_file.parent.rmdir()

    @patch('requests.get')
    def test_load_http_url(self, mock_get):
        """Test loading from HTTP URL."""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
name: HTTP Test Config
version: 1.0.0
description: Test from HTTP
tools:
  include_tools: [tool1, tool2]
"""
        mock_get.return_value = mock_response

        loader = ProfileLoader()
        config = loader.load("https://example.com/config.yaml")

        assert config['name'] == 'HTTP Test Config'
        assert config['version'] == '1.0.0'
        assert 'tools' in config

    def test_load_with_validation_error(self):
        """Test loading with validation error (bad enum value for llm_config.mode)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            invalid_config = """
name: Test Config
version: 1.0.0
description: Test description
llm_config:
  mode: not_a_valid_mode_value
"""
            f.write(invalid_config)
            f.flush()

            loader = ProfileLoader()

            with pytest.raises(ValueError, match="Configuration validation failed"):
                loader.load(f.name)

        # Clean up
        Path(f.name).unlink()

    def test_extends_non_string_raises_clear_error(self):
        """Test that a non-string extends value raises a clear ValueError before validation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            # extends: [a, b] is not a string — should fail with a useful message
            f.write("name: test\nversion: 1.0.0\nextends:\n  - base1\n  - base2\n")
            f.flush()

            loader = ProfileLoader()

            with pytest.raises(ValueError, match="string URI"):
                loader.load(f.name)

        Path(f.name).unlink()

    def test_extends_circular_raises_clear_error(self):
        """Test that a self-referential extends raises a Circular error."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.yaml', delete=False
        ) as f:
            f.flush()
            fname = f.name

        # Write the file to reference itself
        Path(fname).write_text(
            f"name: self-ref\nversion: 1.0.0\nextends: {fname}\n"
        )

        loader = ProfileLoader()

        with pytest.raises(ValueError, match="Circular"):
            loader.load(fname)

        Path(fname).unlink()

    def test_extends_merges_base_and_child(self):
        """Test that extends deep-merges the base config and the child takes precedence."""
        loader = ProfileLoader()

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.yaml', delete=False
        ) as base_f:
            base_f.write(
                "name: base\nversion: 1.0.0\ndescription: from base\n"
                "tags:\n  - base-tag\n"
            )
            base_f.flush()
            base_path = base_f.name

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.yaml', delete=False
        ) as child_f:
            child_f.write(
                f"name: child\nversion: 2.0.0\nextends: {base_path}\n"
                "tags:\n  - child-tag\n"
            )
            child_f.flush()
            child_path = child_f.name

        try:
            config = loader.load(child_path)
            assert config['name'] == 'child'          # child overrides base
            assert config['version'] == '2.0.0'       # child overrides base
            assert config['description'] == 'from base'  # inherited from base
            assert config['tags'] == ['child-tag']    # child replaces, not appends
            assert 'extends' not in config            # stripped after resolution
        finally:
            Path(base_path).unlink()
            Path(child_path).unlink()
