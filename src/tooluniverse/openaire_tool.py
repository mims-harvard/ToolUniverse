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
        max_results = arguments.get("max_results", 10)
        page = arguments.get("page", 1)
        # This class backs both OpenAIRE_search_publications and
        # OpenAIRE_search_projects with the same "type" param. Read the
        # per-instance declared default instead of hardcoding
        # "publications" for all of them, or OpenAIRE_search_projects (whose
        # schema declares default "projects", enum locked to just that value)
        # silently searches publications whenever the caller omits `type`.
        declared_default = (
            self.tool_config.get("parameter", {})
            .get("properties", {})
            .get("type", {})
            .get("default", "publications")
        )
        prod_type = arguments.get("type", declared_default)
        if (
            isinstance(max_results, bool)
            or not isinstance(max_results, int)
            or not 1 <= max_results <= 1000
        ):
            return {
                "status": "success",
                "data": {
                    "status": "error",
                    "error": "max_results must be an integer between 1 and 1000",
                    "query": query or "",
                    "type": prod_type,
                    "total_results": 0,
                    "results": [],
                },
            }
        if isinstance(page, bool) or not isinstance(page, int) or page < 1:
            return {
                "status": "success",
                "data": {
                    "status": "error",
                    "error": "page must be a positive integer (1-based)",
                    "query": query or "",
                    "type": prod_type,
                    "total_results": 0,
                    "results": [],
                },
            }
        if page * max_results > 10_000:
            return {
                "status": "success",
                "data": {
                    "status": "error",
                    "error": "OpenAIRE requires page * max_results <= 10000",
                    "query": query or "",
                    "type": prod_type,
                    "total_results": 0,
                    "results": [],
                },
            }

        if not query:
            return {
                # Top-level error, so the result cache and every caller see a
                # failure; the old inner fields stay in `data` for callers that
                # read data["status"].
                "status": "error",
                "error": "`query` parameter is required.",
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
                # Top-level error, so the result cache and every caller see a
                # failure; the old inner fields stay in `data` for callers that
                # read data["status"].
                "status": "error",
                "error": "Unsupported type. Use publications/datasets/software.",
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
            "size": max_results,
            "page": page,
            "keywords": query,
        }
        try:
            resp = requests.get(endpoint, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            return {
                # Top-level error, so the result cache and every caller see a
                # failure; the old inner fields stay in `data` for callers that
                # read data["status"].
                "status": "error",
                "error": f"Network/API error calling OpenAIRE: {e}",
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
                # Top-level error, so the result cache and every caller see a
                # failure; the old inner fields stay in `data` for callers that
                # read data["status"].
                "status": "error",
                "error": "Failed to decode OpenAIRE response as JSON",
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

        header = data.get("response", {}).get("header", {})

        def _header_int(name, default):
            value = header.get(name, default)
            if isinstance(value, dict):
                value = value.get("$", default)
            try:
                return int(value)
            except (TypeError, ValueError):
                return default

        actual_size = _header_int("size", max_results)
        actual_page = _header_int("page", page)
        accessible_results = min(total_results, 10_000)
        page_end = (actual_page - 1) * actual_size + len(results)
        has_more = page_end < accessible_results
        result_data = {
            "status": "success",
            "query": query,
            "type": prod_type,
            "total_results": total_results,
            "total_results_is_exact": True,
            "accessible_results": accessible_results,
            "returned": len(results),
            "page": actual_page,
            "page_size": actual_size,
            "has_more": has_more,
            "next_page": actual_page + 1 if has_more else None,
            "upstream_truncated": total_results > accessible_results,
            "results": results,
        }
        if total_results > accessible_results:
            result_data["warning"] = (
                "OpenAIRE reports more than 10,000 matches, but its API only "
                "allows the first 10,000 results for a query."
            )
        return {"status": "success", "data": result_data}

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
        try:
            items = data.get("response", {}).get("results", {}).get("result", [])
        except Exception:
            items = []
        if isinstance(items, dict):
            items = [items]

        def _as_list(value):
            if value is None:
                return []
            return value if isinstance(value, list) else [value]

        def _result_url(result_obj):
            children = result_obj.get("children", {})
            if not isinstance(children, dict):
                return None
            instances = _as_list(children.get("instance"))
            for child in _as_list(children.get("result")):
                if isinstance(child, dict):
                    instances.extend(_as_list(child.get("instance")))
            for instance in instances:
                if not isinstance(instance, dict):
                    continue
                for field in ("fulltext", "url"):
                    candidate = self._scalar(instance.get(field))
                    if candidate:
                        return str(candidate).replace("&amp;", "&")
                for webresource in _as_list(instance.get("webresource")):
                    if not isinstance(webresource, dict):
                        continue
                    candidate = self._scalar(webresource.get("url"))
                    if candidate:
                        return str(candidate).replace("&amp;", "&")
            return None

        for item in items:
            if not isinstance(item, dict):
                continue
            metadata = item.get("metadata", {})
            if not isinstance(metadata, dict):
                metadata = {}
            entity = metadata.get("oaf:entity", {})
            result_obj = (
                entity.get("oaf:result", {}) if isinstance(entity, dict) else {}
            )
            # Retain compatibility with older OpenAIRE responses that placed
            # oaf:result directly below metadata.
            if not isinstance(result_obj, dict) or not result_obj:
                result_obj = metadata.get("oaf:result", {})
            if not isinstance(result_obj, dict):
                result_obj = {}

            title = self._scalar(result_obj.get("title"))
            authors = []
            for creator in _as_list(result_obj.get("creator")):
                name = self._scalar(creator)
                if name is not None and str(name) not in authors:
                    authors.append(str(name))

            date_obj = result_obj.get("dateofacceptance") or result_obj.get("date")
            if isinstance(date_obj, dict) and date_obj.get("year") is not None:
                date_value = self._scalar(date_obj.get("year"))
            else:
                date_value = self._scalar(date_obj)
            year = None
            if date_value is not None:
                year_text = str(date_value)
                year = int(year_text[:4]) if year_text[:4].isdigit() else date_value

            doi = None
            for pid in _as_list(result_obj.get("pid")):
                if isinstance(pid, dict) and pid.get("@classid") == "doi":
                    doi = self._scalar(pid)
                    if doi:
                        break

            url = _result_url(result_obj)
            if not url and doi:
                url = f"https://doi.org/{doi}"

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
