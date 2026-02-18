import yaml
import json
import re
import hashlib
import os
import time
import sys
from typing import Dict, Any, Union, List
from huggingface_hub import hf_hub_download
from pydantic._internal._model_construction import ModelMetaclass


def download_from_hf(tool_config):
    # Extract dataset configuration
    hf_parameters = tool_config.get("hf_dataset_path")
    relative_local_path = hf_parameters.get("save_to_local_dir")

    # Compute absolute path to save locally
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

    # If not provided or empty, default to user cache directory under datasets
    if not relative_local_path or (
        isinstance(relative_local_path, str) and not relative_local_path.strip()
    ):
        absolute_local_dir = os.path.join(get_user_cache_dir(), "datasets")
    else:
        # Expand '~' and environment variables
        expanded_path = os.path.expanduser(os.path.expandvars(relative_local_path))
        if os.path.isabs(expanded_path):
            absolute_local_dir = expanded_path
        else:
            absolute_local_dir = os.path.join(project_root, expanded_path)

    # Ensure the directory exists
    os.makedirs(absolute_local_dir, exist_ok=True)

    # Download the CSV from Hugging Face Hub
    try:
        # Prepare download arguments
        download_args = {
            "repo_id": hf_parameters.get("repo_id"),
            "filename": hf_parameters.get("path_in_repo"),
            "repo_type": "dataset",
            "local_dir": absolute_local_dir,
        }

        # Only add token if it's not None and not empty
        token = hf_parameters.get("token")
        if token is not None and token.strip():
            download_args["token"] = token
        else:
            download_args["token"] = False

        downloaded_path = hf_hub_download(**download_args)

        # The downloaded file path is returned by hf_hub_download
        result = {"success": True, "local_path": downloaded_path}
    except Exception as e:
        result = {"success": False, "error": str(e)}

    return result


def get_md5(input_str):
    """Return the hexadecimal MD5 digest of the given string."""
    return hashlib.md5(input_str.encode("utf-8")).hexdigest()


def get_user_cache_dir() -> str:
    """
    Return a cross-platform user cache directory for ToolUniverse.

    macOS: ~/Library/Caches/ToolUniverse
    Linux: $XDG_CACHE_HOME or ~/.cache/tooluniverse
    Windows: %LOCALAPPDATA%\\ToolUniverse\\Cache
    """
    # Allow explicit override via environment variable
    override_dir = os.getenv("TOOLUNIVERSE_TMPDIR")
    if override_dir and override_dir.strip():
        return os.path.expanduser(os.path.expandvars(override_dir))

    platform = sys.platform
    home_dir = os.path.expanduser("~")

    if platform == "darwin":
        return os.path.join(home_dir, "Library", "Caches", "ToolUniverse")

    if platform.startswith("win"):
        local_app_data = os.getenv("LOCALAPPDATA") or os.path.join(
            home_dir, "AppData", "Local"
        )
        return os.path.join(local_app_data, "ToolUniverse", "Cache")

    # Default: Linux/Unix
    xdg_cache = os.getenv("XDG_CACHE_HOME")
    if xdg_cache and xdg_cache.strip():
        return os.path.join(xdg_cache, "tooluniverse")
    return os.path.join(home_dir, ".cache", "tooluniverse")


def yaml_to_dict(yaml_file_path):
    """
    Convert a YAML file to a dictionary.

    Args:
        yaml_file_path (str): Path to the YAML file.

    Returns
        dict or None: Dictionary representation of the YAML file content,
                      or None if the file is not found or has YAML errors.
    """
    try:
        with open(yaml_file_path, "r", encoding="utf-8") as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        print(f"File not found: {yaml_file_path}")
        return None
    except yaml.YAMLError as exc:
        print(f"Error in YAML file: {exc}")
        return None


def read_json_list(file_path):
    """
    Reads a list of JSON objects from a file.

    Parameters
    file_path (str): The path to the JSON file.

    Returns
    list: A list of dictionaries containing the JSON objects.
    """
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data


