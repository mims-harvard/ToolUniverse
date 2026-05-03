"""Dynamic package discovery and evaluation"""

import requests
import time
from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("DynamicPackageDiscovery")
class DynamicPackageDiscovery(BaseTool):
    """Searches PyPI and evaluates packages dynamically based on requirements"""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.pypi_search_url = "https://pypi.org/pypi/{package}/json"
        self.pypi_search_api = "https://pypi.org/search/"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "ToolUniverse-PackageDiscovery/1.0"})

        # Initialize WebSearchTool instance
        from .web_search_tool import WebSearchTool

        self.web_search_tool = WebSearchTool({"name": "WebSearchTool"})

    def _search_pypi_via_web(self, query: str) -> List[Dict[str, Any]]:
        """Search PyPI using web search tool"""
        try:
            # Use pre-initialized WebSearchTool instance
            result = self.web_search_tool.run(
                {
                    "query": f"{query} site:pypi.org",
                    "max_results": 10,
                    "search_type": "python_packages",
                }
            )

            packages = []
            if result.get("status") == "success":
                for item in result.get("results", []):
                    url = item.get("url", "")
                    if "pypi.org/project/" in url:
                        # Extract package name from URL
                        pkg_name = url.split("/project/")[-1].rstrip("/")
                        packages.append(
                            {
                                "name": pkg_name,
                                "source": "pypi_web",
                                "title": item.get("title", ""),
                                "snippet": item.get("snippet", ""),
                                "url": url,
                            }
                        )

            return packages
        except Exception as e:
            print(f"⚠️ Web search for PyPI packages failed: {e}")
            return []

    def _evaluate_package(self, package_name: str) -> Dict[str, Any]:
        """Evaluate a package's suitability by fetching PyPI metadata"""
        try:
            response = self.session.get(
                self.pypi_search_url.format(package=package_name), timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                info = data.get("info", {})
                urls = info.get("project_urls", {})

                # Extract key metrics
                evaluation = {
                    "name": package_name,
                    "version": info.get("version"),
                    "description": info.get("summary", ""),
                    "author": info.get("author", ""),
                    "license": info.get("license", ""),
                    "home_page": info.get("home_page", ""),
                    "download_url": info.get("download_url", ""),
                    "requires_python": info.get("requires_python", ""),
                    "dependencies": info.get("requires_dist", []),
                    "classifiers": info.get("classifiers", []),
                    # Quality indicators
                    "has_docs": bool(urls.get("Documentation")),
                    "has_source": bool(urls.get("Source")),
                    "has_homepage": bool(info.get("home_page")),
                    "has_bug_tracker": bool(urls.get("Bug Reports")),
                    "project_urls": urls,
                    # Popularity indicators
                    "is_stable": "Development Status :: 5 - Production/Stable"
                    in info.get("classifiers", []),
                    "is_mature": "Development Status :: 6 - Mature"
                    in info.get("classifiers", []),
                    "has_tests": "Topic :: Software Development :: Testing"
                    in info.get("classifiers", []),
                    "is_typed": "Typing :: Typed" in info.get("classifiers", []),
                }

                # Calculate a basic quality score
                quality_score = 0
                if evaluation["has_docs"]:
                    quality_score += 20
                if evaluation["has_source"]:
                    quality_score += 15
                if evaluation["is_stable"] or evaluation["is_mature"]:
                    quality_score += 25
                if evaluation["has_tests"]:
                    quality_score += 15
                if evaluation["is_typed"]:
                    quality_score += 10
                if evaluation["has_homepage"]:
                    quality_score += 10
                if evaluation["has_bug_tracker"]:
                    quality_score += 5

                evaluation["quality_score"] = min(quality_score, 100)

                return evaluation
            else:
                return {
                    "name": package_name,
                    "error": f"HTTP {response.status_code}",
                    "quality_score": 0,
                }

        except Exception as e:
            return {"name": package_name, "error": str(e), "quality_score": 0}

    def _rank_packages(
        self, packages: List[Dict[str, Any]], requirements: str, functionality: str
    ) -> List[Dict[str, Any]]:
        """Rank packages by relevance and quality"""
        if not packages:
            return []

        # Filter out packages with errors
        valid_packages = [pkg for pkg in packages if "error" not in pkg]

        # Sort by quality score (descending)
        ranked = sorted(
            valid_packages, key=lambda x: x.get("quality_score", 0), reverse=True
        )

        # Add ranking metadata
        for i, pkg in enumerate(ranked):
            pkg["rank"] = i + 1
            pkg["reasoning"] = f"Quality score: {pkg.get('quality_score', 0)}/100"

        return ranked

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dynamically discover and evaluate packages

        Args:
            requirements: Description of what's needed
            functionality: Specific functionality required
            constraints: Any constraints (Python version, license, etc.)
        """
        try:
            requirements = arguments.get("requirements", "")
            functionality = arguments.get("functionality", "")

            # Search for candidate packages
            search_query = f"{requirements} {functionality}".strip()
            print(f"🔍 Searching for packages: {search_query}")

            candidates = self._search_pypi_via_web(search_query)

            if not candidates:
                result = {
                    "status": "success",
                    "candidates": [],
                    "recommendation": None,
                    "message": "No packages found",
                }
                return {"status": "success", "data": result}

            print(f"📦 Found {len(candidates)} package candidates")

            # Evaluate each candidate
            evaluated = []
            for i, pkg in enumerate(candidates):
                print(f"  Evaluating {i + 1}/{len(candidates)}: {pkg['name']}")
                evaluation = self._evaluate_package(pkg["name"])
                # Merge web search info with PyPI evaluation
                evaluation.update({k: v for k, v in pkg.items() if k not in evaluation})
                evaluated.append(evaluation)

                # Rate limiting
                time.sleep(0.2)

            # Rank by suitability
            ranked = self._rank_packages(evaluated, requirements, functionality)

            top_recommendation = ranked[0] if ranked else None

            if top_recommendation:
                score = top_recommendation.get("quality_score", 0)
                print(
                    f"🏆 Top recommendation: {top_recommendation['name']} (score: {score})"
                )

            result = {
                "status": "success",
                "candidates": ranked,
                "recommendation": top_recommendation,
                "total_evaluated": len(evaluated),
            }

            return {"status": "success", "data": result}

        except Exception as e:
            error_result = {
                "status": "error",
                "error": str(e),
                "candidates": [],
                "recommendation": None,
            }

            return {"status": "error", "data": error_result}
