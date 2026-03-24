# package_tool.py

import requests
import json
from .base_tool import BaseTool
from typing import Dict, Any
from .tool_registry import register_tool


@register_tool("PackageTool")
class PackageTool(BaseTool):
    """
    Universal tool to provide information about Python packages.
    Fetches real-time data from PyPI API with local fallback.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.package_name = tool_config.get("package_name", "")
        self.local_info = tool_config.get("local_info", {})
        self.pypi_timeout = tool_config.get("pypi_timeout", 5)

    def run(self, arguments):
        """
        Get comprehensive package information.

        Args:
            arguments (dict): Optional parameters for customization

        Returns
            dict: Package information including name, description, installation, docs, usage
        """
        include_examples = arguments.get("include_examples", True)
        source = arguments.get("source", "auto")  # 'auto', 'pypi', 'local'

        try:
            if source == "local":
                return self._get_local_info(include_examples)
            elif source == "pypi":
                return self._get_pypi_info(include_examples)
            else:  # auto - try PyPI first, fallback to local
                try:
                    return self._get_pypi_info(include_examples)
                except Exception as e:
                    print(f"PyPI fetch failed: {e}, falling back to local info")
                    return self._get_local_info(include_examples)

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to get package information: {str(e)}",
                "package_name": self.package_name,
            }

    def _get_pypi_info(self, include_examples: bool = True) -> Dict[str, Any]:
        """Fetch package information from PyPI API"""
        url = f"https://pypi.org/pypi/{self.package_name}/json"

        try:
            response = requests.get(url, timeout=self.pypi_timeout)
            response.raise_for_status()
            pypi_data = response.json()

            info = pypi_data.get("info", {})

            # Build response with PyPI data
            result = {
                "package_name": info.get("name", self.package_name),
                "description": info.get("summary", "No description available"),
                "version": info.get("version", "Unknown"),
                "author": info.get("author", "Unknown"),
                "license": info.get("license", "Not specified"),
                "home_page": info.get("home_page", ""),
                "documentation": info.get("project_urls", {}).get("Documentation", ""),
                "repository": info.get("project_urls", {}).get(
                    "Repository", info.get("project_urls", {}).get("Source", "")
                ),
                "python_versions": info.get("classifiers", []),
                "keywords": (
                    info.get("keywords", "").split(",") if info.get("keywords") else []
                ),
                "installation": {
                    "pip": f"pip install {self.package_name}",
                    "conda": f"conda install {self.package_name}",
                    "pip_upgrade": f"pip install --upgrade {self.package_name}",
                },
                "source": "pypi",
                "last_updated": pypi_data.get("last_serial", "Unknown"),
            }

            # Merge with local enhanced information
            local_info = self.local_info
            if local_info:
                result["category"] = local_info.get("category", "General")
                result["import_name"] = local_info.get("import_name", self.package_name)
                result["popularity"] = local_info.get("popularity", 0)

                # Override with better local descriptions if available
                if local_info.get("description") and len(
                    local_info["description"]
                ) > len(result["description"]):
                    result["description"] = local_info["description"]

                # Add local documentation if PyPI doesn't have it
                if not result["documentation"] and local_info.get("documentation"):
                    result["documentation"] = local_info["documentation"]

                # Add custom installation instructions
                if local_info.get("installation"):
                    result["installation"].update(local_info["installation"])

            # Add examples if requested
            if include_examples:
                result["usage_example"] = self._get_usage_example()
                result["quick_start"] = self._get_quick_start_guide()

            return result

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch from PyPI: {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse PyPI response: {str(e)}")

    def _get_local_info(self, include_examples: bool = True) -> Dict[str, Any]:
        """Get package information from local configuration"""
        if not self.local_info:
            return {
                "status": "error",
                "error": f"No local information available for package '{self.package_name}'",
                "package_name": self.package_name,
            }

        result = {
            "package_name": self.local_info.get("name", self.package_name),
            "description": self.local_info.get(
                "description", "No description available"
            ),
            "version": self.local_info.get("version", "Check PyPI for latest"),
            "category": self.local_info.get("category", "General"),
            "license": self.local_info.get("license", "Not specified"),
            "documentation": self.local_info.get("documentation", ""),
            "repository": self.local_info.get("repository", ""),
            "import_name": self.local_info.get("import_name", self.package_name),
            "python_versions": self.local_info.get("python_versions", ["3.6+"]),
            "dependencies": self.local_info.get("dependencies", []),
            "popularity": self.local_info.get("popularity", 0),
            "keywords": self.local_info.get("keywords", []),
            "installation": self._get_installation_instructions(),
            "source": "local",
        }

        if include_examples:
            result["usage_example"] = self._get_usage_example()
            result["quick_start"] = self._get_quick_start_guide()

        return result

    def _get_installation_instructions(self) -> Dict[str, str]:
        """Generate installation instructions"""
        custom_install = self.local_info.get("installation", {})

        instructions = {
            "pip": custom_install.get("pip", f"pip install {self.package_name}"),
            "conda": custom_install.get("conda", f"conda install {self.package_name}"),
            "pip_upgrade": f"pip install --upgrade {self.package_name}",
        }

        # Add additional installation methods if specified
        if "additional" in custom_install:
            instructions.update(custom_install["additional"])

        return instructions

    def _get_usage_example(self) -> str:
        """Get usage example for the package"""
        if self.local_info.get("usage_example"):
            return self.local_info["usage_example"]

        import_name = self.local_info.get("import_name", self.package_name)
        return f"""# Basic usage example for {self.package_name}
import {import_name}

# Add your code here - check the documentation for specific usage
print({import_name}.__version__)"""

    def _get_quick_start_guide(self) -> list:
        """Get quick start guide steps"""
        if self.local_info.get("quick_start"):
            return self.local_info["quick_start"]

        import_name = self.local_info.get("import_name", self.package_name)
        return [
            f"1. Install the package: pip install {self.package_name}",
            f"2. Import in your Python code: import {import_name}",
            "3. Check the documentation for detailed usage examples",
            "4. Start with basic examples and gradually explore advanced features",
        ]