def evaluate_function_call(tool_definition, function_call):
    # Map for type conversion
    type_map = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
        "pydantic": ModelMetaclass,
    }

    # Normalise arguments: missing key, None, or non-dict types all become {}
    raw_args = function_call.get("arguments")
    if not isinstance(raw_args, dict):
        function_call = dict(function_call)  # shallow copy so we don't mutate caller
        function_call["arguments"] = {}

    # Check if the function name matches
    if tool_definition["name"] != function_call["name"]:
        return False, "Function name does not match."

    # Handle the case where properties is None (no arguments expected)
    if tool_definition["parameter"]["properties"] is None:
        # If properties is None, the function should not have any arguments
        if function_call.get("arguments") and len(function_call["arguments"]) > 0:
            return False, "This function does not accept any arguments."
        return True, "Function call is valid."

    # Check if all required parameters are present
    required_params = [
        key
        for key, value in tool_definition["parameter"]["properties"].items()
        if value.get("required", False)
    ]
    missing_params = [
        param for param in required_params if param not in function_call["arguments"]
    ]
    if missing_params:
        return False, f"Missing required parameters: {missing_params}"

    # Check if all provided parameters are valid and their data types are correct
    valid_params = tool_definition["parameter"]["properties"]
    invalid_params = []
    type_mismatches = []

    for param, value in function_call["arguments"].items():
        # Skip validation for special parameters that are handled internally
        if param == "_tooluniverse_stream":
            continue
        if param not in valid_params:
            invalid_params.append(param)
        else:
            param_schema = valid_params[param]

            # Handle both simple and complex parameter schemas
            expected_type = None

            # Case 1: Simple schema with direct "type" field
            if "type" in param_schema:
                expected_type = param_schema["type"]
                # Handle list-style type (e.g., ["string", "null"]) - treat as nullable
                if isinstance(expected_type, list):
                    # Allow None for nullable types
                    if value is None and "null" in expected_type:
                        continue
                    # Extract primary non-null type
                    non_null_types = [t for t in expected_type if t != "null"]
                    expected_type = non_null_types[0] if non_null_types else None

            # Case 2: Complex schema with "anyOf" (common in MCP tools)
            elif "anyOf" in param_schema:
                # Extract the primary type from anyOf, ignoring null types
                for type_option in param_schema["anyOf"]:
                    if type_option.get("type") and type_option["type"] != "null":
                        expected_type = type_option["type"]
                        break

            # Case 3: Complex schema with "oneOf" (e.g., string or array)
            elif "oneOf" in param_schema:
                # For oneOf, we need to check if the value matches any of the types
                # Extract all non-null types from oneOf
                one_of_types = []
                for type_option in param_schema["oneOf"]:
                    if type_option.get("type") and type_option["type"] != "null":
                        one_of_types.append(type_option["type"])

                # Check if value matches any of the oneOf types
                value_matches = False
                for one_of_type in one_of_types:
                    if one_of_type == "array" and isinstance(value, list):
                        # For array type, also check items if specified
                        items_schema = None
                        for type_option in param_schema["oneOf"]:
                            if type_option.get("type") == "array":
                                items_schema = type_option.get("items", {})
                                break
                        # If items schema exists, validate items (simplified check)
                        if items_schema:
                            items_type = items_schema.get("type", "string")
                            if all(
                                isinstance(item, type_map.get(items_type, str))
                                for item in value
                            ):
                                value_matches = True
                                break
                        else:
                            value_matches = True
                            break
                    elif one_of_type in type_map and isinstance(
                        value, type_map[one_of_type]
                    ):
                        value_matches = True
                        break

                if value_matches:
                    # Value matches one of the oneOf types, validation passes - skip to next parameter
                    continue
                else:
                    # Value doesn't match any oneOf type
                    type_mismatches.append(
                        (param, f"oneOf{one_of_types}", type(value).__name__)
                    )
                    # Continue to next parameter (don't fall through to expected_type check)
                    continue

            # If we still don't have a type, skip validation for this parameter
            if not expected_type:
                continue

            if expected_type not in type_map:
                return False, f"Unsupported parameter type: {expected_type}"

            # Special handling for 'number' type which should accept both int and float
            if expected_type == "number":
                if not isinstance(value, (int, float)):
                    type_mismatches.append((param, expected_type, type(value).__name__))
            else:
                if not isinstance(value, type_map[expected_type]):
                    type_mismatches.append((param, expected_type, type(value).__name__))

    if invalid_params:
        return False, f"Invalid parameters provided: {invalid_params}"

    if type_mismatches:
        return False, f"Type mismatches: {type_mismatches}"

    return True, "Function call is valid."


def evaluate_function_call_from_toolbox(toolbox, function_call):
    tool_name = function_call["name"]
    this_tool_dec = toolbox.tool_specification(tool_name, return_prompt=True)
    if this_tool_dec is None:
        return False, "Tool not found."
    results, results_message = evaluate_function_call(this_tool_dec, function_call)
    return results, results_message


