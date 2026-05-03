"""
Tool Metadata Generation Pipeline
Generates comprehensive metadata for a list of tools by extracting details from their configuration files
"""


def compose(arguments, tooluniverse, call_tool):
    """
    Main composition function for Tool Metadata Generation

    Args:
        arguments (dict): Input arguments containing a list of tool config JSONs as well as a tool_type_mappings dict for non-API tools (e.g., {'Databases': ['XMLTool']})
        tooluniverse: ToolUniverse instance
        call_tool: Function to call other tools

    Returns
        list: List of tool metadata dictionaries (JSON-compatible)
    """
    import json
    import warnings
    import uuid
    from collections import Counter

    def _parse_agent_output(output, tool_name="Unknown Tool"):
        """Helper to parse varied agent outputs (JSON string, wrapped dict) into a dict."""
        if isinstance(output, str):
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                print(
                    f"Failed to parse JSON string from {tool_name}; received: {output[:200]}"
                )
                return {}  # Return empty dict on failure to prevent crash

        if isinstance(output, dict) and "success" in output and "result" in output:
            # Handle wrapped output like {'success': True, 'result': '{...}'}
            inner_result = output.get("result")
            if isinstance(inner_result, str) and inner_result.strip():
                try:
                    return json.loads(inner_result)
                except json.JSONDecodeError:
                    print(
                        f"Failed to parse inner result JSON from {tool_name}; using empty metadata."
                    )
                    return {}
            elif isinstance(inner_result, dict):
                return inner_result  # Result is already a dict
            else:
                return {}  # No valid inner result

        return {}

    DEFAULT_TOOL_TYPE_MAPPINGS = {
        "Embedding Store": ["EmbeddingDatabase"],
        "Database": ["XMLTool", "DatasetTool"],
        "Scientific Software Package": ["PackageTool"],
        "AI Agent": ["AgenticTool"],
        "ML Model": [
            "ADMETAITool",
            "AlphaFoldRESTTool",
            "boltz2_docking",
            "compute_depmap24q2_gene_correlations",
            "run_compass_prediction",
            "run_pinnacle_ppi_retrieval",
            "run_transcriptformer_embedding_retrieval",
            "get_abstract_from_patent_app_number",
            "get_claims_from_patent_app_number",
            "get_full_text_from_patent_app_number",
        ],
        "Human Expert Feedback": [
            "mcp_auto_loader_human_expert",
            "consult_human_expert",
            "get_expert_response",
            "get_expert_status",
            "list_pending_expert_requests",
            "submit_expert_response",
        ],
        "MCP": ["MCPAutoLoaderTool", "MCPClientTool", "MCPProxyTool"],
        "Compositional Tool": ["ComposeTool"],
        "Tool Finder Tool": [
            "ToolFinderEmbedding",
            "ToolFinderLLM",
            "ToolFinderKeyword",
        ],
        "Special Tool": ["Finish", "CallAgent"],
    }

    # Step 0: Parse inputs and set up variables
    tool_configs = arguments.get("tool_configs", [])
    tool_type_mappings = arguments.get("tool_type_mappings", {})
    add_existing_tooluniverse_labels = arguments.get(
        "add_existing_tooluniverse_labels", True
    )
    max_new_tooluniverse_labels = arguments.get("max_new_tooluniverse_labels", 0)

    # Merge tool type mappings with defaults, prioritizing user-provided mappings
    for key, value in DEFAULT_TOOL_TYPE_MAPPINGS.items():
        if key not in tool_type_mappings:
            tool_type_mappings[key] = value
    warnings.warn(
        "Warning: Augmenting your provided tool_type_mappings with default tool_type_mappings to ensure compatibility with existing ToolUniverse tools. The default tool_type_mappings are:\n"
        + json.dumps(DEFAULT_TOOL_TYPE_MAPPINGS, indent=4),
        stacklevel=2,
    )

    # Add existing ToolUniverse labels if specified
    tool_labels_set = set()
    if add_existing_tooluniverse_labels:
        # Load existing standardized tool metadata (list of dicts each containing a 'tags' field)
        # Use importlib.resources to avoid absolute paths so this works inside the installed package.
        try:
            try:
                from importlib import resources as importlib_resources  # Py3.9+
            except ImportError:  # pragma: no cover
                import importlib_resources  # type: ignore

            # Access the JSON file inside the package (tooluniverse/website_data/v3_standardized_tags.json)
            json_path = importlib_resources.files("tooluniverse.website_data").joinpath(
                "v3_standardized_tags.json"
            )
            with json_path.open("r", encoding="utf-8") as f:
                existing_metadata_list = json.load(f)

            if isinstance(existing_metadata_list, list):
                for item in existing_metadata_list:
                    if isinstance(item, dict):
                        tags = item.get("tags", [])
                        if isinstance(tags, list):
                            for tag in tags:
                                if isinstance(tag, str) and tag.strip():
                                    tool_labels_set.add(tag.strip())
        except Exception as e:  # Fail gracefully; downstream logic will just proceed without enrichment
            print(f"Failed to load existing ToolUniverse labels: {e}")

    if not tool_configs:
        return []

    # Step 1: Generate detailed metadata for each tool
    all_tool_metadata = []
    for tool_config in tool_configs:
        tool_config_str = json.dumps(tool_config)
        try:
            metadata_params = {
                "tool_config": tool_config_str,
                "tool_type_mappings": tool_type_mappings,
            }
            generated_metadata = {}
            for _ in range(5):  # Retry up to 5 times
                raw_output = call_tool("ToolMetadataGenerator", metadata_params)
                generated_metadata = _parse_agent_output(
                    raw_output, "ToolMetadataGenerator"
                )
                if generated_metadata:  # If the result is not empty, break
                    break
            # Attempt to enrich tags using LabelGenerator if tags are empty or default
            try:
                # Prepare inputs for LabelGenerator
                tool_name = (
                    tool_config.get("name") or generated_metadata.get("name") or ""
                )
                tool_description = (
                    tool_config.get("description")
                    or generated_metadata.get("description")
                    or ""
                )
                # The parameter schema may be nested under parameter->properties
                param_properties = tool_config.get("parameter", {}).get(
                    "properties", {}
                )

                # Convert parameters to a JSON-like string representation (without importing json to keep dependencies minimal)
                # Safe string construction
                def _stringify_params(props):
                    parts = []
                    for k, v in props.items():
                        if isinstance(v, dict):
                            type_val = v.get("type", "unknown")
                            desc_val = v.get("description", "")
                            parts.append(
                                f"\"{k}\": {{ 'type': '{type_val}', 'description': '{desc_val}' }}"
                            )
                        else:
                            parts.append(f'"{k}": ' + repr(v))
                    return "{" + ", ".join(parts) + "}"

                tool_parameters_str = _stringify_params(param_properties)
                category = (
                    tool_config.get("category")
                    or tool_config.get("type")
                    or generated_metadata.get("category")
                    or ""
                )

                label_params = {
                    "tool_name": tool_name,
                    "tool_description": tool_description,
                    "tool_parameters": tool_parameters_str,
                    "category": category,
                    "existing_labels": json.dumps(list(tool_labels_set)),
                }
                label_result = call_tool("LabelGenerator", label_params)
                label_result = _parse_agent_output(label_result, "LabelGenerator")

                # Parse label_result which may be dict or JSON string
                labels = []
                if isinstance(label_result, dict):
                    labels = label_result.get("labels", [])
                # Replace tags
                if labels:
                    generated_metadata["tags"] = labels
            except Exception as tag_exc:
                print(
                    f"Label generation failed for tool {tool_config.get('name', 'N/A')}: {tag_exc}"
                )

            all_tool_metadata.append(generated_metadata)
        except Exception as e:
            print(
                f"Failed to generate metadata for tool {tool_config.get('name', 'N/A')}: {e}"
            )
            # Optionally, append an error object or skip the tool
            all_tool_metadata.append(
                {
                    "error": f"Metadata generation failed for {tool_config.get('name', 'N/A')}",
                    "details": str(e),
                }
            )

    # Step 2: Validate schema
    validated_metadata = []
    schema_template = {
        "id": "",
        "name": "",
        "description": "",
        "detailed_description": "",
        "toolType": "api",
        "tags": [],
        "category": "",
        "lab": "",
        "source": "",
        "version": "v1.0.0",
        "reviewed": False,
        "isValidated": False,
        "usageStats": "0 uses",
        "capabilities": [],
        "limitations": [],
        "parameters": {},
        "inputSchema": {},
        "exampleInput": {},
        "apiEndpoints": [],
    }

    for metadata in all_tool_metadata:
        if "error" in metadata:
            validated_metadata.append(metadata)
            continue

        validated_item = {}
        for key, default_value in schema_template.items():
            value = metadata.get(key, default_value)
            if not isinstance(value, type(default_value)):
                # Attempt to gracefully handle simple type mismatches or reset
                if isinstance(default_value, list) and not isinstance(value, list):
                    value = []
                elif isinstance(default_value, dict) and not isinstance(value, dict):
                    value = {}
                elif isinstance(default_value, str) and not isinstance(value, str):
                    value = str(value) if value is not None else ""
                elif isinstance(default_value, bool) and not isinstance(value, bool):
                    value = bool(value)
                else:
                    value = default_value  # Fallback to default if type is complex/unexpected
            validated_item[key] = value
        validated_metadata.append(validated_item)

    all_tool_metadata = validated_metadata

    # Step 3: Standardize sources and tags using ToolMetadataStandardizer
    try:
        source_list = []
        for tool in all_tool_metadata:
            if "error" not in tool and tool.get("source"):
                source_list.append(tool.get("source"))
        # Standardize sources
        if source_list:
            standardizer_params = {"metadata_list": list(set(source_list))}
            standardized_sources_map = call_tool(
                "ToolMetadataStandardizer", standardizer_params
            )
            standardized_sources_map = _parse_agent_output(
                standardized_sources_map, "ToolMetadataStandardizer"
            )
            print("Standardized sources mapping:", standardized_sources_map)

            # Create a reverse map for easy lookup
            source_to_standard_map = {}
            for standard_name, raw_names in standardized_sources_map.items():
                for raw_name in raw_names:
                    source_to_standard_map[raw_name] = standard_name

            # Update the source in each metadata object
            for tool_metadata in all_tool_metadata:
                if "error" not in tool_metadata:
                    original_source = tool_metadata.get("source")
                    if original_source in source_to_standard_map:
                        tool_metadata["source"] = source_to_standard_map[
                            original_source
                        ]
    except Exception as e:
        print(f"An error occurred during source standardization: {e}")

    try:
        # Step 4: Standardize tags, with an optional second pass to meet label limits
        all_raw_tags = []
        for tool in all_tool_metadata:
            if "error" not in tool and isinstance(tool.get("tags"), list):
                all_raw_tags.extend(tool.get("tags", []))

        # Filter out existing labels before standardization
        tags_to_standardize = [
            tag for tag in set(all_raw_tags) if tag not in tool_labels_set
        ]
        if max_new_tooluniverse_labels <= 0:
            # If no new labels are allowed, skip standardization and just remove new tags
            for tool_metadata in all_tool_metadata:
                if "error" not in tool_metadata and isinstance(
                    tool_metadata.get("tags"), list
                ):
                    original_tags = tool_metadata.get("tags", [])
                    filtered_tags = [
                        tag for tag in original_tags if tag in tool_labels_set
                    ]
                    tool_metadata["tags"] = sorted(list(set(filtered_tags)))
            return (
                all_tool_metadata  # Return early since no further processing is needed
            )

        tag_to_standard_map = {}
        if tags_to_standardize:
            # Iteratively standardize tags for up to 5 passes to meet the label limit.
            current_tags_to_standardize = list(set(tags_to_standardize))
            # This map will store the final standardized version for each original raw tag.
            tag_to_standard_map = {tag: tag for tag in tags_to_standardize}

            for i in range(5):  # Loop for up to 5 standardization passes
                num_tags = len(current_tags_to_standardize)

                # If the number of tags is within the limit, no more standardization is needed.
                if (
                    max_new_tooluniverse_labels > 0
                    and num_tags <= max_new_tooluniverse_labels
                ):
                    print(
                        f"Tag count ({num_tags}) is within the limit ({max_new_tooluniverse_labels}). Stopping standardization."
                    )
                    break

                print(f"Pass {i + 1}: Standardizing {num_tags} tags.")

                # Set the limit for the standardizer tool.
                # Use a default high limit if max_new_tooluniverse_labels is not set, otherwise use the specified limit.
                limit = (
                    max_new_tooluniverse_labels
                    if max_new_tooluniverse_labels > 0
                    else 150
                )

                standardizer_params = {
                    "metadata_list": current_tags_to_standardize,
                    "limit": limit,
                }

                print(f"Pass {i + 1} input tags: ", current_tags_to_standardize)

                # Call the standardizer tool and parse the output, with retries.
                pass_output_map = {}
                for _ in range(5):  # Retry up to 5 times
                    raw_output = call_tool(
                        "ToolMetadataStandardizer", standardizer_params
                    )
                    pass_output_map = _parse_agent_output(
                        raw_output, "ToolMetadataStandardizer"
                    )
                    if pass_output_map:  # If the result is not empty, break
                        break

                print(f"Pass {i + 1} standardized tags mapping:", pass_output_map)

                # Create a reverse map for the current pass for easy lookup.
                # Maps a tag from the input list to its new standardized version.
                pass_reverse_map = {}
                for standard_tag, raw_tags_in_pass in pass_output_map.items():
                    for raw_tag in raw_tags_in_pass:
                        pass_reverse_map[raw_tag] = standard_tag

                # Update the final mapping by chaining the new standardization.
                # For each original tag, find its current mapping and see if it was further standardized in this pass.
                for original_tag, current_standard_tag in tag_to_standard_map.items():
                    # If the current standard tag was part of this pass's input and got re-mapped, update it.
                    if current_standard_tag in pass_reverse_map:
                        tag_to_standard_map[original_tag] = pass_reverse_map[
                            current_standard_tag
                        ]

                # The new set of tags for the next pass are the keys of the current pass's output.
                current_tags_to_standardize = sorted(list(pass_output_map.keys()))

                # If the standardizer returns an empty map, it means no further consolidation is possible.
                if not current_tags_to_standardize:
                    print("No further tag consolidation possible. Stopping.")
                    break

            # Update tags in each metadata object using the final mapping
            for tool_metadata in all_tool_metadata:
                if "error" not in tool_metadata and isinstance(
                    tool_metadata.get("tags"), list
                ):
                    original_tags = tool_metadata.get("tags", [])
                    # For each original tag, use its standardized version if available, otherwise keep the original.
                    # This correctly handles tags that were already in tool_labels_set and thus not standardized.
                    standardized_tags = {
                        tag_to_standard_map.get(tag, tag) for tag in original_tags
                    }
                    tool_metadata["tags"] = sorted(list(standardized_tags))

    except Exception as e:
        print(f"An error occurred during tag standardization: {e}")

    # Step 5: Remove tags that occur only once across the entire dataset,
    # but only for tags that are new (not pre-existing in tooluniverse)
    try:
        # Flatten the list of all new tags from all tools, ignoring error entries
        all_new_tags_flat = [
            tag
            for tool_metadata in all_tool_metadata
            if "error" not in tool_metadata
            and isinstance(tool_metadata.get("tags"), list)
            for tag in tool_metadata.get("tags", [])
            if tag not in tool_labels_set
        ]

        if all_new_tags_flat:
            # Count the frequency of each new tag
            new_tag_counts = Counter(all_new_tags_flat)

            # Identify new tags that appear more than once
            new_tags_to_keep = {
                tag for tag, count in new_tag_counts.items() if count > 1
            }

            # Filter the tags in each tool's metadata
            for tool_metadata in all_tool_metadata:
                if "error" not in tool_metadata and isinstance(
                    tool_metadata.get("tags"), list
                ):
                    original_tags = tool_metadata.get("tags", [])
                    # Keep all pre-existing tags, and only new tags that appear more than once
                    filtered_tags = [
                        tag
                        for tag in original_tags
                        if tag in tool_labels_set or tag in new_tags_to_keep
                    ]
                    tool_metadata["tags"] = sorted(list(set(filtered_tags)))

    except Exception as e:
        print(f"An error occurred during single-occurrence tag removal: {e}")

    # Step 6: Manually set the UUID 'id' field to ensure true randomness
    for tool_metadata in all_tool_metadata:
        if "error" not in tool_metadata:
            tool_metadata["id"] = str(uuid.uuid4())

    return all_tool_metadata
