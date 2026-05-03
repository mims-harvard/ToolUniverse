#!/usr/bin/env python3
"""
AlphaFold Tool Example

Demonstrates AlphaFold protein structure prediction tools available in ToolUniverse
"""

import json
import os
import warnings
from typing import Any, Dict, List
from tooluniverse import ToolUniverse

# =============================================================================
# Warning Suppression
# =============================================================================
# Description: Suppress RDKit and other warnings for cleaner output
# Syntax: warnings.filterwarnings() calls
warnings.filterwarnings("ignore", category=RuntimeWarning, module="importlib._bootstrap")
warnings.filterwarnings("ignore", message=".*RDKit.*")
warnings.filterwarnings("ignore", message=".*pkg_resources.*")

# =============================================================================
# Schema Loading
# =============================================================================
# Description: Load tool schemas for validation (optional)
# Note: Schema validation is disabled if data file is not available
schemas = {}
try:
    schema_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "alphafold_tools.json"
    )
    with open(schema_path) as f:
        tools_json = json.load(f)
    schemas = {tool["name"]: tool["return_schema"] for tool in tools_json}
except FileNotFoundError:
    # Schema file not available, continue without validation
    pass

# =============================================================================
# Tool Initialization
# =============================================================================
# Description: Initialize ToolUniverse and load all available tools
# Syntax: tu = ToolUniverse(); tu.load_tools()
tu = ToolUniverse()
tu.load_tools()

# =============================================================================
# Method 1: Protein Structure Prediction
# =============================================================================
# Description: Get AlphaFold structure prediction for a protein
# Syntax: tu.run({"name": "alphafold_get_prediction", "arguments": {"qualifier": "P69905"}})
result1 = tu.run({
    "name": "alphafold_get_prediction",
    "arguments": {"qualifier": "P69905"}  # Hemoglobin subunit alpha
})

# =============================================================================
# Method 2: Invalid Protein Prediction
# =============================================================================
# Description: Test error handling with invalid protein identifier
# Syntax: tu.run({"name": "alphafold_get_prediction", "arguments": {"qualifier": "XXX123"}})
result2 = tu.run({
    "name": "alphafold_get_prediction",
    "arguments": {"qualifier": "XXX123"}  # Invalid identifier
})

# =============================================================================
# Method 3: Missing Parameter Test
# =============================================================================
# Description: Test error handling with missing required parameters
# Syntax: tu.run({"name": "alphafold_get_prediction", "arguments": {}})
result3 = tu.run({
    "name": "alphafold_get_prediction",
    "arguments": {}  # Missing qualifier parameter
})

# =============================================================================
# Method 4: Protein Summary Information
# =============================================================================
# Description: Get summary information about a protein
# Syntax: tu.run({"name": "alphafold_get_summary", "arguments": {"qualifier": "P69905"}})
result4 = tu.run({
    "name": "alphafold_get_summary",
    "arguments": {"qualifier": "P69905"}
})

# =============================================================================
# Method 5: Protein Annotations
# =============================================================================
# Description: Get specific annotations for a protein
# Syntax: tu.run({"name": "alphafold_get_annotations", "arguments": {"qualifier": "P69905", "type": "MUTAGEN"}})
result5 = tu.run({
    "name": "alphafold_get_annotations",
    "arguments": {
        "qualifier": "P69905",
        "type": "MUTAGEN"
    }
})

# =============================================================================
# Method 6: Invalid Annotation Type
# =============================================================================
# Description: Test error handling with invalid annotation type
# Syntax: tu.run({"name": "alphafold_get_annotations", "arguments": {"qualifier": "P69905", "type": "INVALID"}})
result6 = tu.run({
    "name": "alphafold_get_annotations",
    "arguments": {
        "qualifier": "P69905",
        "type": "INVALID"
    }
})

# =============================================================================
# Method 7: Result Processing
# =============================================================================
# Description: Process and analyze AlphaFold results
# Syntax: Check result structure and extract relevant information

def process_alphafold_result(result, tool_name):
    """Process AlphaFold tool results"""
    if isinstance(result, dict) and "error" in result:
        # Handle error response
        error_detail = result.get("detail", "")
        return False, f"Error: {result['error']}", error_detail
    elif isinstance(result, dict) and "data" in result:
        # Handle successful response
        data = result["data"]
        return True, "Success", data
    else:
        return False, "No data returned", None

# Process each result
success1, message1, data1 = process_alphafold_result(result1, "alphafold_get_prediction")
success2, message2, data2 = process_alphafold_result(result2, "alphafold_get_prediction")
success3, message3, data3 = process_alphafold_result(result3, "alphafold_get_prediction")
success4, message4, data4 = process_alphafold_result(result4, "alphafold_get_summary")
success5, message5, data5 = process_alphafold_result(result5, "alphafold_get_annotations")
success6, message6, data6 = process_alphafold_result(result6, "alphafold_get_annotations")

# =============================================================================
# Method 8: Schema Validation
# =============================================================================
# Description: Validate results against expected schemas
# Syntax: Check result structure against predefined schemas

