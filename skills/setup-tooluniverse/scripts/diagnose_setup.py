#!/usr/bin/env python3
"""
Comprehensive diagnostic tool for ToolUniverse setup issues.

Generates a detailed report covering:
- System information
- Python environment
- Installation status
- Configuration validation
- Common issue detection
"""

import sys
import subprocess
import platform
import json
import shutil
from pathlib import Path
from datetime import datetime


class DiagnosticReport:
    """Generate comprehensive diagnostic report."""
    
    def __init__(self):
        self.report = []
        self.issues = []
        self.warnings = []
    
    def add_section(self, title):
        """Add a section header."""
        self.report.append(f"\n{'=' * 60}")
        self.report.append(f"{title}")
        self.report.append(f"{'=' * 60}")
    
    def add_line(self, line):
        """Add a line to report."""
        self.report.append(line)
    
    def add_issue(self, issue):
        """Add an issue."""
        self.issues.append(issue)
        self.report.append(f"❌ ISSUE: {issue}")
    
    def add_warning(self, warning):
        """Add a warning."""
        self.warnings.append(warning)
        self.report.append(f"⚠️  WARNING: {warning}")
    
    def add_success(self, message):
        """Add a success message."""
        self.report.append(f"✓ {message}")
    
    def get_report(self):
        """Get full report as string."""
        return "\n".join(self.report)
    
    def save_report(self, filename):
        """Save report to file."""
        with open(filename, 'w') as f:
            f.write(self.get_report())


def check_system_info(report):
    """Gather system information."""
    report.add_section("System Information")
    
    report.add_line(f"Platform: {platform.system()} {platform.release()}")
    report.add_line(f"Machine: {platform.machine()}")
    report.add_line(f"Processor: {platform.processor()}")
    report.add_line(f"Python version: {sys.version}")
    report.add_line(f"Python executable: {sys.executable}")


def check_python_environment(report):
    """Check Python environment details."""
    report.add_section("Python Environment")
    
    # Check Python version compatibility
    version = sys.version_info
    if version.major == 3 and 10 <= version.minor < 14:
        report.add_success(f"Python {version.major}.{version.minor}.{version.micro} (compatible)")
    else:
        report.add_issue(f"Python {version.major}.{version.minor} not compatible (need 3.10-3.13)")
    
    # Check pip
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        report.add_success(f"pip: {result.stdout.strip()}")
    except subprocess.CalledProcessError:
        report.add_issue("pip not available")
    
    # Check site-packages
    try:
        import site
        report.add_line(f"Site packages: {site.getsitepackages()}")
    except Exception:
        report.add_warning("Could not determine site-packages location")


def check_tooluniverse_installation(report):
    """Check ToolUniverse installation status."""
    report.add_section("ToolUniverse Installation")
    
    # Try to import
    try:
        import tooluniverse
        report.add_success(f"ToolUniverse imported: version {tooluniverse.__version__}")
        
        # Get installation location
        tu_path = Path(tooluniverse.__file__).parent
        report.add_line(f"Installation path: {tu_path}")
        
        # Try to load tools
        try:
            from tooluniverse import ToolUniverse
            tu = ToolUniverse()
            report.add_line("Attempting to load tools...")
            tu.load_tools()
            tool_count = len(tu.tools)
            report.add_success(f"Loaded {tool_count} tools")
            
            if tool_count < 700:
                report.add_warning(f"Expected ~764 tools, only loaded {tool_count}")
        except Exception as e:
            report.add_issue(f"Could not load tools: {e}")
    
    except ImportError as e:
        report.add_issue(f"ToolUniverse not installed: {e}")
        report.add_line("Install with: pip install tooluniverse")


def check_cli_commands(report):
    """Check CLI command availability."""
    report.add_section("CLI Commands")
    
    commands = [
        "tooluniverse-smcp-stdio",
        "tooluniverse-smcp-server",
        "tooluniverse-smcp",
        "tooluniverse-http-api",
    ]
    
    for cmd in commands:
        cmd_path = shutil.which(cmd)
        if cmd_path:
            report.add_success(f"{cmd}: {cmd_path}")
        else:
            report.add_issue(f"{cmd} not found in PATH")


