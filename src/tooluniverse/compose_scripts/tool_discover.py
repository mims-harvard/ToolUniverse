import json
import os
import time


def _search_api_documentation(tool_description, call_tool):
    """Search for API documentation and libraries related to the tool description"""
    api_context = {
        "packages": [],
        "documentation_urls": [],
        "github_repos": [],
        "search_queries": [],
    }

    try:
        # Search for API documentation
        print("🌐 Searching for API documentation...", flush=True)
        try:
            api_search_result = call_tool(
                "web_search",
                {
                    "query": f"{tool_description} API documentation official docs",
                    "max_results": 10,
                    "search_type": "api_documentation",
                },
            )

            if api_search_result.get("status") == "success":
                api_context["documentation_urls"] = [
                    {"title": r["title"], "url": r["url"], "snippet": r["snippet"]}
                    for r in api_search_result.get("results", [])
                ]
                api_context["search_queries"].append(api_search_result.get("query", ""))
        except Exception as e:
            print(f"⚠️ API documentation search failed: {e}", flush=True)

        # Search for Python packages
        print("📦 Searching for Python packages...", flush=True)
        try:
            package_search_result = call_tool(
                "web_search",
                {
                    "query": f"{tool_description} python package pypi",
                    "max_results": 10,
                    "search_type": "python_packages",
                },
            )

            if package_search_result.get("status") == "success":
                api_context["packages"] = [
                    {"title": r["title"], "url": r["url"], "snippet": r["snippet"]}
                    for r in package_search_result.get("results", [])
                ]
                api_context["search_queries"].append(
                    package_search_result.get("query", "")
                )
        except Exception as e:
            print(f"⚠️ Python packages search failed: {e}", flush=True)

        # Search for GitHub repositories
        print("🐙 Searching for GitHub repositories...", flush=True)
        try:
            github_search_result = call_tool(
                "web_search",
                {
                    "query": f"{tool_description} github repository",
                    "max_results": 3,
                    "search_type": "github_repos",
                },
            )

            if github_search_result.get("status") == "success":
                api_context["github_repos"] = [
                    {"title": r["title"], "url": r["url"], "snippet": r["snippet"]}
                    for r in github_search_result.get("results", [])
                ]
                api_context["search_queries"].append(
                    github_search_result.get("query", "")
                )
        except Exception as e:
            print(f"⚠️ GitHub repositories search failed: {e}", flush=True)

        print(
            f"✅ Found {len(api_context['documentation_urls'])} docs, {len(api_context['packages'])} packages, {len(api_context['github_repos'])} repos"
        )

    except Exception as e:
        print(f"⚠️ Web search failed: {e}", flush=True)
        api_context["error"] = str(e)

    return api_context


def _discover_similar_tools(tool_description, call_tool):
    """Discover similar tools using both web search and internal tool finder"""
    similar_tools = []

    # First, try web search for additional context
    try:
        print("🌐 Performing web search for additional context...")
        web_search_result = call_tool(
            "web_search",
            {
                "query": f"{tool_description} python library API",
                "max_results": 3,
                "search_type": "api_documentation",
            },
        )

        if web_search_result.get("status") == "success":
            # Convert web search results to tool-like format for consistency
            web_tools = []
            for i, result in enumerate(web_search_result.get("results", [])):
                web_tools.append(
                    {
                        "name": f"web_result_{i + 1}",
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "snippet": result.get("snippet", ""),
                        "source": "web_search",
                    }
                )
            similar_tools.extend(web_tools)
            print(f"Found {len(web_tools)} web search results")
    except Exception as e:
        print(f"⚠️ Web search failed: {e}")

    # Then use internal tool finder
    discovery_methods = [
        ("Tool_Finder_Keyword", {"description": tool_description, "limit": 5})
    ]

    for method_name, args in discovery_methods:
        try:
            result = call_tool(method_name, args)
            if result and isinstance(result, list):
                similar_tools.extend(result)
        except Exception as e:
            print(f"⚠️ Internal tool finder failed: {e}")

    # Deduplicate
    seen = set()
    deduped_tools = []
    for tool in similar_tools:
        try:
            if isinstance(tool, dict):
                tool_tuple = tuple(sorted(tool.items()))
            elif isinstance(tool, (list, tuple)):
                deduped_tools.append(tool)
                continue
            else:
                tool_tuple = tool

            if tool_tuple not in seen:
                seen.add(tool_tuple)
                deduped_tools.append(tool)
        except (TypeError, AttributeError):
            deduped_tools.append(tool)

    return deduped_tools


def _discover_packages_dynamically(tool_description, call_tool):
    """Dynamically discover relevant packages using web search and PyPI"""

    print("🔍 Discovering packages dynamically...")

    # Step 0: Use Dynamic_Package_Search tool for intelligent package discovery
    try:
        dynamic_result = call_tool(
            "dynamic_package_discovery",
            {
                "requirements": tool_description,
                "functionality": "API access and data processing",
                "constraints": {"python_version": ">=3.8"},
            },
        )

        if dynamic_result.get("status") == "success":
            candidates = dynamic_result.get("candidates", [])
            if candidates:
                print(
                    f"✅ Dynamic search found {len(candidates)} package candidates",
                    flush=True,
                )
                return candidates
    except Exception as e:
        print(f"⚠️ Dynamic package search failed: {e}", flush=True)

    # Step 1: Web search for packages and libraries
    web_packages = []
    try:
        search_queries = [
            f"{tool_description} python library",
            f"{tool_description} python package pypi",
            f"{tool_description} python implementation",
        ]

        for query in search_queries:
            result = call_tool(
                "web_search",
                {"query": query, "max_results": 5, "search_type": "python_packages"},
            )

            if result.get("status") == "success":
                for item in result.get("results", []):
                    # Extract package names from URLs and titles
                    if "pypi.org" in item.get("url", ""):
                        pkg_name = (
                            item["url"].split("/")[-1] or item["url"].split("/")[-2]
                        )
                        web_packages.append(
                            {
                                "name": pkg_name,
                                "source": "pypi_web",
                                "title": item.get("title", ""),
                                "snippet": item.get("snippet", ""),
                                "url": item.get("url", ""),
                            }
                        )
                    elif "github.com" in item.get("url", ""):
                        web_packages.append(
                            {
                                "name": item.get("title", "").split()[0],
                                "source": "github",
                                "title": item.get("title", ""),
                                "snippet": item.get("snippet", ""),
                                "url": item.get("url", ""),
                            }
                        )

    except Exception as e:
        print(f"⚠️ Web package search failed: {e}")

    # Step 2: Use API documentation search
    api_packages = []
    try:
        api_result = call_tool(
            "web_search",
            {
                "query": f"{tool_description} python package pypi",
                "max_results": 5,
                "search_type": "python_packages",
            },
        )

        if api_result.get("status") == "success":
            api_packages = api_result.get("results", [])

    except Exception as e:
        print(f"⚠️ API documentation search failed: {e}")

    # Step 3: Combine and deduplicate
    all_packages = []
    seen_names = set()

    for pkg in web_packages + api_packages:
        name = pkg.get("name", "").lower().strip()
        if name and name not in seen_names:
            seen_names.add(name)
            all_packages.append(pkg)

    print(f"✅ Discovered {len(all_packages)} package candidates")

    # Step 4: Inspect packages using PyPIPackageInspector for comprehensive metrics
    inspected_packages = []
    for pkg in all_packages[:10]:  # Limit to top 10 candidates to save API calls
        try:
            pkg_name = pkg.get("name", "").strip()
            if not pkg_name:
                continue

            print(f"  🔬 Inspecting package: {pkg_name}")

            # Use PyPIPackageInspector to get comprehensive package information
            inspection_result = call_tool(
                "PyPIPackageInspector",
                {
                    "package_name": pkg_name,
                    "include_github": True,
                    "include_downloads": True,
                },
            )

            if inspection_result.get("status") == "success":
                # Merge original search data with comprehensive inspection results
                enriched_pkg = pkg.copy()
                enriched_pkg.update(
                    {
                        "pypi_metadata": inspection_result.get("pypi_metadata", {}),
                        "download_stats": inspection_result.get("download_stats", {}),
                        "github_stats": inspection_result.get("github_stats", {}),
                        "quality_scores": inspection_result.get("quality_scores", {}),
                        "recommendation": inspection_result.get("recommendation", ""),
                        "overall_score": inspection_result.get(
                            "quality_scores", {}
                        ).get("overall_score", 0),
                    }
                )
                inspected_packages.append(enriched_pkg)

                # Print summary
                scores = inspection_result.get("quality_scores", {})
                print(
                    f"    Overall: {scores.get('overall_score', 0)}/100 | "
                    f"Popularity: {scores.get('popularity_score', 0)} | "
                    f"Maintenance: {scores.get('maintenance_score', 0)} | "
                    f"Docs: {scores.get('documentation_score', 0)}"
                )
            else:
                # If inspection fails, keep the basic package info
                enriched_pkg = pkg.copy()
                enriched_pkg["inspection_error"] = inspection_result.get(
                    "error", "Unknown error"
                )
                enriched_pkg["overall_score"] = 0
                inspected_packages.append(enriched_pkg)
                print(
                    f"    ⚠️ Inspection failed: {inspection_result.get('error', 'Unknown')}"
                )

            time.sleep(0.5)  # Rate limiting

        except Exception as e:
            enriched_pkg = pkg.copy()
            enriched_pkg["inspection_error"] = str(e)
            enriched_pkg["overall_score"] = 0
            inspected_packages.append(enriched_pkg)
            print(f"    ⚠️ Could not inspect package {pkg_name}: {e}")

    # Sort by overall score (descending)
    inspected_packages.sort(key=lambda x: x.get("overall_score", 0), reverse=True)

    print("\n📊 Package inspection summary:")
    for i, pkg in enumerate(inspected_packages[:5], 1):
        score = pkg.get("overall_score", 0)
        name = pkg.get("name", "unknown")
        print(f"  {i}. {name}: {score}/100")

    # Step 5: Evaluate packages using PackageEvaluator with enhanced data
    if inspected_packages:
        try:
            evaluation_result = call_tool(
                "PackageEvaluator",
                {
                    "requirements": tool_description,
                    "functionality": tool_description,
                    "candidates": json.dumps(inspected_packages),
                    "evaluation_criteria": json.dumps(
                        {
                            "popularity": "high_priority",  # 下载量、stars
                            "maintenance": "high_priority",  # 最近更新时间
                            "documentation": "medium_priority",  # 文档完整性
                            "compatibility": "high_priority",  # Python版本兼容
                            "security": "medium_priority",  # 安全性
                        }
                    ),
                },
            )

            if evaluation_result and "result" in evaluation_result:
                eval_data = evaluation_result["result"]
                if isinstance(eval_data, str):
                    eval_data = json.loads(eval_data)

                print("📊 Package evaluation completed")
                top_rec = eval_data.get("top_recommendation", {})
                print(f"🏆 Top recommendation: {top_rec.get('name', 'None')}")
                if "popularity_score" in top_rec:
                    print(f"   📈 Popularity: {top_rec.get('popularity_score', 'N/A')}")
                if "maintenance_score" in top_rec:
                    print(
                        f"   🔧 Maintenance: {top_rec.get('maintenance_score', 'N/A')}"
                    )

                return eval_data

        except Exception as e:
            print(f"⚠️ Package evaluation failed: {e}")

    return {
        "rankings": [],
        "top_recommendation": None,
        "candidates": inspected_packages or all_packages,
    }