def compare_function_calls(
    pred_function_call, gt_function_call, compare_arguments=True, compare_value=True
):
    # Extracting the name and arguments from the predicted function call
    pred_name = pred_function_call["name"]
    pred_arguments = pred_function_call["arguments"]

    # Extracting the name and arguments from the ground truth function call
    gt_name = gt_function_call["name"]
    gt_arguments = gt_function_call["arguments"]

    # Compare function names
    if pred_name != gt_name:
        return False, "Function names do not match."

    if compare_arguments:
        # Compare arguments
        if set(pred_arguments.keys()) != set(gt_arguments.keys()):
            missing_in_pred = set(gt_arguments.keys()) - set(pred_arguments.keys())
            missing_in_gt = set(pred_arguments.keys()) - set(gt_arguments.keys())
            return (
                False,
                f"Argument keys do not match. Missing in predicted: {missing_in_pred}, Missing in ground truth: {missing_in_gt}",
            )
    if compare_value:
        # Compare argument values
        mismatched_values = []
        for key in pred_arguments:
            if pred_arguments[key] != gt_arguments[key]:
                mismatched_values.append((key, pred_arguments[key], gt_arguments[key]))

        if mismatched_values:
            return False, f"Argument values do not match: {mismatched_values}"

    return True, "Function calls match."


def extract_function_call_json(lst, return_message=False, verbose=True, format="llama"):
    # Handle different input types
    if isinstance(lst, dict):
        if return_message:
            return lst, ""
        return lst
    elif isinstance(lst, list):
        # Check if it's a list of function call dictionaries
        if all(isinstance(item, dict) and "name" in item for item in lst):
            if return_message:
                return lst, ""
            return lst
        # Otherwise, treat as string list to join
        result_str = "".join(lst)
    else:
        # Single string or other type
        result_str = str(lst)

    if verbose:
        print("\033[1;34mPossible LLM outputs for function call:\033[0m", result_str)
    try:
        function_call_json = json.loads(result_str.strip())
        if return_message:
            return function_call_json, ""
        return function_call_json
    except json.JSONDecodeError:
        try:
            if format == "llama":
                index_start = result_str.find("[TOOL_CALLS]")
                index_end = result_str.find("</s>")
                if index_end == -1:
                    index_end = result_str.find("<|eom_id|>")
                if index_end == -1:
                    function_call_str = result_str[index_start + len("[TOOL_CALLS]") :]
                else:
                    function_call_str = result_str[
                        index_start + len("[TOOL_CALLS]") : index_end
                    ]
                function_call_json = json.loads(function_call_str.strip())
            elif format == "qwen":
                index_start = result_str.find("<tool_call>")
                function_call_str = result_str[index_start:]

                pattern = re.compile(r"<tool_call>(.*?)</tool_call>", re.DOTALL)
                matches = pattern.findall(function_call_str)
                function_call_json = []

                for match in matches:
                    # Clean up the JSON string
                    json_str = match.strip()
                    data = json.loads(json_str)
                    function_call_json.append(data)

            if return_message:
                message = result_str[:index_start]
                return function_call_json, message
            return function_call_json

        except json.JSONDecodeError as e:
            print("Not a function call:", e)
            if return_message:
                return None, result_str
            return None


