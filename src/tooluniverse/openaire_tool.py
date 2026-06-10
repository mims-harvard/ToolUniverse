import requests
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("OpenAIRETool")
class OpenAIRETool(BaseTool):
    """
    Search OpenAIRE Explore for research products (publications by default).

    Parameters (arguments):
        query (str): Query string
        max_results (int): Max number of results (default 10, max 100)
        type (str): product type filter: publications | datasets | software
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.base_url = "https://api.openaire.eu/search/publications"

    def run(self, arguments=None):
        arguments = arguments or {}
        query = arguments.get("query")
        max_results = int(arguments.get("max_results", 10))
        prod_type = arguments.get("type", "publications")

        if not query:
            return {
                "status": "success",
                "data": {
                    "status": "error",
                    "error": "`query` parameter is required.",
                    "query": "",
                    "type": prod_type,
                    "total_results": 0,
                    "results": [],
                },
            }

        endpoint = self._endpoint_for_type(prod_type)
        if endpoint is None:
            return {
                "status": "success",
                "data": {
                    "status": "error",
                    "error": "Unsupported type. Use publications/datasets/software.",
                    "query": query,
                    "type": prod_type,
                    "total_results": 0,
                    "results": [],
                },
            }

        # OpenAIRE's legacy `query` param now returns HTTP 400; the current
        # search API (publications, datasets, software, projects) uses
        # `keywords` for free-text search.
        params = {
            "format": "json",
            "size": max(1, min(max_results, 100)),
            "keywords": query,
        }
        try:
            resp = requests.get(endpoint, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            return {
                "status": "success",
                "data": {
                    "status": "error",
                    "error": "Network/API error calling OpenAIRE",
                    "reason": str(e),
                    "query": query,
                    "type": prod_type,
                    "total_results": 0,
                    "results": [],
                },
            }
        except ValueError:
            return {
                "status": "success",
                "data": {
                    "status": "error",
                    "error": "Failed to decode OpenAIRE response as JSON",
                    "query": query,
                    "type": prod_type,
                    "total_results": 0,
                    "results": [],
                },
            }

        if prod_type == "projects":
            results = self._normalize_projects(data)
        else:
            results = self._normalize(data, prod_type)

        # Total reported by OpenAIRE (across all pages), not just this page
        total_results = self._total_from_header(data)
        if total_results is None:
            total_results = len(results)

        return {
            "status": "success",
            "data": {
                "status": "success",
                "query": query,
                "type": prod_type,
                "total_results": total_results,
                "returned": len(results),
                "results": results,
            },
        }

    def _endpoint_for_type(self, prod_type):
        if prod_type == "publications":
            return "https://api.openaire.eu/search/publications"
        if prod_type == "datasets":
            return "https://api.openaire.eu/search/datasets"
        if prod_type == "software":
            return "https://api.openaire.eu/search/software"
        if prod_type == "projects":
            return "https://api.openaire.eu/search/projects"
        return None

    @staticmethod
    def _total_from_header(data):
        """Extract the total result count from the OpenAIRE response header."""
        try:
            total = data.get("response", {}).get("header", {}).get("total")
            if isinstance(total, dict):
                total = total.get("$")
            return int(total) if total is not None else None
        except (ValueError, TypeError, AttributeError):
            return None

    @staticmethod
    def _scalar(value):
        """OpenAIRE wraps scalars as {'$': value}; unwrap to the plain value."""
        if isinstance(value, dict):
            return value.get("$")
        if isinstance(value, list):
            for item in value:
                unwrapped = OpenAIRETool._scalar(item)
                if unwrapped is not None:
                    return unwrapped
            return None
        return value

    def _normalize_projects(self, data):
        """Normalize OpenAIRE funded-project / grant search results."""
        results = []
        try:
            items = data.get("response", {}).get("results", {}).get("result", [])
        except Exception:
            items = []
        if isinstance(items, dict):
            items = [items]

        for it in items:
            metadata = it.get("metadata", {}) if isinstance(it, dict) else {}
            project = metadata.get("oaf:entity", {}).get("oaf:project", {})
            if not isinstance(project, dict):
                continue

            # Funder + funding stream live in the fundingtree
            funding_tree = project.get("fundingtree", {})
            if isinstance(funding_tree, list):
                funding_tree = funding_tree[0] if funding_tree else {}
            funder = (
                funding_tree.get("funder", {}) if isinstance(funding_tree, dict) else {}
            )
            level0 = (
                funding_tree.get("funding_level_0", {})
                if isinstance(funding_tree, dict)
                else {}
            )

            results.append(
                {
                    "code": self._scalar(project.get("code")),
                    "acronym": self._scalar(project.get("acronym")),
                    "title": self._scalar(project.get("title")),
                    "funder": self._scalar(funder.get("name"))
                    if isinstance(funder, dict)
                    else None,
                    "funder_shortname": self._scalar(funder.get("shortname"))
                    if isinstance(funder, dict)
                    else None,
                    "funding_stream": self._scalar(level0.get("name"))
                    if isinstance(level0, dict)
                    else None,
                    "start_date": self._scalar(project.get("startdate")),
                    "end_date": self._scalar(project.get("enddate")),
                    "funded_amount": self._scalar(project.get("fundedamount")),
                    "total_cost": self._scalar(project.get("totalcost")),
                    "currency": self._scalar(project.get("currency")),
                    "website": self._scalar(project.get("websiteurl")),
                    "type": "projects",
                    "source": "OpenAIRE",
                }
            )

        return results

    def _normalize(self, data, prod_type):
        results = []
        # OpenAIRE JSON has a root 'response' with 'results' → 'result' list
        try:
            items = data.get("response", {}).get("results", {}).get("result", [])
        except Exception:
            items = []

        for it in items:
            # header may contain identifiers, not used presently
            _ = it.get("header", {}) if isinstance(it.get("header"), dict) else {}
            metadata = (
                it.get("metadata", {}) if isinstance(it.get("metadata"), dict) else {}
            )
            title = None
            authors = []
            year = None
            doi = None
            url = None

            # Titles can be nested in 'oaf:result' structure
            result_obj = metadata.get("oaf:result", {})
            if isinstance(result_obj, dict):
                t = result_obj.get("title")
                if isinstance(t, list) and t:
                    title = t[0].get("$")
                elif isinstance(t, dict):
                    title = t.get("$")

                # Authors
                creators = result_obj.get("creator", [])
                if isinstance(creators, list):
                    for c in creators:
                        name = c.get("$")
                        if name:
                            authors.append(name)

                # Year
                date_obj = result_obj.get("dateofacceptance") or result_obj.get("date")
                if isinstance(date_obj, dict):
                    year = date_obj.get("year") or date_obj.get("$")

                # DOI and URL
                pid = result_obj.get("pid", [])
                if isinstance(pid, list):
                    for p in pid:
                        if p.get("@classid") == "doi":
                            doi = p.get("$")
                bestaccessright = result_obj.get("bestaccessright", {})
                if isinstance(bestaccessright, dict):
                    url_value = bestaccessright.get("$")
                    if url_value:
                        url = url_value

            results.append(
                {
                    "title": title,
                    "authors": authors,
                    "year": year,
                    "doi": doi,
                    "url": url,
                    "type": prod_type,
                    "source": "OpenAIRE",
                }
            )

        return results