def _get_specification_template_example():
    """Get a template example for tool specification"""
    return """
{
  "type": "ExampleTool",
  "name": "example_tool_name",
  "description": "Custom implementation for [specific functionality]",
  "implementation": "Implementation strategy: Based on package evaluation, use the 'top_recommended_package' library (score: 95/100) to handle [X]. Key steps: 1) Validate input parameters for [Y], 2) Call top_recommended_package.method() with [Z], 3) Parse and format response. Recommended packages: top_recommended_package (highly rated), alternative_package (backup). Installation: pip install top_recommended_package. Error handling: wrap API calls in try-except for ConnectionError and TimeoutError. This approach leverages the highest-rated, most maintained libraries for reliability.",
  "parameter": {
    "type": "object",
    "properties": {
      "input_param": {
        "type": "string",
        "description": "Description of input parameter",
        "required": true
      }
    },
    "required": ["input_param"]
  },
  "return_schema": {
    "type": "object",
    "properties": {
      "result": {"type": "string", "description": "Tool output description"}
    }
  },
  "test_examples": [
    {"input_param": "test_value"},
    {"input_param": "test_value2"},
  ],
  "label": [
        "label1", "label2", "label3"
    ]
}
"""


def _generate_tool_with_xml(tool_description, reference_info, call_tool):
    """Generate complete tool (spec + implementation) using UnifiedToolGenerator with XML format"""
    import xml.etree.ElementTree as ET

    specification_template = _get_specification_template_example()
    code_template = _get_tool_template_example()
    xml_template = f"""<code><![CDATA[
{code_template}
]]></code>
<spec><![CDATA[
{specification_template}
]]></spec>
"""

    spec_input = {
        "tool_description": tool_description,
        "reference_info": json.dumps(reference_info),
        "xml_template": xml_template,
    }

    result = call_tool("UnifiedToolGenerator", spec_input)
    print(result["result"])

    # Handle both AgenticTool format (success/result) and standard format (status/data)
    if isinstance(result, dict):
        if result.get("success"):
            xml_content = result.get("result", "")
        elif result.get("status") == "success":
            xml_content = result.get("data", "")
        else:
            raise RuntimeError(
                f"UnifiedToolGenerator returned invalid result: {result}"
            )
    else:
        raise RuntimeError(f"UnifiedToolGenerator returned non-dict result: {result}")

    # Parse XML to extract spec and code
    # The XML format is: <code>...</code><spec>...</spec> (no root element, no CDATA)
    xml_content = xml_content.strip()

    # Remove markdown code blocks if present
    if "```xml" in xml_content:
        xml_content = xml_content.split("```xml")[1].split("```")[0].strip()
    elif "```" in xml_content:
        xml_content = xml_content.split("```")[1].split("```")[0].strip()

    # Wrap in a root element for parsing since the template doesn't have one
    wrapped_xml = f"<root>{xml_content}</root>"

    try:
        root = ET.fromstring(wrapped_xml)
    except ET.ParseError as e:
        print(f"❌ XML Parse Error: {e}")
        print(f"📄 XML Content (first 500 chars):\n{xml_content[:500]}")
        print("📄 XML Content (around error line):")
        lines = xml_content.split("\n")
        error_line = (
            int(str(e).split("line")[1].split(",")[0].strip())
            if "line" in str(e)
            else 0
        )
        if error_line > 0 and len(lines) >= error_line:
            for i in range(max(0, error_line - 3), min(len(lines), error_line + 3)):
                print(f"Line {i + 1}: {lines[i]}")
        raise RuntimeError(f"Failed to parse XML from UnifiedToolGenerator: {e}")

    # Extract code
    code_elem = root.find("code")
    implementation_code = (
        code_elem.text.strip() if code_elem is not None and code_elem.text else ""
    )

    # Extract spec
    spec_elem = root.find("spec")
    spec_text = (
        spec_elem.text.strip() if spec_elem is not None and spec_elem.text else "{}"
    )
    tool_config = json.loads(spec_text)

    # Add implementation directly to tool_config
    tool_config["implementation"] = {
        "source_code": implementation_code,
        "dependencies": [],
        "imports": [],
    }

    # Verify type field matches the actual class name in code
    # Extract class name from code using regex
    import re

    class_match = re.search(r"class\s+(\w+)\s*\(", implementation_code)
    if class_match:
        actual_class_name = class_match.group(1)
        if tool_config.get("type") != actual_class_name:
            print(
                f"⚠️ Fixing type mismatch: '{tool_config.get('type')}' -> '{actual_class_name}'"
            )
            tool_config["type"] = actual_class_name

    return tool_config


