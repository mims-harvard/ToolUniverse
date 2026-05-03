#!/usr/bin/env python3
"""
Analyze all tool configuration files in src/tooluniverse/data
to identify tools that don't cover all endpoint resources.
"""

import os
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

def analyze_tool_config(filepath: str) -> Dict[str, Any]:
    """Analyze a single tool configuration file"""
    try:
        with open(filepath, 'r') as f:
            tools = json.load(f)
        
        if not isinstance(tools, list):
            tools = [tools]
        
        analysis = {
            'file': os.path.basename(filepath),
            'filepath': filepath,
            'tool_count': len(tools),
            'tools': [],
            'issues': [],
            'missing_fields': [],
            'endpoints': set(),
            'has_return_schema': 0,
            'has_test_examples': 0,
            'has_description': 0,
        }
        
        for tool in tools:
            tool_info = {
                'name': tool.get('name', 'UNNAMED'),
                'type': tool.get('type', 'UNKNOWN'),
                'has_description': bool(tool.get('description')),
                'has_return_schema': bool(tool.get('return_schema')),
                'has_test_examples': bool(tool.get('test_examples')),
                'parameter_count': 0,
                'required_params': 0,
                'endpoint': tool.get('fields', {}).get('endpoint', ''),
            }
            
            # Check parameter schema
            if 'parameter' in tool:
                params = tool['parameter']
                if isinstance(params, dict) and 'properties' in params:
                    tool_info['parameter_count'] = len(params.get('properties', {}))
                    tool_info['required_params'] = len(params.get('required', []))
            
            # Track endpoints
            if tool_info['endpoint']:
                analysis['endpoints'].add(tool_info['endpoint'])
            
            # Check for missing fields and count present ones
            for field in ('description', 'return_schema', 'test_examples'):
                has_key = f'has_{field}'
                if tool_info[has_key]:
                    analysis[has_key] += 1
                else:
                    analysis['missing_fields'].append(f"{tool_info['name']}: missing {field}")
            
            analysis['tools'].append(tool_info)
        
        # Convert endpoints set to list for JSON serialization
        analysis['endpoints'] = list(analysis['endpoints'])
        
        return analysis
        
    except json.JSONDecodeError as e:
        return {
            'file': os.path.basename(filepath),
            'filepath': filepath,
            'error': f'JSON decode error: {str(e)}',
            'tool_count': 0,
        }
    except Exception as e:
        return {
            'file': os.path.basename(filepath),
            'filepath': filepath,
            'error': f'Error: {str(e)}',
            'tool_count': 0,
        }

def analyze_all_configs(data_dir: str = 'src/tooluniverse/data') -> Dict[str, Any]:
    """Analyze all tool configuration files"""
    data_path = Path(data_dir)
    
    if not data_path.exists():
        print(f"Error: Directory {data_dir} does not exist")
        return {}
    
    results = {
        'total_files': 0,
        'total_tools': 0,
        'files_with_errors': 0,
        'files_analyzed': [],
        'summary': {
            'files_without_return_schema': [],
            'files_without_test_examples': [],
            'files_without_descriptions': [],
            'files_with_single_tool': [],
            'files_with_many_tools': [],
        },
        'by_category': defaultdict(list),
    }
    
    # Find all JSON files
    json_files = list(data_path.glob('*.json'))
    json_files.extend(data_path.glob('**/*.json'))  # Include subdirectories
    
    # Remove duplicates
    json_files = list(set(json_files))
    json_files.sort()
    
    results['total_files'] = len(json_files)
    
    print(f"Found {len(json_files)} JSON configuration files")
    print("Analyzing...")
    
    for json_file in json_files:
        if json_file.name.startswith('.'):
            continue
            
        analysis = analyze_tool_config(str(json_file))
        results['files_analyzed'].append(analysis)
        
        if 'error' in analysis:
            results['files_with_errors'] += 1
            print(f"  ERROR: {analysis['file']} - {analysis.get('error', 'Unknown error')}")
            continue
        
        results['total_tools'] += analysis['tool_count']
        
        # Categorize
        if analysis['tool_count'] == 0:
            continue
        elif analysis['tool_count'] == 1:
            results['summary']['files_with_single_tool'].append(analysis['file'])
        elif analysis['tool_count'] > 20:
            results['summary']['files_with_many_tools'].append({
                'file': analysis['file'],
                'count': analysis['tool_count']
            })
        
        # Check for missing fields
        _field_to_summary = {
            'has_return_schema': 'files_without_return_schema',
            'has_test_examples': 'files_without_test_examples',
            'has_description': 'files_without_descriptions',
        }
        for field_key, summary_key in _field_to_summary.items():
            missing = analysis['tool_count'] - analysis[field_key]
            if missing > 0:
                results['summary'][summary_key].append({
                    'file': analysis['file'],
                    'missing': missing,
                    'total': analysis['tool_count'],
                })
        
        # Categorize by tool type
        tool_types = set(t['type'] for t in analysis['tools'])
        for tool_type in tool_types:
            results['by_category'][tool_type].append(analysis['file'])
    
    return results