def validate_alphafold_schema(result, tool_name):
    """Validate AlphaFold result against expected schema"""
    if not isinstance(result, dict) or "data" not in result:
        return False, "Invalid result format"
    
    data = result["data"]
    schema = schemas.get(tool_name, {})
    expected_keys = schema.get("properties", {}).keys()
    
    # Handle list vs dict results
    if isinstance(data, list) and data:
        record = data[0]
    elif isinstance(data, dict):
        record = data
    else:
        record = {}
    
    missing_keys = [k for k in expected_keys if k not in record]
    if missing_keys:
        return False, f"Missing expected fields: {missing_keys}"
    else:
        return True, "All expected schema fields present"

# Validate results
valid1, schema_msg1 = validate_alphafold_schema(result1, "alphafold_get_prediction")
valid4, schema_msg4 = validate_alphafold_schema(result4, "alphafold_get_summary")
valid5, schema_msg5 = validate_alphafold_schema(result5, "alphafold_get_annotations")

# =============================================================================
# Method 9: Data Extraction
# =============================================================================
# Description: Extract specific information from AlphaFold results
# Syntax: Access specific fields from result data

def extract_prediction_info(data):
    """Extract key information from prediction results"""
    if not data:
        return {}
    
    # Handle list vs dict results
    if isinstance(data, list) and data:
        record = data[0]
    elif isinstance(data, dict):
        record = data
    else:
        return {}
    
    return {
        'uniprot_description': record.get('uniprotDescription', 'N/A'),
        'uniprot_accession': record.get('uniprotAccession', 'N/A'),
        'organism': record.get('organismScientificName', 'N/A'),
        'avg_plddt': record.get('globalMetricValue', 'N/A')
    }

def extract_summary_info(data):
    """Extract key information from summary results"""
    if not data:
        return {}
    
    # Handle list vs dict results
    if isinstance(data, list) and data:
        record = data[0]
    elif isinstance(data, dict):
        record = data
    else:
        return {}
    
    uniprot_entry = record.get('uniprot_entry', {})
    structures = record.get('structures', [])
    
    return {
        'uniprot_ac': uniprot_entry.get('ac', 'N/A'),
        'uniprot_id': uniprot_entry.get('id', 'N/A'),
        'sequence_length': uniprot_entry.get('sequence_length', 'N/A'),
        'structures_count': len(structures)
    }

def extract_annotation_info(data):
    """Extract key information from annotation results"""
    if not data:
        return {}
    
    # Handle list vs dict results
    if isinstance(data, list) and data:
        record = data[0]
    elif isinstance(data, dict):
        record = data
    else:
        return {}
    
    annotations = record.get('annotation', [])
    first_annotation = annotations[0] if annotations else {}
    
    return {
        'accession': record.get('accession', 'N/A'),
        'annotations_count': len(annotations),
        'first_type': first_annotation.get('type', 'N/A'),
        'first_description': first_annotation.get('description', 'N/A')
    }

# Extract information from results
prediction_info = extract_prediction_info(data1)
summary_info = extract_summary_info(data4)
annotation_info = extract_annotation_info(data5)

# =============================================================================
# Method 10: Batch Processing
# =============================================================================
# Description: Process multiple AlphaFold queries in sequence
# Syntax: Loop through multiple tool calls

alphafold_queries = [
    {
        "name": "alphafold_get_prediction",
        "arguments": {"qualifier": "P69905"}
    },
    {
        "name": "alphafold_get_summary",
        "arguments": {"qualifier": "P69905"}
    },
    {
        "name": "alphafold_get_annotations",
        "arguments": {"qualifier": "P69905", "type": "MUTAGEN"}
    }
]

batch_results = []
for query in alphafold_queries:
    try:
        result = tu.run(query)
        batch_results.append(result)
    except Exception as e:
        # Handle individual query failures
        batch_results.append({"error": str(e)})

# =============================================================================
# Summary of AlphaFold Tools
# =============================================================================
# Available AlphaFold tools provide protein structure prediction capabilities:
# - alphafold_get_prediction: Get structure prediction for a protein
# - alphafold_get_summary: Get summary information about a protein
# - alphafold_get_annotations: Get specific annotations for a protein
# 
# Common parameters:
# - qualifier: UniProt accession number or protein identifier
# - type: Annotation type (for annotations tool)
# 
# Result structures:
# - All tools return data in "data" field
# - Results can be dictionaries or lists depending on the tool
# - Error responses contain "error" and optional "detail" fields
# 
# Schema validation:
# - Results should match expected schema structure
# - Check for required fields in response data
# - Handle both list and dictionary result formats
# 
# Error handling:
# - Check for "error" key in dictionary responses
# - Handle missing parameter errors
# - Validate protein identifiers before calling tools
# - Use appropriate annotation types for annotation queries
# 
# Performance considerations:
# - AlphaFold queries may take time to process
# - Use valid UniProt accession numbers
# - Handle timeout errors for complex queries
# - Consider batch processing for multiple proteins
# 
# Use cases:
# - Protein structure analysis
# - Structural biology research
# - Protein annotation and characterization
# - Comparative structural analysis