def _get_tool_template_example():
    """Get a simple, correct example of @register_tool usage"""
    return '''
# Example of correct @register_tool usage:

from typing import Dict, Any
from tooluniverse.base_tool import BaseTool
from tooluniverse.tool_registry import register_tool

@register_tool("ExampleTool")
class ExampleTool(BaseTool):
    """Example tool showing correct structure"""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        # Initialize any required resources here

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main tool execution method

        Args:
            arguments: Dictionary containing tool parameters

        Returns:
            Dictionary with tool results (format varies by tool type)
        """
        try:
            # Extract parameters
            param1 = arguments.get('param1')
            param2 = arguments.get('param2')

            # Your tool logic here
            result = f"Processed {param1} with {param2}"

            # Return format can vary - choose what's appropriate for your tool:
            return {
                "status": "success",
                "data": result
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Tool execution failed: {str(e)}"
            }
'''


def _collect_reference_info(tool_description, call_tool):
    """Collect all reference information for tool implementation"""
    print("🌐 Collecting reference information...", flush=True)

    # Search for API documentation and libraries
    print("  📚 Searching for API documentation...", flush=True)
    api_documentation_context = _search_api_documentation(tool_description, call_tool)
    print(
        f"  ✅ Found {len(api_documentation_context.get('packages', []))} packages, {len(api_documentation_context.get('documentation_urls', []))} docs"
    )

    # Dynamic package discovery
    print("  🔬 Discovering packages dynamically...", flush=True)
    package_recommendations = _discover_packages_dynamically(
        tool_description, call_tool
    )
    print(f"  ✅ Found {len(package_recommendations)} package recommendations")

    # Discover similar tools
    print("  📊 Discovering similar tools...", flush=True)
    similar_tools = _discover_similar_tools(tool_description, call_tool)
    print(f"  ✅ Found {len(similar_tools)} similar tools")

    # Combine all reference information
    reference_info = {
        "similar_tools": similar_tools or [],
        "api_documentation": api_documentation_context or {},
        "package_recommendations": package_recommendations or {},
    }

    print(f"  📋 Reference info collected: {list(reference_info.keys())}")
    return reference_info


def _optimize_tool_with_xml(tool_config, optimization_context, call_tool):
    """Optimize complete tool (spec + implementation) using XMLToolOptimizer with XML format"""
    import xml.etree.ElementTree as ET

    print("🔧 Optimizing tool...")

    try:
        # Build XML from current tool_config
        # Format: <code><![CDATA[...]]></code><spec><![CDATA[...]]></spec>
        implementation_data = tool_config.get("implementation", {})
        implementation_code = implementation_data.get("source_code", "")

        # Save original implementation as backup
        original_implementation = implementation_code

        # Build spec (without internal fields)
        tool_spec = {
            k: v
            for k, v in tool_config.items()
            if not k.startswith("_") and k != "implementation"
        }
        spec_json = json.dumps(tool_spec, indent=2, ensure_ascii=False)

        xml_tool = f"""<code><![CDATA[
{implementation_code}
]]></code>
<spec><![CDATA[
{spec_json}
]]></spec>"""

        # Enhance optimization context with detailed error information
        enhanced_context = optimization_context.copy()

        # Extract test results and analyze for errors
        test_results = optimization_context.get("test_results", {})
        if test_results and "test_details" in test_results:
            test_details = test_results["test_details"]

            # Find all tests with errors in their output
            error_tests = []
            for test in test_details:
                output = test.get("output", {})
                result = output.get("result", {})

                # Check if result contains an error
                if isinstance(result, dict) and "error" in result:
                    error_tests.append(
                        {
                            "test_id": test.get("test_id"),
                            "test_input": test.get("test_input"),
                            "error": result.get("error"),
                            "error_details": result.get("error_details", {}),
                            "error_type": result.get("error_details", {}).get(
                                "type", "Unknown"
                            ),
                        }
                    )

            if error_tests:
                enhanced_context["test_errors"] = error_tests
                enhanced_context["error_summary"] = (
                    f"Found {len(error_tests)}/{len(test_details)} tests with errors"
                )
                # Also include raw test details for LLM to analyze
                enhanced_context["raw_test_details"] = test_details

        # Call XMLToolOptimizer
        result = call_tool(
            "XMLToolOptimizer",
            {
                "xml_tool": xml_tool,
                "optimization_context": json.dumps(enhanced_context),
            },
        )

        # Handle both AgenticTool format (success/result) and standard format (status/data)
        optimized_xml = None
        if isinstance(result, dict):
            if result.get("success"):
                optimized_xml = result.get("result", "")
            elif result.get("status") == "success":
                optimized_xml = result.get("data", "")

        if optimized_xml:
            # Parse optimized XML
            # Format: <code><![CDATA[...]]></code><spec><![CDATA[...]]></spec>
            optimized_xml = optimized_xml.strip()
            if "```xml" in optimized_xml:
                optimized_xml = optimized_xml.split("```xml")[1].split("```")[0].strip()
            elif "```" in optimized_xml:
                optimized_xml = optimized_xml.split("```")[1].split("```")[0].strip()

            # Wrap in a root element for parsing
            wrapped_xml = f"<root>{optimized_xml}</root>"
            root = ET.fromstring(wrapped_xml)

            # Extract optimized code
            code_elem = root.find("code")
            optimized_code = (
                code_elem.text.strip()
                if code_elem is not None and code_elem.text
                else implementation_code
            )

            # Extract optimized spec (if changed)
            spec_elem = root.find("spec")
            if spec_elem is not None and spec_elem.text:
                spec_text = spec_elem.text.strip()
                optimized_spec = json.loads(spec_text)
                # Update ALL fields from optimized spec (except implementation)
                for key, value in optimized_spec.items():
                    if key != "implementation":  # Don't overwrite implementation dict
                        tool_config[key] = value
                print(f"   📋 Updated spec fields: {list(optimized_spec.keys())}")

            # Update implementation
            if "implementation" not in tool_config:
                tool_config["implementation"] = {}
            tool_config["implementation"]["source_code"] = optimized_code

            # Verify type field matches the actual class name in optimized code
            import re

            class_match = re.search(r"class\s+(\w+)\s*\(", optimized_code)
            if class_match:
                actual_class_name = class_match.group(1)
                if tool_config.get("type") != actual_class_name:
                    print(
                        f"⚠️ Fixing type mismatch after optimization: '{tool_config.get('type')}' -> '{actual_class_name}'"
                    )
                    tool_config["type"] = actual_class_name

            print("✅ Tool optimized")
        else:
            print(
                "⚠️ Optimization failed or returned empty result, keeping original code"
            )
            # Restore original code if optimization failed
            tool_config["implementation"]["source_code"] = original_implementation
    except Exception as e:
        print(f"❌ Error during optimization: {e}")
        print("   Keeping original code due to optimization error")
        import traceback

        traceback.print_exc()
        # Restore original code on error
        tool_config["implementation"]["source_code"] = original_implementation

    return tool_config