def check_mcp_configuration(report):
    """Check MCP configuration files."""
    report.add_section("MCP Configuration")
    
    system = platform.system()
    
    # Determine config locations
    if system == "Darwin":  # macOS
        cursor_config = Path.home() / "Library" / "Application Support" / "Cursor" / "User" / "mcp.json"
        claude_config = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "Windows":
        cursor_config = Path.home() / "AppData" / "Roaming" / "Cursor" / "User" / "mcp.json"
        claude_config = Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
    else:  # Linux
        cursor_config = Path.home() / ".config" / "Cursor" / "User" / "mcp.json"
        claude_config = Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
    
    configs = [
        ("Cursor", cursor_config),
        ("Claude Desktop", claude_config),
    ]
    
    found_any = False
    
    for app_name, config_path in configs:
        if config_path.exists():
            found_any = True
            report.add_success(f"{app_name} config found: {config_path}")
            
            # Parse and validate
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                
                # Check for ToolUniverse
                if "mcpServers" in config and "tooluniverse" in config["mcpServers"]:
                    tu_config = config["mcpServers"]["tooluniverse"]
                    report.add_success("ToolUniverse server configured")
                    report.add_line(f"  Command: {tu_config.get('command')}")
                    report.add_line(f"  Args: {tu_config.get('args', [])}")
                    
                    # Check for compact mode
                    if "--compact-mode" in tu_config.get("args", []):
                        report.add_success("Compact mode enabled")
                    else:
                        report.add_warning("Compact mode not enabled (may cause context overflow)")
                else:
                    report.add_warning(f"ToolUniverse not configured in {app_name}")
            
            except json.JSONDecodeError as e:
                report.add_issue(f"Invalid JSON in {config_path}: {e}")
            except Exception as e:
                report.add_warning(f"Could not parse {config_path}: {e}")
        else:
            report.add_line(f"{app_name} config not found: {config_path}")
    
    if not found_any:
        report.add_warning("No MCP configuration files found")


def check_optional_dependencies(report):
    """Check optional dependencies."""
    report.add_section("Optional Dependencies")
    
    deps = {
        "sentence_transformers": "ML/embedding tools",
        "cellxgene_census": "Single-cell tools",
        "biopython": "Bioinformatics tools",
        "rdkit": "Chemistry tools",
        "py3Dmol": "3D visualization",
    }
    
    for package, purpose in deps.items():
        try:
            __import__(package)
            report.add_success(f"{package} installed ({purpose})")
        except ImportError:
            report.add_line(f"{package} not installed ({purpose})")


def check_common_issues(report):
    """Check for common setup issues."""
    report.add_section("Common Issues Check")
    
    # Issue 1: PATH not including scripts
    scripts_in_path = any(
        "scripts" in p.lower() or "bin" in p.lower()
        for p in sys.path
    )
    if scripts_in_path:
        report.add_success("Scripts directory appears to be in PATH")
    else:
        report.add_warning("Scripts directory may not be in PATH")
    
    # Issue 2: Multiple Python installations
    try:
        result = subprocess.run(
            ["which", "-a", "python3"],
            capture_output=True,
            text=True,
            check=True
        )
        python_installs = result.stdout.strip().split('\n')
        if len(python_installs) > 1:
            report.add_warning(f"Multiple Python installations found: {python_installs}")
            report.add_line("Ensure you're using the correct one")
        else:
            report.add_success(f"Single Python installation: {python_installs[0]}")
    except Exception:
        pass  # Windows or other systems
    
    # Issue 3: Disk space
    try:
        stat = shutil.disk_usage(Path.home())
        free_gb = stat.free / (1024**3)
        if free_gb < 1:
            report.add_warning(f"Low disk space: {free_gb:.2f} GB free")
        else:
            report.add_success(f"Disk space: {free_gb:.2f} GB free")
    except Exception:
        pass


def generate_recommendations(report):
    """Generate recommendations based on findings."""
    report.add_section("Recommendations")
    
    if report.issues:
        report.add_line("\n🔴 Critical Issues to Fix:")
        for i, issue in enumerate(report.issues, 1):
            report.add_line(f"  {i}. {issue}")
    
    if report.warnings:
        report.add_line("\n🟡 Warnings to Review:")
        for i, warning in enumerate(report.warnings, 1):
            report.add_line(f"  {i}. {warning}")
    
    if not report.issues and not report.warnings:
        report.add_line("\n✅ No issues detected! Setup looks good.")
    
    report.add_line("\n📚 Next Steps:")
    if report.issues:
        report.add_line("  1. Fix critical issues listed above")
        report.add_line("  2. Rerun: python scripts/diagnose_setup.py")
    else:
        report.add_line("  1. Restart Cursor or Claude Desktop")
        report.add_line("  2. Verify MCP server appears")
        report.add_line("  3. Test with: list_tools or grep_tools")


def main():
    """Run comprehensive diagnostics."""
    report = DiagnosticReport()
    
    report.add_section("ToolUniverse Setup Diagnostic Report")
    report.add_line(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run all checks
    check_system_info(report)
    check_python_environment(report)
    check_tooluniverse_installation(report)
    check_cli_commands(report)
    check_mcp_configuration(report)
    check_optional_dependencies(report)
    check_common_issues(report)
    generate_recommendations(report)
    
    # Print report
    print(report.get_report())
    
    # Save to file
    output_file = Path("tooluniverse_diagnostic_report.txt")
    report.save_report(output_file)
    
    print(f"\n\n📄 Report saved to: {output_file.absolute()}")
    
    # Return status
    if report.issues:
        print("\n❌ Issues detected - see report above")
        return 1
    else:
        print("\n✅ Diagnostic complete - no critical issues")
        return 0


if __name__ == "__main__":
    sys.exit(main())