def format_error_response(
    error: Exception, tool_name: str = None, context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Format error responses in a consistent structure.

    This function ensures all error responses follow the same format for better
    error handling and debugging.

    Args:
        error (Exception): The error that occurred
        tool_name (str, optional): Name of the tool that failed
        context (Dict[str, Any], optional): Additional context about the error

    Returns
        Dict[str, Any]: Standardized error response
    """
    from .exceptions import ToolError

    # If it's already a ToolError, use its structured format
    if isinstance(error, ToolError):
        return {
            "error": str(error),
            "error_type": error.error_type,
            "retriable": error.retriable,
            "next_steps": error.next_steps,
            "details": error.details,
            "tool_name": tool_name,
            "timestamp": time.time(),
        }

    # For regular exceptions, create a basic structure
    return {
        "error": str(error),
        "error_type": type(error).__name__,
        "retriable": False,
        "next_steps": [],
        "details": context or {},
        "tool_name": tool_name,
        "timestamp": time.time(),
    }


def get_parameter_schema(tool_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get parameter schema from tool configuration.

    Args:
        tool_config (Dict[str, Any]): Tool configuration dictionary

    Returns
        Dict[str, Any]: Parameter schema dictionary
    """
    return tool_config.get("parameter", {})


def validate_query(query: Dict[str, Any]) -> bool:
    """
    Validate a query dictionary for required fields and structure.

    Args:
        query (Dict[str, Any]): The query dictionary to validate

    Returns
        bool: True if query is valid, False otherwise
    """
    if not isinstance(query, dict):
        return False

    # Check for basic required fields (customize based on your needs)
    required_fields = ["query", "parameters"]
    for field in required_fields:
        if field not in query:
            return False

    # Additional validation logic can be added here
    return True


def normalize_gene_symbol(gene_symbol: str) -> str:
    """
    Normalize a gene symbol to standard format.

    Args:
        gene_symbol (str): The gene symbol to normalize

    Returns
        str: Normalized gene symbol
    """
    if not isinstance(gene_symbol, str):
        return str(gene_symbol)

    # Convert to uppercase and strip whitespace
    normalized = gene_symbol.strip().upper()

    # Remove common prefixes/suffixes if needed
    # This is a basic implementation - customize as needed
    normalized = re.sub(r"^GENE[-_]?", "", normalized)
    normalized = re.sub(r"[-_]?GENE$", "", normalized)

    return normalized


def format_api_response(
    response_data: Any, format_type: str = "json"
) -> Union[str, Dict[str, Any], List[Any]]:
    """
    Format API response data into a standardized format.

    Args:
        response_data (Any): The response data to format
        format_type (str): The desired output format ('json', 'pretty', 'minimal')

    Returns
        Union[str, Dict[str, Any]]: Formatted response
    """
    if format_type == "json":
        if isinstance(response_data, (dict, list)):
            return response_data
        else:
            return {"data": response_data, "status": "success"}

    elif format_type == "pretty":
        if isinstance(response_data, dict):
            return json.dumps(response_data, indent=2, ensure_ascii=False)
        else:
            return json.dumps(
                {"data": response_data, "status": "success"},
                indent=2,
                ensure_ascii=False,
            )

    elif format_type == "minimal":
        if isinstance(response_data, dict) and "data" in response_data:
            return response_data["data"]
        else:
            return response_data

    else:
        return response_data


def validate_hook_config(config: Dict[str, Any]) -> bool:
    """
    Validate hook configuration for correctness and completeness.

    This function checks that the hook configuration contains all required
    fields and that the structure is valid for the hook system.

    Args:
        config (Dict[str, Any]): Hook configuration to validate

    Returns
        bool: True if configuration is valid, False otherwise
    """
    try:
        # Check for required top-level fields
        if not isinstance(config, dict):
            return False

        # Validate global settings if present
        if "global_settings" in config:
            global_settings = config["global_settings"]
            if not isinstance(global_settings, dict):
                return False

        # Validate hooks array
        if "hooks" in config:
            hooks = config["hooks"]
            if not isinstance(hooks, list):
                return False

            for hook in hooks:
                if not validate_hook_conditions(hook.get("conditions", {})):
                    return False

        # Validate tool-specific hooks
        if "tool_specific_hooks" in config:
            tool_hooks = config["tool_specific_hooks"]
            if not isinstance(tool_hooks, dict):
                return False

            for _tool_name, tool_config in tool_hooks.items():
                if not isinstance(tool_config, dict):
                    return False
                if "hooks" in tool_config:
                    for hook in tool_config["hooks"]:
                        if not validate_hook_conditions(hook.get("conditions", {})):
                            return False

        # Validate category hooks
        if "category_hooks" in config:
            category_hooks = config["category_hooks"]
            if not isinstance(category_hooks, dict):
                return False

            for _category_name, category_config in category_hooks.items():
                if not isinstance(category_config, dict):
                    return False
                if "hooks" in category_config:
                    for hook in category_config["hooks"]:
                        if not validate_hook_conditions(hook.get("conditions", {})):
                            return False

        return True

    except Exception:
        return False


def validate_hook_conditions(conditions: Dict[str, Any]) -> bool:
    """
    Validate hook trigger conditions.

    This function checks that the hook conditions are properly structured
    and contain valid operators and thresholds.

    Args:
        conditions (Dict[str, Any]): Hook conditions to validate

    Returns
        bool: True if conditions are valid, False otherwise
    """
    try:
        if not isinstance(conditions, dict):
            return False

        # Validate output length conditions
        if "output_length" in conditions:
            length_condition = conditions["output_length"]
            if not isinstance(length_condition, dict):
                return False

            # Check for required fields
            if "threshold" not in length_condition:
                return False
            if "operator" not in length_condition:
                return False

            # Validate threshold is numeric
            threshold = length_condition["threshold"]
            if not isinstance(threshold, (int, float)) or threshold < 0:
                return False

            # Validate operator
            operator = length_condition["operator"]
            if operator not in [">", ">=", "<", "<="]:
                return False

        # Validate content type conditions
        if "content_type" in conditions:
            content_type = conditions["content_type"]
            if not isinstance(content_type, str):
                return False
            if content_type not in ["json", "text", "xml", "csv"]:
                return False

        # Validate tool type conditions
        if "tool_type" in conditions:
            tool_type = conditions["tool_type"]
            if not isinstance(tool_type, str):
                return False

        # Validate tool name conditions
        if "tool_name" in conditions:
            tool_name = conditions["tool_name"]
            if not isinstance(tool_name, str):
                return False

        return True

    except Exception:
        return False