# Keep old function for backward compatibility
def _generate_implementation(
    tool_config, call_tool, reference_info=None, max_attempts=3
):
    """Legacy function - implementation is now generated together with spec

    Args:
        tool_config: Tool configuration with implementation already included
        call_tool: Function to call other tools
        reference_info: Optional reference information
        max_attempts: Maximum number of generation attempts (default: 3)

    Returns:
        dict: Implementation data containing source_code, dependencies, etc.
    """
    if (
        "implementation" in tool_config
        and isinstance(tool_config["implementation"], dict)
        and "source_code" in tool_config["implementation"]
    ):
        # Already has actual code implementation
        return tool_config["implementation"]

    # Fallback to old generation method if needed
    if reference_info is None:
        reference_info = {}

    template_example = _get_tool_template_example()
    reference_info["template_example"] = template_example

    print("🔄 Generating initial implementation code...")

    # Retry loop to ensure we get syntactically valid code
    error_messages = []

    for attempt in range(max_attempts):
        if attempt > 0:
            print(f"   🔄 Retry attempt {attempt + 1}/{max_attempts}")
            # Add error feedback to reference_info for subsequent attempts
            reference_info["error_feedback"] = {
                "previous_errors": error_messages,
                "instruction": "Previous attempts failed with syntax errors. Please carefully avoid these errors and generate syntactically correct code.",
            }

        # Prepare input with updated reference_info
        impl_input = {
            "tool_specification": json.dumps(tool_config),
            "reference_info": json.dumps(reference_info),
            "template_example": template_example,
        }

        result = call_tool("ToolImplementationGenerator", impl_input)

        if result and "result" in result:
            impl_data = _parse_result(result["result"])
            if impl_data and "implementation" in impl_data:
                impl = impl_data["implementation"]

                # Basic validation: check syntax only
                source_code = impl.get("source_code", "")
                if source_code:
                    try:
                        compile(source_code, "<generated>", "exec")
                        print("✅ Initial implementation generated (syntax valid)")
                        return impl
                    except SyntaxError as e:
                        error_msg = f"Attempt {attempt + 1}: Syntax error at line {e.lineno}: {e.msg}"
                        print(f"   ⚠️ {error_msg}")
                        error_messages.append(error_msg)
                        continue
                else:
                    error_msg = f"Attempt {attempt + 1}: No source code generated"
                    print(f"   ⚠️ {error_msg}")
                    error_messages.append(error_msg)

        if attempt == max_attempts - 1:
            print(
                f"❌ Failed to generate syntactically valid code after {max_attempts} attempts"
            )
            print(f"   Errors encountered: {error_messages}")

    return None


def _generate_test_cases(tool_config, call_tool):
    """Generate test cases - uses test_examples from tool_config

    Note: Test cases are now generated by UnifiedToolGenerator as part of the spec.
    This function extracts and formats them for execution.
    """
    # Get test_examples from tool_config (already generated by UnifiedToolGenerator)
    test_examples = tool_config.get("test_examples", [])

    if not test_examples:
        print("⚠️ No test_examples found in tool_config")
        return []

    # Convert simplified test_examples format to full test case format
    # test_examples: [{"param1": "value1"}, {"param2": "value2"}]
    # test_cases: [{"name": "toolName", "arguments": {...}}, ...]
    tool_name = tool_config.get("name")
    test_cases = []

    for test_input in test_examples:
        if isinstance(test_input, dict):
            test_case = {"name": tool_name, "arguments": test_input}
            test_cases.append(test_case)

    print(f"📋 Using {len(test_cases)} test cases from tool configuration")
    return test_cases


def _validate_test_cases(test_cases, tool_config):
    """Validate test cases"""
    if not isinstance(test_cases, list):
        return False

    tool_name = tool_config.get("name", "")
    required_params = tool_config.get("parameter", {}).get("required", [])

    for test_case in test_cases:
        if not isinstance(test_case, dict):
            return False
        if test_case.get("name") != tool_name:
            return False
        args = test_case.get("arguments", {})
        missing_params = [p for p in required_params if p not in args]
        if missing_params:
            return False

    return True


def _execute_code_safely_with_executor(code_file, tool_name, test_arguments, call_tool):
    """
    使用 python_code_executor 安全执行生成的工具代码

    Args:
        code_file: 生成的代码文件路径
        tool_name: 工具名称
        test_arguments: 测试参数
        call_tool: 调用其他工具的函数

    Returns:
        dict: {
            "success": bool,
            "result": Any,
            "error": str,
            "error_type": str,
            "traceback": str,
            "stdout": str,
            "stderr": str,
            "execution_time_ms": int
        }
    """
    print("   🔐 Executing code via python_code_executor...")

    # 验证文件存在
    if not os.path.exists(code_file):
        return {
            "success": False,
            "error": f"Code file not found: {code_file}",
            "error_type": "FileNotFoundError",
            "traceback": "",
        }

    # 构建测试执行代码
    test_code = f"""
import sys
import os
import importlib.util

# 添加当前目录到路径
sys.path.insert(0, os.getcwd())

# 动态加载生成的模块
spec = importlib.util.spec_from_file_location("{tool_name}", "{code_file}")
if spec is None:
    raise ImportError(f"Cannot create spec for {tool_name} from {code_file}")

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

# 获取工具类
ToolClass = getattr(module, "{tool_name}", None)
if ToolClass is None:
    raise AttributeError(f"Tool class {tool_name} not found in module")

# 实例化工具
tool_instance = ToolClass({{"name": "{tool_name}"}})

# 执行测试
test_args = {test_arguments}
result = tool_instance.run(test_args)
"""

    # 调用 python_code_executor
    try:
        execution_result = call_tool(
            "python_code_executor",
            {
                "code": test_code,
                "arguments": {},
                "timeout": 30,
                "allowed_imports": [
                    "requests",
                    "xml",
                    "json",
                    "urllib",
                    "http",
                    "bs4",
                    "lxml",
                    "pandas",
                    "numpy",
                    "scipy",
                    "matplotlib",
                    "seaborn",
                    "sys",
                    "os",
                    "importlib",
                    "importlib.util",
                    "typing",
                    "Bio",
                ],
            },
        )

        # 标准化返回格式
        if execution_result.get("success"):
            return {
                "success": True,
                "result": execution_result.get("result"),
                "stdout": execution_result.get("stdout", ""),
                "stderr": execution_result.get("stderr", ""),
                "execution_time_ms": execution_result.get("execution_time_ms", 0),
            }
        else:
            return {
                "success": False,
                "error": execution_result.get("error", "Unknown error"),
                "error_type": execution_result.get("error_type", "UnknownError"),
                "traceback": execution_result.get("traceback", ""),
                "stdout": execution_result.get("stdout", ""),
                "stderr": execution_result.get("stderr", ""),
            }

    except Exception as e:
        import traceback as tb

        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": tb.format_exc(),
        }


def _execute_test_cases_with_template(execution_context, call_tool):
    """Execute the pre-saved execution template and return results

    Args:
        execution_context: Dict containing execution information:
            - execution_file: Path to the execution template file
            - tool_config: Tool configuration (optional)
            - test_cases: Test cases (optional)
            - temp_dir: Temporary directory (optional)
        call_tool: Function to call other tools
    """
    execution_file = execution_context.get("execution_file")
    print(f"🚀 Running execution template: {execution_file}")

    test_results = {
        "total_tests": 0,
        "passed_tests": 0,
        "failed_tests": 0,
        "test_details": [],
        "overall_success_rate": 0.0,
        "errors_fixed": 0,
        "fix_attempts": 0,
    }

    if not execution_file or not os.path.exists(execution_file):
        print(f"❌ Execution template not found: {execution_file}")
        return test_results

    # Execute using python_script_runner tool
    try:
        import json

        # Use python_script_runner to execute the file
        working_dir = os.path.dirname(execution_file) if execution_file else "."

        # Call python_script_runner without validation parameter (default validate=True)
        execution_result = call_tool(
            "python_script_runner",
            {
                "script_path": execution_file,
                "timeout": 120,
                "working_directory": working_dir,
            },
        )

        print("📋 Execution output:")
        if execution_result.get("success"):
            print(execution_result.get("stdout", ""))
            if execution_result.get("stderr"):
                print("⚠️ Execution errors:")
                print(execution_result.get("stderr"))
        else:
            print(
                f"❌ Execution failed: {execution_result.get('error', 'Unknown error')}"
            )

        # Parse execution results directly from stdout
        stdout = execution_result.get("stdout", "")

        # Extract JSON results
        if "### TEST_RESULTS_JSON ###" in stdout:
            try:
                json_start = stdout.index("### TEST_RESULTS_JSON ###") + len(
                    "### TEST_RESULTS_JSON ###\n"
                )
                json_end = stdout.index("### END_TEST_RESULTS_JSON ###")
                json_str = stdout[json_start:json_end].strip()
                parsed_results = json.loads(json_str)

                # Store raw test results for optimizer to analyze
                test_results["test_details"] = parsed_results.get("test_cases", [])
                test_results["total_tests"] = len(test_results["test_details"])

                print(f"📊 Executed {test_results['total_tests']} test cases")

            except Exception as e:
                print(f"⚠️ Failed to parse results: {e}")
                test_results["parse_error"] = str(e)
                # Fallback to simple counting
                test_results["total_tests"] = 0
        else:
            print("⚠️ No JSON results found in output, falling back to simple counting")
            lines = stdout.split("\n")
            passed_count = sum(1 for line in lines if "✅ Success:" in line)
            failed_count = sum(1 for line in lines if "❌ Error:" in line)
            test_results["total_tests"] = passed_count + failed_count
            test_results["passed_tests"] = passed_count
            test_results["failed_tests"] = failed_count

    except Exception as e:
        print(f"❌ Error executing template: {e}")
        import traceback

        traceback.print_exc()

    return test_results


