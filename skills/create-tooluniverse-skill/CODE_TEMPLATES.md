# Code Templates

Python implementation and test templates for ToolUniverse skills.

## python_implementation.py Template

```python
#!/usr/bin/env python3
"""
[DOMAIN NAME] - Python SDK Implementation
Replace [DOMAIN NAME], [domain], tool names, and parameters.
"""

from datetime import datetime
from tooluniverse import ToolUniverse


def domain_analysis_pipeline(
    input_param_1=None,
    input_param_2=None,
    organism="Homo sapiens",
    output_file=None,
):
    """[DOMAIN] analysis pipeline."""
    tu = ToolUniverse()
    tu.load_tools()

    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"domain_analysis_{timestamp}.md"

    report = []
    report.append("# [DOMAIN] Analysis Report\n")
    report.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    if input_param_1:
        report.append(f"**Input 1**: {input_param_1}\n")
    report.append(f"**Organism**: {organism}\n\n---\n")

    # Phase 1
    if input_param_1:
        report.append("\n## 1. [Phase 1 Name]\n")
        try:
            result = tu.tools.DATABASE1_TOOL(param=input_param_1)
            if isinstance(result, dict) and result.get("status") == "success":
                data = result.get("data", [])
                if data:
                    report.append(f"\n### Results ({len(data)} entries)\n")
                    report.append("\n| Col1 | Col2 |\n|------|------|\n")
                    for item in data[:10]:
                        report.append(f"| {item.get('f1','N/A')} | {item.get('f2','N/A')} |\n")
                else:
                    report.append("\n*No results found.*\n")
            elif isinstance(result, list) and result:
                report.append(f"\n### Results ({len(result)} entries)\n")
            else:
                report.append("\n*Data unavailable.*\n")
        except Exception as e:
            report.append(f"\n*Error: {e}*\n")

    # Phase 2, 3... (similar pattern)

    # Summary phase (always included)
    report.append("\n## Summary\n")

    with open(output_file, "w") as f:
        f.write("".join(report))
    print(f"Report generated: {output_file}")
    return output_file


if __name__ == "__main__":
    domain_analysis_pipeline(input_param_1="example", output_file="example.md")
```

## test_skill.py Template

```python
#!/usr/bin/env python3
"""Test script for [DOMAIN] skill."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from python_implementation import domain_analysis_pipeline


def test_basic():
    """Test basic analysis with single input."""
    output = domain_analysis_pipeline(input_param_1="test", output_file="test1.md")
    assert os.path.exists(output)
    with open(output) as f:
        content = f.read()
        assert "Analysis Report" in content
    print("PASS: basic analysis")


def test_multiple_inputs():
    """Test with multiple inputs."""
    output = domain_analysis_pipeline(
        input_param_1="v1", input_param_2="v2", output_file="test2.md"
    )
    assert os.path.exists(output)
    print("PASS: multiple inputs")


def test_error_handling():
    """Test graceful handling of invalid input."""
    try:
        output = domain_analysis_pipeline(
            input_param_1="INVALID_XYZ", output_file="test3.md"
        )
        assert os.path.exists(output)
        print("PASS: error handling")
    except Exception as e:
        print(f"FAIL: crashed with {e}")
        raise


def main():
    tests = [test_basic, test_multiple_inputs, test_error_handling]
    passed = failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"FAIL: {t.__name__}: {e}")
            failed += 1
    print(f"\nResults: {passed}/{len(tests)} passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
```

## test_tools_template.py Template

See `test_tools_template.py` in this directory for the tool-testing script template. Key steps:
1. Load ToolUniverse once
2. Test each tool with known-good params
3. Check response format (standard dict, direct list, direct dict)
4. Detect SOAP tools (retry with `operation` param)
5. Print parameter corrections table and response format notes

## Response Format Handling

Three formats tools may return:
- **Standard**: `{status: "success", data: [...]}`
- **Direct list**: `[...]` without wrapper
- **Direct dict**: `{field1: ..., field2: ...}` without status

Handle all three with `isinstance()` checks in implementation.
