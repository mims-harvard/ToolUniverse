"""
ToolUniverse Profile Configuration Management

This module provides tools for loading, validating, and managing ToolUniverse Profile configurations.
Profile allows users to define collections of tools with specific configurations,
LLM settings, and hooks for advanced scientific workflows.

Main Components:
- ProfileLoader: Loads Profile configurations from various sources (HuggingFace, local files, URLs)
- ProfileValidator: Validates Profile configurations using JSON Schema
- ValidationError: Exception raised when configuration validation fails

Usage:
    from tooluniverse.profile import ProfileLoader, validate_profile_config

    # Load a Profile configuration
    loader = ProfileLoader()
    config = loader.load("hf:user/repo")

    # Validate a configuration
    is_valid, errors = validate_profile_config(config)
"""

from .loader import ProfileLoader
from .validator import (
    validate_profile_config,
    validate_with_schema,
    validate_yaml_file_with_schema,
    validate_yaml_format_by_template,
    validate_yaml_file,
    fill_defaults,
    ValidationError,
    PROFILE_SCHEMA,
)

__all__ = [
    "ProfileLoader",
    "validate_profile_config",
    "validate_with_schema",
    "validate_yaml_file_with_schema",
    "validate_yaml_format_by_template",
    "validate_yaml_file",
    "fill_defaults",
    "ValidationError",
    "PROFILE_SCHEMA",
]