def _evaluate_quality(
    tool_config,
    test_cases,
    call_tool,
    test_execution_results=None,
    detailed=True,
    temp_dir=None,
):
    """评估代码质量 - 基于测试执行结果计算分数"""

    # 如果已提供测试结果，直接使用；否则执行测试
    if test_execution_results is None:
        # Save tool files first
        base_filename = f"generated_tool_{tool_config['name']}"
        saved_files = _save_tool_files(
            tool_config, base_filename, call_tool, temp_dir, test_cases
        )

        # Extract execution file
        execution_file = next(
            (f for f in saved_files if f.endswith("_execute.py")), None
        )

        # Execute tests using the saved file
        execution_context = {
            "execution_file": execution_file,
            "tool_config": tool_config,
            "test_cases": test_cases,
            "temp_dir": temp_dir,
        }
        test_execution_results = _execute_test_cases_with_template(
            execution_context, call_tool
        )
    else:
        print("   ♻️ Using pre-executed test results")

    # Extract implementation code for analysis
    implementation_code = ""
    if "implementation" in tool_config:
        impl = tool_config["implementation"]
        implementation_code = impl["source_code"]

    # Extract test details for score calculation
    parsed_data = {"test_execution": test_execution_results}

    # Calculate overall score based on test execution results
    if test_execution_results and "test_details" in test_execution_results:
        test_details = test_execution_results.get("test_details", [])
        total_tests = len(test_details)
        passed_tests = sum(
            1
            for t in test_details
            if t.get("output", {}).get("result", {}).get("error") is None
        )

        if total_tests > 0:
            parsed_data["overall_score"] = (passed_tests / total_tests) * 10
            print(
                f"   📊 Score: {parsed_data['overall_score']:.2f}/10 ({passed_tests}/{total_tests})"
            )
        else:
            parsed_data["overall_score"] = 0.0
    else:
        parsed_data["overall_score"] = 5.0

    # Try to enrich with CodeQualityAnalyzer analysis (optional, can fail)
    try:
        eval_input = {
            "tool_name": tool_config.get("name", "UnknownTool"),
            "tool_description": tool_config.get("description", "")[:200],
            "tool_parameters": json.dumps(tool_config.get("parameter", {})),
            "implementation_code": implementation_code[:2000],
            "test_cases": json.dumps(test_cases[:2] if test_cases else []),
            "test_execution_results": json.dumps(
                {
                    "total": test_execution_results.get("total_tests", 0),
                    "passed": (
                        passed_tests if "test_details" in test_execution_results else 0
                    ),
                }
            ),
        }

        result = call_tool("CodeQualityAnalyzer", eval_input)

        if isinstance(result, dict):
            if result.get("success"):
                result_data = result.get("result", "{}")
            elif result.get("status") == "success":
                result_data = result.get("data", "{}")
            else:
                result_data = "{}"
        else:
            result_data = "{}"

        quality_data = _parse_result(result_data)
        if quality_data and "overall_score" in quality_data:
            # Use CodeQualityAnalyzer score if available
            parsed_data["overall_score"] = quality_data["overall_score"]
            parsed_data["quality_analysis"] = quality_data
    except Exception as e:
        print(f"   ⚠️ CodeQualityAnalyzer skipped: {e}")

    return parsed_data


def _check_and_install_dependencies(
    tool_config, installed_packages, user_confirmed_install, call_tool
):
    """Check and install dependencies with user confirmation

    Args:
        tool_config: Tool configuration containing dependencies
        installed_packages: Set of already installed packages
        user_confirmed_install: Whether user has confirmed installation
        call_tool: Function to call other tools

    Returns:
        tuple: (should_continue, user_confirmed, installed_packages, instruction)
        - should_continue: True to continue, False to trigger reimplementation
        - user_confirmed: Updated confirmation status
        - installed_packages: Updated set of installed packages
        - instruction: Instruction for optimizer if reimplementation needed, else None
    """
    dependencies = tool_config.get("implementation", {}).get("dependencies", [])
    if not dependencies:
        return True, user_confirmed_install, installed_packages, None

    # Check missing packages by trying to import them
    missing_packages = []
    for dep in dependencies:
        if dep not in installed_packages:
            # Extract base package name for import test
            base_name = (
                dep.split(".")[0]
                .split(">=")[0]
                .split("==")[0]
                .split("<")[0]
                .replace("-", "_")
            )
            try:
                result = call_tool(
                    "python_code_executor",
                    {"code": f"import {base_name}", "timeout": 3},
                )
                if result.get("success"):
                    installed_packages.add(dep)
                else:
                    missing_packages.append(dep)
            except Exception:
                missing_packages.append(dep)

    if not missing_packages:
        return True, user_confirmed_install, installed_packages, None

    # Get parent packages to install (extract base package name)
    packages_to_install = list(
        set(
            [
                pkg.split(".")[0].split(">=")[0].split("==")[0].split("<")[0]
                for pkg in missing_packages
            ]
        )
    )

    # User confirmation (first time only)
    if not user_confirmed_install:
        print(f"\n📦 Missing packages: {', '.join(packages_to_install)}")
        print("   Install these packages to continue?")

        # DEBUG MODE: Auto-accept installation to avoid interactive prompts
        print("\n🔧 DEBUG MODE: Auto-installing packages...")
        user_confirmed_install = True
    else:
        print(f"📦 Auto-installing: {', '.join(packages_to_install)}")

    # Install packages
    import subprocess
    import sys

    failed = []

    for pkg in packages_to_install:
        try:
            print(f"   📥 Installing {pkg}...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", pkg],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode == 0:
                print(f"   ✅ {pkg}")
                installed_packages.add(pkg)
            else:
                print(f"   ❌ {pkg}")
                failed.append({"pkg": pkg, "err": result.stderr[:200]})
        except Exception as e:
            print(f"   ❌ {pkg}")
            failed.append({"pkg": pkg, "err": str(e)})

    if failed:
        print("🔄 Failed. Requesting reimplementation...")
        errors = "\n".join([f"- {f['pkg']}: {f['err']}" for f in failed])
        instruction = (
            f"CRITICAL: FAILED: {[f['pkg'] for f in failed]}\n"
            f"Errors:\n{errors}\n"
            f"Use different packages OR standard library OR installed: {list(installed_packages)}"
        )
        return False, user_confirmed_install, installed_packages, instruction

    return True, user_confirmed_install, installed_packages, None