def generate_report(results: Dict[str, Any], output_file: str = 'COMPREHENSIVE_TOOL_ANALYSIS.md'):
    """Generate a comprehensive markdown report"""
    
    report_lines = [
        "# Comprehensive Tool Configuration Analysis",
        "",
        "**Generated:** Automated analysis of all tool configuration files",
        "**Purpose:** Identify tools with incomplete configurations and missing endpoint coverage",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        f"- **Total Configuration Files:** {results['total_files']}",
        f"- **Total Tools:** {results['total_tools']}",
        f"- **Files with Errors:** {results['files_with_errors']}",
        "",
        "### Key Findings",
        "",
        f"- **Files missing return_schema:** {len(results['summary']['files_without_return_schema'])}",
        f"- **Files missing test_examples:** {len(results['summary']['files_without_test_examples'])}",
        f"- **Files missing descriptions:** {len(results['summary']['files_without_descriptions'])}",
        f"- **Files with single tool:** {len(results['summary']['files_with_single_tool'])}",
        f"- **Files with 20+ tools:** {len(results['summary']['files_with_many_tools'])}",
        "",
        "---",
        "",
    ]

    # Sections 1-3: missing field tables (identical structure, different data)
    _missing_sections = [
        ("1", "Return Schema", "return_schema definitions", "files_without_return_schema"),
        ("2", "Test Examples", "test_examples", "files_without_test_examples"),
        ("3", "Descriptions", "descriptions", "files_without_descriptions"),
    ]
    for num, label, desc_suffix, summary_key in _missing_sections:
        items = sorted(
            results['summary'][summary_key],
            key=lambda x: x['missing'], reverse=True,
        )[:50]
        report_lines.extend([
            f"## {num}. Files Missing {label}",
            "",
            f"These files have tools without {desc_suffix}:",
            "",
            "| File | Missing | Total Tools |",
            "|------|---------|-------------|",
        ])
        for item in items:
            report_lines.append(f"| {item['file']} | {item['missing']} | {item['total']} |")
        report_lines.extend(["", "---", ""])

    report_lines.extend([
        "## 4. Files with Many Tools (20+)",
        "",
        "These files contain many tools and may need endpoint coverage verification:",
        "",
        "| File | Tool Count |",
        "|------|-----------|",
    ])
    
    for item in sorted(results['summary']['files_with_many_tools'],
                      key=lambda x: x['count'], reverse=True):
        report_lines.append(f"| {item['file']} | {item['count']} |")
    
    report_lines.extend([
        "",
        "---",
        "",
        "## 5. Tool Categories",
        "",
        "Tools grouped by type:",
        "",
    ])
    
    for tool_type, files in sorted(results['by_category'].items()):
        report_lines.append(f"### {tool_type}")
        report_lines.append(f"- **Files:** {len(files)}")
        report_lines.append(f"- **Sample files:** {', '.join(files[:5])}")
        if len(files) > 5:
            report_lines.append(f"- *... and {len(files) - 5} more*")
        report_lines.append("")
    
    report_lines.extend([
        "",
        "---",
        "",
        "## 6. Detailed File Analysis",
        "",
        "### Files Requiring Attention",
        "",
    ])
    
    # Find files with issues
    files_with_issues = []
    for analysis in results['files_analyzed']:
        if 'error' in analysis:
            continue
        
        issues = []
        for field_key, label in [
            ('has_return_schema', 'return_schema'),
            ('has_test_examples', 'test_example'),
            ('has_description', 'description'),
        ]:
            missing = analysis['tool_count'] - analysis[field_key]
            if missing > 0:
                issues.append(f"Missing {missing} {label}(s)")
        
        if issues:
            files_with_issues.append({
                'file': analysis['file'],
                'tool_count': analysis['tool_count'],
                'issues': issues,
                'missing_fields': analysis.get('missing_fields', [])[:5]  # First 5
            })
    
    # Sort by number of issues
    files_with_issues.sort(key=lambda x: len(x['issues']), reverse=True)
    
    report_lines.append("| File | Tool Count | Issues |")
    report_lines.append("|------|-----------|--------|")
    
    for item in files_with_issues[:100]:  # Top 100
        issues_str = "; ".join(item['issues'])
        report_lines.append(f"| {item['file']} | {item['tool_count']} | {issues_str} |")
    
    report_lines.extend([
        "",
        "---",
        "",
        "## 7. Next Steps",
        "",
        "1. **Review files with missing return_schema** - Add return schemas for all tools",
        "2. **Review files with missing test_examples** - Add test examples for all tools",
        "3. **Review files with missing descriptions** - Add descriptions for all tools",
        "4. **Verify endpoint coverage** - Check if tools cover all available API endpoints",
        "5. **Check large tool files** - Files with 20+ tools may need endpoint verification",
        "",
        "---",
        "",
        "**Report Status:** Complete",
        f"**Total Files Analyzed:** {results['total_files']}",
        f"**Total Tools Found:** {results['total_tools']}",
    ])
    
    report = "\n".join(report_lines)
    
    with open(output_file, 'w') as f:
        f.write(report)
    
    print(f"\nReport written to: {output_file}")
    return output_file

def main():
    print("ToolUniverse Configuration Analyzer")
    print("=" * 50)
    
    # Analyze all configs
    results = analyze_all_configs()
    
    # Print summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Total files: {results['total_files']}")
    print(f"Total tools: {results['total_tools']}")
    print(f"Files with errors: {results['files_with_errors']}")
    print(f"\nFiles missing return_schema: {len(results['summary']['files_without_return_schema'])}")
    print(f"Files missing test_examples: {len(results['summary']['files_without_test_examples'])}")
    print(f"Files missing descriptions: {len(results['summary']['files_without_descriptions'])}")
    
    # Generate report
    report_file = generate_report(results)
    print(f"\nDetailed report saved to: {report_file}")
    
    # Also save JSON for programmatic access
    json_file = report_file.replace('.md', '.json')
    with open(json_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"JSON data saved to: {json_file}")

if __name__ == '__main__':
    main()
