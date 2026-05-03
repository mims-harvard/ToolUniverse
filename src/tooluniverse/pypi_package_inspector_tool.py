"""PyPI Package Inspector - Comprehensive package information extraction"""

import requests
import time
from datetime import datetime, timedelta
from typing import Dict, Any
from .tool_registry import register_tool
from .base_tool import BaseTool


# @register_tool(
#     "PyPIPackageInspector",
#     config={
#         "name": "PyPIPackageInspector",
#         "type": "PyPIPackageInspector",
#         "description": (
#             "Extracts comprehensive package information from PyPI and GitHub "
#             "for quality evaluation. Provides detailed metrics on popularity, "
#             "maintenance, security, and compatibility."
#         ),
#         "parameter": {
#             "type": "object",
#             "properties": {
#                 "package_name": {
#                     "type": "string",
#                     "description": "Name of the Python package to inspect",
#                 },
#                 "include_github": {
#                     "type": "boolean",
#                     "description": "Whether to fetch GitHub statistics",
#                     "default": True,
#                 },
#                 "include_downloads": {
#                     "type": "boolean",
#                     "description": "Whether to fetch download statistics",
#                     "default": True,
#                 },
#             },
#             "required": ["package_name"],
#         },
#     },
# )
class PyPIPackageInspector(BaseTool):
    """
    Extracts comprehensive package information from PyPI and GitHub.
    Provides detailed metrics on popularity, maintenance, security,
    and compatibility.
    """

    def __init__(self, tool_config: Dict[str, Any] = None):
        BaseTool.__init__(self, tool_config or {})
        self.pypi_api_url = "https://pypi.org/pypi/{package}/json"
        self.pypistats_api_url = "https://pypistats.org/api/packages/{package}/recent"
        self.github_api_url = "https://api.github.com/repos/{owner}/{repo}"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "ToolUniverse-PyPIInspector/1.0",
                "Accept": "application/vnd.github.v3+json",
            }
        )

        # GitHub token if available
        github_token = self.tool_config.get("github_token")
        if github_token:
            self.session.headers["Authorization"] = f"token {github_token}"

    def _get_pypi_metadata(self, package_name: str) -> Dict[str, Any]:
        """Fetch comprehensive metadata from PyPI"""
        try:
            response = self.session.get(
                self.pypi_api_url.format(package=package_name), timeout=10
            )

            if response.status_code == 404:
                return {"status": "error", "error": "Package not found on PyPI"}

            response.raise_for_status()
            data = response.json()

            info = data.get("info", {})
            releases = data.get("releases", {})
            urls = data.get("urls", [])

            # Parse project URLs to find GitHub repo
            project_urls = info.get("project_urls", {})
            github_url = None
            for _key, url in project_urls.items():
                if url and "github.com" in url.lower():
                    github_url = url
                    break

            # If no project URLs, check home_page
            if not github_url and info.get("home_page"):
                if "github.com" in info.get("home_page", "").lower():
                    github_url = info["home_page"]

            # Get release history
            release_dates = []
            for _version, files in releases.items():
                if files:
                    upload_time = files[0].get("upload_time_iso_8601")
                    if upload_time:
                        try:
                            date = datetime.fromisoformat(
                                upload_time.replace("Z", "+00:00")
                            )
                            release_dates.append(date)
                        except (ValueError, AttributeError):
                            pass

            release_dates.sort(reverse=True)

            # Calculate maintenance metrics
            latest_release = release_dates[0] if release_dates else None
            days_since_last_release = None
            if latest_release:
                time_diff = datetime.now(latest_release.tzinfo) - latest_release
                days_since_last_release = time_diff.days

            # Count recent releases (last year)
            one_year_ago = datetime.now() - timedelta(days=365)
            recent_releases = sum(
                1 for date in release_dates if date.replace(tzinfo=None) > one_year_ago
            )

            return {
                "name": info.get("name"),
                "version": info.get("version"),
                "summary": info.get("summary", ""),
                "description_length": len(info.get("description", "")),
                "author": info.get("author", ""),
                "author_email": info.get("author_email", ""),
                "maintainer": info.get("maintainer", ""),
                "license": info.get("license", ""),
                "requires_python": info.get("requires_python", ""),
                "requires_dist": info.get("requires_dist", []),
                "classifiers": info.get("classifiers", []),
                "keywords": info.get("keywords", ""),
                "project_urls": project_urls,
                "github_url": github_url,
                "home_page": info.get("home_page", ""),
                "package_url": info.get("package_url", ""),
                "release_url": info.get("release_url", ""),
                "docs_url": info.get("docs_url", ""),
                # Release metrics
                "total_releases": len(releases),
                "latest_release_date": (
                    latest_release.isoformat() if latest_release else None
                ),
                "days_since_last_release": days_since_last_release,
                "releases_last_year": recent_releases,
                # File metrics
                "has_wheel": any(
                    url.get("packagetype") == "bdist_wheel" for url in urls
                ),
                "has_source": any(url.get("packagetype") == "sdist" for url in urls),
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"PyPI API error: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_download_stats(self, package_name: str) -> Dict[str, Any]:
        """Fetch download statistics from pypistats.org"""
        try:
            response = self.session.get(
                self.pypistats_api_url.format(package=package_name), timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "downloads_last_day": (data.get("data", {}).get("last_day", 0)),
                    "downloads_last_week": (data.get("data", {}).get("last_week", 0)),
                    "downloads_last_month": (data.get("data", {}).get("last_month", 0)),
                }
            else:
                return {
                    "downloads_last_day": 0,
                    "downloads_last_week": 0,
                    "downloads_last_month": 0,
                    "note": "Download stats unavailable",
                }

        except Exception as e:
            return {
                "downloads_last_day": 0,
                "downloads_last_week": 0,
                "downloads_last_month": 0,
                "error": str(e),
            }

    def _get_github_stats(self, github_url: str) -> Dict[str, Any]:
        """Fetch repository statistics from GitHub"""
        try:
            # Parse owner and repo from URL
            # Expected format: https://github.com/owner/repo
            parts = github_url.rstrip("/").split("/")
            if len(parts) < 2:
                return {"status": "error", "error": "Invalid GitHub URL format"}

            repo_name = parts[-1]
            owner = parts[-2]

            # Remove .git suffix if present
            if repo_name.endswith(".git"):
                repo_name = repo_name[:-4]

            response = self.session.get(
                self.github_api_url.format(owner=owner, repo=repo_name), timeout=10
            )

            if response.status_code == 404:
                return {"status": "error", "error": "GitHub repository not found"}

            response.raise_for_status()
            data = response.json()

            # Calculate activity metrics
            pushed_at = data.get("pushed_at")
            days_since_last_push = None
            if pushed_at:
                try:
                    last_push = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
                    time_diff = datetime.now(last_push.tzinfo) - last_push
                    days_since_last_push = time_diff.days
                except (ValueError, AttributeError):
                    pass

            return {
                "stars": data.get("stargazers_count", 0),
                "watchers": data.get("subscribers_count", 0),
                "forks": data.get("forks_count", 0),
                "open_issues": data.get("open_issues_count", 0),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
                "pushed_at": pushed_at,
                "days_since_last_push": days_since_last_push,
                "default_branch": data.get("default_branch", "main"),
                "language": data.get("language"),
                "has_issues": data.get("has_issues", False),
                "has_wiki": data.get("has_wiki", False),
                "has_pages": data.get("has_pages", False),
                "archived": data.get("archived", False),
                "disabled": data.get("disabled", False),
                "license": (
                    data.get("license", {}).get("name") if data.get("license") else None
                ),
                "topics": data.get("topics", []),
                "description": data.get("description", ""),
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"GitHub API error: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _calculate_quality_scores(
        self, pypi_data: Dict, downloads: Dict, github_data: Dict
    ) -> Dict[str, Any]:
        """Calculate quality scores based on collected metrics"""

        scores = {
            "popularity_score": 0,
            "maintenance_score": 0,
            "documentation_score": 0,
            "compatibility_score": 0,
            "security_score": 0,
            "overall_score": 0,
        }

        # === POPULARITY SCORE ===
        popularity = 0

        # Downloads (40 points max)
        downloads_last_month = downloads.get("downloads_last_month", 0)
        if downloads_last_month > 1000000:
            popularity += 40
        elif downloads_last_month > 100000:
            popularity += 30
        elif downloads_last_month > 10000:
            popularity += 20
        elif downloads_last_month > 1000:
            popularity += 10
        elif downloads_last_month > 100:
            popularity += 5

        # GitHub stars (30 points max)
        stars = github_data.get("stars", 0)
        if stars > 10000:
            popularity += 30
        elif stars > 5000:
            popularity += 25
        elif stars > 1000:
            popularity += 20
        elif stars > 500:
            popularity += 15
        elif stars > 100:
            popularity += 10
        elif stars > 10:
            popularity += 5

        # Forks (15 points max)
        forks = github_data.get("forks", 0)
        if forks > 1000:
            popularity += 15
        elif forks > 500:
            popularity += 12
        elif forks > 100:
            popularity += 9
        elif forks > 50:
            popularity += 6
        elif forks > 10:
            popularity += 3

        # Total releases (15 points max)
        total_releases = pypi_data.get("total_releases", 0)
        if total_releases > 100:
            popularity += 15
        elif total_releases > 50:
            popularity += 12
        elif total_releases > 20:
            popularity += 9
        elif total_releases > 10:
            popularity += 6
        elif total_releases > 5:
            popularity += 3

        scores["popularity_score"] = min(popularity, 100)

        # === MAINTENANCE SCORE ===
        maintenance = 0

        # Recent release (40 points max)
        days_since_release = pypi_data.get("days_since_last_release")
        if days_since_release is not None:
            if days_since_release <= 30:
                maintenance += 40
            elif days_since_release <= 90:
                maintenance += 30
            elif days_since_release <= 180:
                maintenance += 20
            elif days_since_release <= 365:
                maintenance += 10
            elif days_since_release <= 730:
                maintenance += 5

        # Recent GitHub activity (30 points max)
        days_since_push = github_data.get("days_since_last_push")
        if days_since_push is not None:
            if days_since_push <= 7:
                maintenance += 30
            elif days_since_push <= 30:
                maintenance += 25
            elif days_since_push <= 90:
                maintenance += 20
            elif days_since_push <= 180:
                maintenance += 10
            elif days_since_push <= 365:
                maintenance += 5

        # Release frequency (30 points max)
        releases_last_year = pypi_data.get("releases_last_year", 0)
        if releases_last_year >= 12:
            maintenance += 30
        elif releases_last_year >= 6:
            maintenance += 25
        elif releases_last_year >= 4:
            maintenance += 20
        elif releases_last_year >= 2:
            maintenance += 15
        elif releases_last_year >= 1:
            maintenance += 10

        scores["maintenance_score"] = min(maintenance, 100)

        # === DOCUMENTATION SCORE ===
        documentation = 0

        # Has documentation URL (30 points)
        if pypi_data.get("project_urls", {}).get("Documentation") or pypi_data.get(
            "docs_url"
        ):
            documentation += 30

        # Description length (30 points)
        desc_length = pypi_data.get("description_length", 0)
        if desc_length > 5000:
            documentation += 30
        elif desc_length > 2000:
            documentation += 20
        elif desc_length > 500:
            documentation += 10
        elif desc_length > 100:
            documentation += 5

        # Has README/wiki (20 points)
        if github_data.get("has_wiki"):
            documentation += 10
        if github_data.get("has_pages"):
            documentation += 10

        # Keywords (10 points)
        if pypi_data.get("keywords"):
            documentation += 10

        # Classifiers (10 points)
        if len(pypi_data.get("classifiers", [])) > 5:
            documentation += 10
        elif len(pypi_data.get("classifiers", [])) > 0:
            documentation += 5

        scores["documentation_score"] = min(documentation, 100)

        # === COMPATIBILITY SCORE ===
        compatibility = 0

        # Has wheel distribution (40 points)
        if pypi_data.get("has_wheel"):
            compatibility += 40

        # Has source distribution (20 points)
        if pypi_data.get("has_source"):
            compatibility += 20

        # Python version support (40 points)
        requires_python = pypi_data.get("requires_python", "")
        if requires_python:
            compatibility += 20
            # Check for broad compatibility
            if "3.6" in requires_python or "3.7" in requires_python:
                compatibility += 20

        scores["compatibility_score"] = min(compatibility, 100)

        # === SECURITY SCORE ===
        security = 0

        # Has license (30 points)
        if pypi_data.get("license") or github_data.get("license"):
            security += 30

        # Not archived or disabled (30 points)
        if not github_data.get("archived", False) and not github_data.get(
            "disabled", False
        ):
            security += 30

        # Active issue management (20 points)
        open_issues = github_data.get("open_issues", 0)
        if github_data.get("has_issues"):
            if open_issues < 10:
                security += 20
            elif open_issues < 50:
                security += 15
            elif open_issues < 100:
                security += 10
            else:
                security += 5

        # Has maintainer (20 points)
        if pypi_data.get("maintainer") or pypi_data.get("author"):
            security += 20

        scores["security_score"] = min(security, 100)

        # === OVERALL SCORE ===
        # Weighted average
        scores["overall_score"] = int(
            scores["popularity_score"] * 0.25
            + scores["maintenance_score"] * 0.30
            + scores["documentation_score"] * 0.20
            + scores["compatibility_score"] * 0.15
            + scores["security_score"] * 0.10
        )

        return scores

    def _generate_recommendation(
        self, scores: Dict, pypi_data: Dict, github_data: Dict
    ) -> str:
        """Generate a human-readable recommendation based on scores"""
        overall = scores["overall_score"]

        if overall >= 80:
            recommendation = (
                "✅ HIGHLY RECOMMENDED - Excellent package with "
                "strong community support"
            )
        elif overall >= 60:
            recommendation = "👍 RECOMMENDED - Good package with acceptable quality"
        elif overall >= 40:
            recommendation = "⚠️ USE WITH CAUTION - Package has some concerns"
        else:
            recommendation = "❌ NOT RECOMMENDED - Consider alternatives"

        # Add specific concerns
        concerns = []
        if scores["maintenance_score"] < 40:
            concerns.append("Poor maintenance")
        if scores["popularity_score"] < 30:
            concerns.append("Low popularity")
        if scores["documentation_score"] < 40:
            concerns.append("Insufficient documentation")
        if github_data.get("archived"):
            concerns.append("Repository is archived")

        if concerns:
            recommendation += f" ({', '.join(concerns)})"

        return recommendation

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inspect a package and return comprehensive quality metrics

        Args:
            package_name: Name of the package to inspect
            include_github: Whether to fetch GitHub stats (default: True)
            include_downloads: Whether to fetch download stats (default: True)

        Returns:
            Dict with package metadata, statistics, and quality scores
        """
        try:
            package_name = arguments.get("package_name", "").strip()
            if not package_name:
                return {
                    "status": "error",
                    "data": {"error": "package_name is required"},
                }

            include_github = arguments.get("include_github", True)
            include_downloads = arguments.get("include_downloads", True)

            print(f"🔍 Inspecting package: {package_name}")

            # Step 1: Get PyPI metadata
            print("  📦 Fetching PyPI metadata...")
            pypi_data = self._get_pypi_metadata(package_name)

            if "error" in pypi_data:
                return {
                    "status": "error",
                    "data": {
                        "error": pypi_data["error"],
                        "package_name": package_name,
                    },
                }

            # Step 2: Get download statistics
            downloads = {}
            if include_downloads:
                print("  📊 Fetching download statistics...")
                downloads = self._get_download_stats(package_name)
                time.sleep(0.5)  # Rate limiting

            # Step 3: Get GitHub statistics
            github_data = {}
            if include_github and pypi_data.get("github_url"):
                print(
                    f"  🐙 Fetching GitHub statistics from {pypi_data['github_url']}..."
                )
                github_data = self._get_github_stats(pypi_data["github_url"])
                time.sleep(0.5)  # Rate limiting

            # Step 4: Calculate quality scores
            print("  🎯 Calculating quality scores...")
            scores = self._calculate_quality_scores(pypi_data, downloads, github_data)

            # Compile comprehensive report
            result = {
                "package_name": package_name,
                "pypi_metadata": pypi_data,
                "download_stats": downloads,
                "github_stats": github_data,
                "quality_scores": scores,
                "recommendation": self._generate_recommendation(
                    scores, pypi_data, github_data
                ),
            }

            print(
                f"✅ Inspection complete - Overall score: {scores['overall_score']}/100"
            )

            return {"status": "success", "data": result}

        except Exception as e:
            return {
                "status": "error",
                "data": {
                    "error": str(e),
                    "package_name": arguments.get("package_name", ""),
                },
            }