def iterative_comprehensive_optimization(
    tool_config, call_tool, max_iterations=5, target_score=8.5, temp_dir=None
):
    """
    Comprehensive optimization with guaranteed minimum iterations
    and multi-agent improvement strategy
    """
    print("\n🚀 Starting comprehensive optimization")
    print(f"Target: {target_score}/10, Max iterations: {max_iterations}")

    improvement_history = []
    user_confirmed_install = False
    installed_packages = set()

    for iteration in range(max_iterations):
        print(f"\n{'=' * 60}")
        print(f"🔄 Iteration {iteration + 1}/{max_iterations}")

        # Check and install dependencies
        should_continue, user_confirmed_install, installed_packages, instruction = (
            _check_and_install_dependencies(
                tool_config, installed_packages, user_confirmed_install, call_tool
            )
        )

        if not should_continue:
            # Dependency issue - trigger reimplementation
            optimization_context = {
                "quality_report": {"overall_score": 0, "issues": ["Dependency issue"]},
                "test_results": {"total_tests": 0, "failed_tests": 0},
                "iteration": iteration,
                "target_score": target_score,
                "current_score": 0,
                "improvement_history": improvement_history,
                "instruction": instruction,
            }
            tool_config = optimize_code(tool_config, optimization_context, call_tool)
            continue

        # Generate and execute tests
        test_cases = _generate_test_cases(tool_config, call_tool)

        base_filename = f"generated_tool_{tool_config['name']}"
        saved_files = _save_tool_files(
            tool_config, base_filename, call_tool, temp_dir, test_cases
        )
        execution_file = next(
            (f for f in saved_files if f.endswith("_execute.py")), None
        )

        execution_context = {
            "execution_file": execution_file,
            "tool_config": tool_config,
            "test_cases": test_cases,
            "temp_dir": temp_dir,
        }
        test_results = _execute_test_cases_with_template(execution_context, call_tool)

        # Evaluate quality
        quality_report = _evaluate_quality(
            tool_config,
            test_cases,
            call_tool,
            test_execution_results=test_results,
            temp_dir=temp_dir,
            detailed=True,
        )

        current_score = quality_report["overall_score"]
        print(f"📊 Score: {current_score:.2f}/10")

        # Early stopping
        if current_score >= target_score:
            print("🎯 Target reached!")
            improvement_history.append(
                {
                    "iteration": iteration + 1,
                    "score": current_score,
                    "improvements": quality_report.get("improvement_suggestions", []),
                    "early_stop": True,
                }
            )
            break

        # Optimize code
        optimization_context = {
            "quality_report": quality_report,
            "test_results": test_results,
            "iteration": iteration,
            "target_score": target_score,
            "current_score": current_score,
            "improvement_history": improvement_history,
        }
        tool_config = optimize_code(tool_config, optimization_context, call_tool)

        improvement_history.append(
            {
                "iteration": iteration + 1,
                "score": current_score,
                "improvements": quality_report.get("improvement_suggestions", []),
            }
        )

    # Final evaluation
    final_test_cases = _generate_test_cases(tool_config, call_tool)

    # Save final tool files
    final_base_filename = f"generated_tool_{tool_config['name']}_final"
    saved_files = _save_tool_files(
        tool_config, final_base_filename, call_tool, temp_dir
    )

    # Extract execution file
    execution_file = next((f for f in saved_files if f.endswith("_execute.py")), None)

    # Execute final tests using the saved file
    execution_context = {
        "execution_file": execution_file,
        "tool_config": tool_config,
        "test_cases": final_test_cases,
        "temp_dir": temp_dir,
    }
    final_test_results = _execute_test_cases_with_template(execution_context, call_tool)
    final_quality = _evaluate_quality(
        tool_config,
        final_test_cases,
        call_tool,
        test_execution_results=final_test_results,  # 新增参数
        detailed=True,
        temp_dir=temp_dir,
    )

    print(f"\n🏁 Optimization completed after {max_iterations} iterations")
    print(f"Final score: {final_quality['overall_score']:.2f}/10")

    return tool_config, final_quality, improvement_history


def _optimize_specification_existing(tool_config, optimization_context, call_tool):
    """Use existing ToolSpecificationOptimizer with comprehensive optimization context"""
    result = call_tool(
        "ToolSpecificationOptimizer",
        {
            "tool_config": json.dumps(tool_config),
            "optimization_context": json.dumps(optimization_context),
        },
    )

    if result and "result" in result:
        opt_data = _parse_result(result["result"])
        if "optimized_config" in opt_data:
            # Merge optimized spec
            merged = tool_config.copy()
            opt_config = opt_data["optimized_config"]

            spec_fields = [
                "name",
                "description",
                "parameter",
                "return_schema",
                "test_examples",
            ]
            merged.update({k: v for k, v in opt_config.items() if k in spec_fields})

            print("  ✅ Specification optimized")
            return merged
        else:
            return tool_config


def _parse_result(result_data):
    """Parse result data from agent calls"""
    if isinstance(result_data, str):
        # 清理可能的 markdown 代码块封装
        cleaned_data = result_data.strip()

        # 移除 ```json ``` 代码块封装
        if cleaned_data.startswith("```json"):
            cleaned_data = cleaned_data[7:]  # 移除 ```json
        if cleaned_data.startswith("```"):
            cleaned_data = cleaned_data[3:]  # 移除 ```
        if cleaned_data.endswith("```"):
            cleaned_data = cleaned_data[:-3]  # 移除结尾的 ```

        cleaned_data = cleaned_data.strip()

        try:
            return json.loads(cleaned_data)
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON 解析失败: {e}")
            print(f"原始数据前200字符: {result_data[:200]}")
            print(f"清理后数据前200字符: {cleaned_data[:200]}")
            return {}
    return result_data


# Keep the old function for backward compatibility
def _generate_execution_template(
    tool_config, base_filename, test_cases=None, temp_dir=None
):
    """Generate execution template script for testing the tool"""
    class_name = tool_config.get("name", "CustomTool")
    tool_config.get("type", "CustomTool")

    execution_template = f'''#!/usr/bin/env python3
"""
Execution template for {class_name}
Generated by ToolDiscover
"""

import sys
import json
import os
import traceback
import subprocess
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def load_tool_config(config_file):
    """Load tool configuration from JSON file"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading config: {{e}}")
        return None

def load_test_cases(tool_config):
    """Extract test cases from tool configuration"""
    return tool_config.get("test_examples", [])

def execute_tool_test(client, tool_name, test_input):
    """Execute a single test case and return raw result"""
    try:
        # Build tool call in ToolUniverse format
        tool_call = {{
            "name": tool_name,
            "arguments": test_input
        }}
        # Execute the tool using tooluniverse.run method
        result = client.run(tool_call)
        return {{"status": "executed", "result": result}}
    except Exception as e:
        return {{"status": "exception", "exception_type": type(e).__name__, "exception_message": str(e)}}

def main():
    """Main execution function"""
    print("🚀 Starting tool execution...")

    # Load configuration
    config_file = f"{base_filename}_config.json"
    tool_config = load_tool_config(config_file)
    if not tool_config:
        return

    print(f"✅ Loaded tool config: {{tool_config.get('name', 'Unknown')}}")

    # Load test cases
    test_cases = load_test_cases(tool_config)
    print(f"📋 Found {{len(test_cases)}} test cases")

    # Import the tool class
    try:
        # Import the generated tool module using importlib
        import importlib.util
        import sys

        code_file = f"{base_filename}_code.py"
        spec = importlib.util.spec_from_file_location("tool_module", code_file)
        if spec is None:
            raise ImportError(f"Cannot create spec for {{code_file}}")

        tool_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tool_module)

        # Get the tool class
        tool_type = tool_config.get("type")
        if not tool_type:
            raise ValueError("Tool config missing required 'type' field")
        tool_class = getattr(tool_module, tool_type)

        # Initialize ToolUniverse and register the tool
        from tooluniverse import ToolUniverse
        client = ToolUniverse()
        client.register_custom_tool(
            tool_class=tool_class,
            tool_name=tool_type,
            tool_config=tool_config,
            instantiate=True
        )

        # Get the instantiated tool
        print(f"✅ Successfully loaded tool.")

    except Exception as e:
        print(f"❌ Error importing tool: {{e}}")
        print(f"Traceback: {{traceback.format_exc()}}")
        return

    # Execute test cases and collect ALL results
    all_results = []
    tool_name = tool_config.get("name")
    for i, test_input in enumerate(test_cases, 1):
        print(f"\\n🧪 Test case {{i}}/{{len(test_cases)}}: {{test_input}}")
        test_result = execute_tool_test(client, tool_name, test_input)
        all_results.append({{"test_id": i, "test_input": test_input, "output": test_result}})

        # Just print what we got, no interpretation
        print(f"   📤 Result: {{test_result}}")

    # Output everything as JSON
    print("\\n### TEST_RESULTS_JSON ###")
    print(json.dumps({{"test_cases": all_results}}, indent=2))
    print("### END_TEST_RESULTS_JSON ###")

if __name__ == "__main__":
    main()
'''

    # Save execution template
    execution_file = f"{base_filename}_execute.py"
    if temp_dir:
        execution_file = os.path.join(temp_dir, os.path.basename(execution_file))

    # Ensure absolute path
    execution_file = os.path.abspath(execution_file)

    with open(execution_file, "w", encoding="utf-8") as f:
        f.write(execution_template)

    print(f"   📜 Execution template saved: {execution_file}")
    return execution_file


def _extract_imports_from_code(code_content):
    """Extract import statements from generated code"""
    import re

    imports = []

    # Find all import statements
    import_patterns = [
        r"^import\s+([a-zA-Z_][a-zA-Z0-9_.]*)",  # import module
        r"^from\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+import",  # from module import
    ]

    for line in code_content.split("\n"):
        line = line.strip()
        for pattern in import_patterns:
            match = re.match(pattern, line)
            if match:
                module_name = match.group(1)
                # Skip standard library modules
                if not _is_standard_library_module(module_name):
                    imports.append(module_name)

    return list(set(imports))  # Remove duplicates


def _is_standard_library_module(module_name):
    """Check if a module is part of Python standard library"""
    standard_modules = {
        "os",
        "sys",
        "json",
        "math",
        "datetime",
        "time",
        "random",
        "re",
        "collections",
        "itertools",
        "functools",
        "operator",
        "urllib",
        "http",
        "xml",
        "csv",
        "io",
        "pathlib",
        "glob",
        "shutil",
        "tempfile",
        "subprocess",
        "threading",
        "multiprocessing",
        "queue",
        "logging",
        "warnings",
        "traceback",
        "inspect",
        "abc",
        "enum",
        "dataclasses",
        "typing_extensions",
        "xml.etree.ElementTree",
        "tooluniverse",
    }

    # Check if it's a standard module or starts with standard module
    base_module = module_name.split(".")[0]
    return base_module in standard_modules


def _save_tool_files(
    tool_config, base_filename, call_tool=None, temp_dir=None, test_cases=None
):
    """Save tool files to temporary directory"""
    print("   📝 Preparing to save tool files...")
    print(f"   📁 Base filename: {base_filename}")

    # Use temporary directory if provided
    if temp_dir:
        base_filename = os.path.join(temp_dir, os.path.basename(base_filename))
        print(f"   📁 Saving to temp directory: {temp_dir}")

    # Update configuration
    config_to_save = tool_config.copy()
    tool_name = config_to_save.get("name", "CustomTool")
    # Keep the original type field (class name), don't overwrite it with the name
    print(f"   🏷️ Tool name: {tool_name}")

    # Extract dependency information
    dependencies = []
    if (
        "implementation" in tool_config
        and "dependencies" in tool_config["implementation"]
    ):
        dependencies = tool_config["implementation"]["dependencies"]
        print(f"   📦 Dependencies: {dependencies}")

    # Add dependencies field to configuration
    config_to_save["dependencies"] = dependencies

    # Merge test cases if provided
    if test_cases:
        existing_test_examples = config_to_save.get("test_examples", [])
        # Combine provided test cases with existing ones
        combined_test_cases = list(test_cases)  # Start with provided test cases
        # Add existing ones that are not duplicates
        for existing in existing_test_examples:
            if existing not in combined_test_cases:
                combined_test_cases.append(existing)
        config_to_save["test_examples"] = combined_test_cases
        print(f"   📋 Merged test cases: {len(combined_test_cases)} total")

    # Remove implementation code
    if "implementation" in config_to_save:
        del config_to_save["implementation"]
        print("   🗑️ Removed implementation from config")

    # Save configuration file
    config_file = f"{base_filename}_config.json"
    print(f"   💾 Saving config file: {config_file}")
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config_to_save, f, indent=2, ensure_ascii=False)
    print(f"   ✅ Config file saved: {os.path.getsize(config_file)} bytes")

    # Generate code file
    code_file = f"{base_filename}_code.py"
    print(f"   🔧 Generating code file: {code_file}")
    _generate_tool_code(tool_config, code_file, call_tool)
    print(f"   ✅ Code file generated: {os.path.getsize(code_file)} bytes")

    # Extract actual imports from generated code and update dependencies
    try:
        with open(code_file, "r", encoding="utf-8") as f:
            code_content = f.read()

        actual_imports = _extract_imports_from_code(code_content)
        if actual_imports:
            print(f"   🔍 Extracted imports from code: {actual_imports}")
            # Update dependencies with actual imports
            dependencies = list(set(dependencies + actual_imports))
            config_to_save["dependencies"] = dependencies
            print(f"   📦 Updated dependencies: {dependencies}")

            # Update config file with new dependencies
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config_to_save, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"   ⚠️ Could not extract imports from code: {e}")

    # Generate execution template
    execution_file = _generate_execution_template(
        tool_config, base_filename, test_cases, temp_dir
    )
    print(
        f"   ✅ Execution template generated: {os.path.getsize(execution_file)} bytes"
    )

    # Ensure all paths are absolute
    config_file = os.path.abspath(config_file)
    code_file = os.path.abspath(code_file)
    execution_file = os.path.abspath(execution_file)

    return [config_file, code_file, execution_file]


def _convert_json_to_python(obj):
    """Recursively convert JSON object booleans and types to Python format"""
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            result[key] = _convert_json_to_python(value)
        return result
    elif isinstance(obj, list):
        return [_convert_json_to_python(item) for item in obj]
    elif obj == "true":
        return True
    elif obj == "false":
        return False
    elif obj == "string":
        return str
    elif obj == "number":
        return float
    elif obj == "integer":
        return int
    elif obj == "object":
        return dict
    elif obj == "array":
        return list
    else:
        return obj


def _convert_python_types_to_strings(obj):
    """Convert Python type objects to JSON schema standard types consistently"""
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            if key == "type":
                if isinstance(value, str):
                    # Normalize to JSON schema standard
                    type_mapping = {
                        "str": "string",
                        "int": "integer",
                        "float": "number",
                        "bool": "boolean",
                        "dict": "object",
                        "list": "array",
                        "none": "null",
                        # Already correct JSON schema types
                        "string": "string",
                        "integer": "integer",
                        "number": "number",
                        "boolean": "boolean",
                        "object": "object",
                        "array": "array",
                        "null": "null",
                    }
                    result[key] = type_mapping.get(value.lower(), value)
                elif isinstance(value, type):
                    # Handle Python type objects
                    type_name = value.__name__.lower()
                    type_mapping = {
                        "str": "string",
                        "int": "integer",
                        "float": "number",
                        "bool": "boolean",
                        "dict": "object",
                        "list": "array",
                        "none": "null",
                    }
                    result[key] = type_mapping.get(type_name, "string")
                else:
                    result[key] = value
            else:
                result[key] = _convert_python_types_to_strings(value)
        return result
    elif isinstance(obj, list):
        return [_convert_python_types_to_strings(item) for item in obj]
    elif obj is True:
        return True  # Keep boolean values as booleans
    elif obj is False:
        return False
    elif obj is str:
        return "string"
    elif obj is float:
        return "number"
    elif obj is int:
        return "integer"
    elif obj is dict:
        return "object"
    elif obj is list:
        return "array"
    else:
        return obj


def _validate_generated_code(code_file, code_content=None):
    """Validate the generated code for syntax and structure"""
    print("      🔍 Validating code syntax...")

    # Use provided content or read from file
    if code_content is None:
        with open(code_file, "r", encoding="utf-8") as f:
            code_content = f.read()

    try:
        compile(code_content, code_file, "exec")
        print(f"      ✅ Generated code syntax validated: {code_file}")
        return True, code_content
    except SyntaxError as e:
        print(f"      ❌ Syntax error in generated code: {e}")
        print(f"         Line {e.lineno}: {e.text}")
        print(f"         Error type: {type(e).__name__}")
        return False, str(e)


def _fix_syntax_errors(tool_config, code_file, syntax_error, call_tool):
    """Attempt to fix syntax errors using agents"""
    if not call_tool:
        return False

    print("      🔧 Attempting to fix syntax error using ImplementationDebugger...")
    try:
        # Create a quality report for the syntax error
        quality_report = {
            "overall_score": 0.0,
            "scores": {"syntax_correctness": 0.0, "code_quality": 0.0},
            "issues": [f"Syntax error: {syntax_error}"],
            "improvement_suggestions": [
                "Fix syntax errors",
                "Ensure proper Python syntax",
            ],
        }

        # Try to fix using UnifiedCodeOptimizer
        result = call_tool(
            "UnifiedCodeOptimizer",
            {
                "tool_config": json.dumps(tool_config),
                "quality_report": json.dumps(quality_report),
                "iteration": 0,
                "improvement_focus": json.dumps(["syntax_fix", "stability"]),
            },
        )

        if result and "result" in result:
            opt_data = _parse_result(result["result"])
            if (
                "implementation" in opt_data
                and "source_code" in opt_data["implementation"]
            ):
                # Try to regenerate the code with the fixed implementation
                tool_config["implementation"] = opt_data["implementation"]
                print("      🔄 Regenerating code with fixed implementation...")

                # Regenerate the code file
                with open(code_file, "w", encoding="utf-8") as f:
                    f.write(opt_data["implementation"]["source_code"])

                # Validate the fixed code
                is_valid, _ = _validate_generated_code(code_file)
                if is_valid:
                    print("      ✅ Syntax error fixed successfully!")
                    return True
                else:
                    print("      ⚠️ Fixed code still has syntax errors")

    except Exception as fix_error:
        print(f"      ⚠️ Failed to fix syntax error: {fix_error}")

    return False


def _validate_class_structure(code_content):
    """Validate that the generated code has the required class structure"""
    print("      🔍 Validating class structure...")

    required_elements = [
        ("@register_tool", "Generated code missing @register_tool decorator"),
        ("class", "Generated code missing class definition"),
        ("def run(self, arguments", "Generated code missing run method"),
        ("BaseTool", "Generated code missing BaseTool inheritance"),
        ("def __init__(self, tool_config", "Generated code missing __init__ method"),
    ]

    for element, error_msg in required_elements:
        if element not in code_content:
            raise ValueError(error_msg)

    print("      ✅ Generated code structure validated")


def _generate_tool_code(tool_config, code_file, call_tool=None):
    """Generate Python code for all tool types using correct register_tool method"""
    tool_name = tool_config["name"]
    print(f"      🏷️ Tool name: {tool_name}")

    # Clean tool name to be a valid Python class name
    import re

    clean_tool_name = re.sub(r"[^a-zA-Z0-9_]", "", tool_name)
    if not clean_tool_name or clean_tool_name[0].isdigit():
        clean_tool_name = "Tool" + clean_tool_name
    print(f"      🧹 Cleaned class name: {clean_tool_name}")

    print(f"      📝 Writing code to file: {code_file}")

    # Write code to file
    try:
        source_code = tool_config["implementation"]["source_code"]
        with open(code_file, "w", encoding="utf-8") as f:
            f.write(source_code)
        print("      ✅ Code written successfully")
    except Exception as e:
        print(f"      ❌ Code writing failed: {e}")
        import traceback

        traceback.print_exc()

    # Read the generated code once
    with open(code_file, "r", encoding="utf-8") as f:
        code_content = f.read()

    # Validate generated code
    is_valid, error_info = _validate_generated_code(code_file, code_content)

    if not is_valid:
        # Try to fix syntax errors
        if not _fix_syntax_errors(tool_config, code_file, error_info, call_tool):
            # Save fallback file
            fallback_file = code_file.replace(".py", "_fallback.py")
            with open(fallback_file, "w", encoding="utf-8") as f:
                f.write(
                    "# Fallback file - contains syntax errors that need manual fixing\n"
                )
                f.write(f"# Original error: {error_info}\n\n")
                f.write(code_content)
            print(f"      📄 Fallback file saved: {fallback_file}")
            print(
                f"      ⚠️ Syntax error could not be automatically fixed. Please review {fallback_file}"
            )

            raise SyntaxError(
                f"Generated code has syntax error: {error_info}. "
                f"Fallback file saved to {fallback_file} for manual review."
            )

    # Validate class structure using cached content
    _validate_class_structure(code_content)


def compose(arguments, tooluniverse, call_tool):
    """General tool discovery and generation system"""
    tool_description = arguments["tool_description"]
    max_iterations = arguments.get("max_iterations", 2)
    arguments.get("save_to_file", True)
    save_dir = arguments.get("save_dir", None)

    # Determine where to save files
    import tempfile
    import shutil

    # If save_dir is provided, use it; otherwise use current working directory
    if save_dir:
        output_dir = os.path.abspath(save_dir)
    else:
        output_dir = os.getcwd()

    # Also create a temp directory for intermediate files during optimization
    temp_dir = tempfile.mkdtemp(prefix="tool_discover_")
    print(f"📁 Created temporary folder: {temp_dir}", flush=True)
    print(f"📁 Files will be saved to: {output_dir}", flush=True)

    try:
        print(f"🔍 Starting tool discovery: {tool_description}", flush=True)

        # 1. Collect reference information
        reference_info = _collect_reference_info(tool_description, call_tool)

        # 2. Generate tool specification AND implementation together (XML format)
        print("🏗️ Generating tool (specification + implementation)...", flush=True)
        tool_config = _generate_tool_with_xml(
            tool_description, reference_info, call_tool
        )

        # Display results
        print("\033[92mTool specification:\033[0m")
        config_display = {k: v for k, v in tool_config.items() if k != "implementation"}
        print(json.dumps(config_display, indent=4))

        print("\n💻 Implementation code:")
        print(
            "################################################################################"
        )
        print(tool_config["implementation"]["source_code"])
        print(
            "################################################################################"
        )

        # 4. Iterative optimization (handles runtime validation, testing, error fixing, and optimization)
        print("\n🚀 Phase: Iterative Optimization")
        target_quality_score = arguments.get("target_quality_score", 8.5)
        tool_config, final_quality_score, improvement_history = (
            iterative_comprehensive_optimization(
                tool_config,
                call_tool,
                max_iterations=max_iterations,
                target_score=target_quality_score,
                temp_dir=temp_dir,
            )
        )

        # Display final results
        if isinstance(final_quality_score, dict):
            score = final_quality_score.get("overall_score", 0)
        else:
            score = final_quality_score
        print(
            f"🎉 Implementation and optimization completed! Final quality score: {score:.2f}/10"
        )

        # 5. Save final tool files to output directory
        print("💾 Saving tool files...")
        base_filename = f"generated_tool_{tool_config['name']}"

        # First save to temp directory
        temp_saved_files = _save_tool_files(
            tool_config, base_filename, call_tool, temp_dir, None
        )
        print(f"Saved to temp: {temp_saved_files}")

        # Then copy to output directory
        saved_files = []
        os.makedirs(output_dir, exist_ok=True)

        for temp_file in temp_saved_files:
            filename = os.path.basename(temp_file)
            output_file = os.path.join(output_dir, filename)
            shutil.copy2(temp_file, output_file)
            saved_files.append(output_file)
            print(f"💾 Copied to output directory: {output_file}")

        print(f"\n✅ Saved files: {saved_files}")

        print("\n🎉 Tool generation completed!")
        print(f"Tool name: {tool_config['name']}")
        print(f"Tool type: {tool_config.get('type', 'Unknown')}")
        if isinstance(final_quality_score, dict):
            score = final_quality_score.get("overall_score", 0)
        else:
            score = final_quality_score
        print(f"Final quality: {score:.1f}/10")

        return {
            "tool_config": tool_config,
            "quality_score": final_quality_score,
            "saved_files": saved_files,
            "output_directory": output_dir,
        }

    finally:
        # Clean up temporary directory
        try:
            shutil.rmtree(temp_dir)
            print(f"🧹 Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            print(f"⚠️ Warning: Could not clean up temporary directory {temp_dir}: {e}")


# ============================================================================
# NEW CORE FUNCTIONS FOR REFACTORED SYSTEM
# ============================================================================


def optimize_code(tool_config, optimization_context, call_tool):
    """Wrapper function that calls the XML-based optimizer"""
    return _optimize_tool_with_xml(tool_config, optimization_context, call_tool)
