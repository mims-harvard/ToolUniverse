import requests
from typing import Any, Dict, Optional
from .base_tool import BaseTool
from .http_utils import request_with_retry
from .tool_registry import register_tool


@register_tool("OpenAlexTool")
class OpenAlexTool(BaseTool):
    """
    Tool to retrieve literature from OpenAlex based on search keywords.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.base_url = "https://api.openalex.org/works"

    def run(self, arguments):
        """Main entry point for the tool."""
        # Backwards/UX compatibility: accept common aliases.
        search_keywords = arguments.get("search_keywords") or arguments.get("query")
        if not search_keywords or not str(search_keywords).strip():
            return {
                "status": "error",
                "error": "`search_keywords` (or `query`) parameter is required and must be non-empty.",
            }
        max_results = arguments.get("max_results", arguments.get("limit", 10))
        year_from = arguments.get("year_from", None)
        year_to = arguments.get("year_to", None)
        open_access = arguments.get("open_access", None)
        require_has_fulltext = bool(arguments.get("require_has_fulltext", False))
        fulltext_terms = arguments.get("fulltext_terms")

        return self.search_literature(
            search_keywords,
            max_results,
            year_from,
            year_to,
            open_access,
            require_has_fulltext=require_has_fulltext,
            fulltext_terms=fulltext_terms,
        )

    def search_literature(
        self,
        search_keywords,
        max_results=10,
        year_from=None,
        year_to=None,
        open_access=None,
        *,
        require_has_fulltext: bool = False,
        fulltext_terms: Optional[list[str]] = None,
    ):
        """
        Search for literature using OpenAlex API.

        Parameters
            search_keywords (str): Keywords to search for in title, abstract, and content.
            max_results (int): Maximum number of results to return (default: 10).
            year_from (int): Start year for publication date filter (optional).
            year_to (int): End year for publication date filter (optional).
            open_access (bool): Filter for open access papers only (optional).

        Returns
            list: List of dictionaries containing paper information.
        """
        # Build query parameters
        params = {
            "search": search_keywords,
            "per-page": min(max_results, 200),  # OpenAlex allows max 200 per page
            "mailto": "support@openalex.org",  # Polite pool access
        }

        # Don't force a sort by citations: for discovery searches it can hide newer,
        # lower-cited but highly relevant works. OpenAlex's default ordering is
        # generally better for keyword search.

        # Add year filters if provided
        filters = []
        if year_from is not None and year_to is not None:
            filters.append(f"publication_year:{year_from}-{year_to}")
        elif year_from is not None:
            filters.append(f"from_publication_date:{year_from}-01-01")
        elif year_to is not None:
            filters.append(f"to_publication_date:{year_to}-12-31")

        # Add open access filter if specified
        if open_access is True:
            filters.append("is_oa:true")
        elif open_access is False:
            filters.append("is_oa:false")

        valid_ft_terms: list[str] = []
        if isinstance(fulltext_terms, list):
            valid_ft_terms = [
                t.strip().replace(",", " ")
                for t in fulltext_terms
                if isinstance(t, str) and t.strip()
            ]
        if valid_ft_terms:
            require_has_fulltext = True
            filters.extend([f"fulltext.search:{t}" for t in valid_ft_terms])

        if require_has_fulltext:
            filters.append("has_fulltext:true")

        if filters:
            params["filter"] = ",".join(filters)

        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()

            papers = []
            for work in data.get("results", []):
                try:
                    paper_info = self._extract_paper_info(work)
                    papers.append(paper_info)
                except Exception:
                    # Skip papers with missing data rather than failing completely
                    continue

            print(
                f"[OpenAlex] Retrieved {len(papers)} papers for keywords: '{search_keywords}'"
            )
            return papers

        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"Error retrieving data from OpenAlex: {e}",
            }

    def _extract_paper_info(self, work):
        """
        Extract relevant information from a work object returned by OpenAlex API.

        Parameters
            work (dict): Work object from OpenAlex API response.

        Returns
            dict: Formatted paper information.
        """
        # Extract title
        title = work.get("title", "No title available")

        # Extract abstract (display_name from abstract_inverted_index if available)
        abstract = None
        if work.get("abstract_inverted_index"):
            # Reconstruct abstract from inverted index
            abstract_dict = work["abstract_inverted_index"]
            abstract_words = [""] * 500  # Assume max 500 words
            for word, positions in abstract_dict.items():
                for pos in positions:
                    if pos < len(abstract_words):
                        abstract_words[pos] = word
            abstract = " ".join([word for word in abstract_words if word]).strip()

        if not abstract:
            abstract = "Abstract not available"

        # Extract authors
        authors = []
        for authorship in work.get("authorships", []):
            author = authorship.get("author", {})
            author_name = author.get("display_name", "Unknown Author")
            authors.append(author_name)

        # Extract publication year
        publication_year = work.get("publication_year", "Year not available")

        # Extract organizations/affiliations
        organizations = set()
        for authorship in work.get("authorships", []):
            for institution in authorship.get("institutions", []):
                org_name = institution.get("display_name")
                if org_name:
                    organizations.add(org_name)

        # Extract additional useful information
        primary_location = work.get("primary_location") or {}
        source = primary_location.get("source") or {}
        venue = source.get("display_name", "Unknown venue")
        doi = work.get("doi", "No DOI")
        citation_count = work.get("cited_by_count", 0)
        open_access_info = work.get("open_access") or {}
        open_access = open_access_info.get("is_oa", False)
        pdf_url = open_access_info.get("oa_url")
        has_fulltext = bool(work.get("has_fulltext", False))
        content_urls = work.get("content_urls")

        # Extract keywords/concepts
        keywords = []
        concepts = work.get("concepts", [])
        if isinstance(concepts, list):
            for concept in concepts:
                if isinstance(concept, dict):
                    concept_name = concept.get("display_name", "")
                    if concept_name:
                        keywords.append(concept_name)

        # Extract article type
        article_type = work.get("type", "Unknown")

        # Extract publisher
        primary_location = work.get("primary_location") or {}
        source = primary_location.get("source") or {}
        publisher = source.get("publisher", "Unknown")

        return {
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "year": publication_year,
            "organizations": list(organizations),
            "venue": venue,
            "doi": doi,
            "citation_count": citation_count,
            "open_access": open_access,
            "pdf_url": pdf_url,
            "has_fulltext": has_fulltext,
            "content_urls": content_urls,
            "keywords": keywords if keywords else "Keywords not available",
            "article_type": article_type,
            "publisher": publisher,
            "openalex_id": work.get("id", ""),
            "url": work.get("doi") if work.get("doi") else work.get("id", ""),
            "data_quality": {
                "has_abstract": bool(abstract and abstract != "Abstract not available"),
                "has_authors": bool(authors),
                "has_venue": bool(venue and venue != "Unknown venue"),
                "has_year": bool(
                    publication_year and publication_year != "Year not available"
                ),
                "has_doi": bool(doi and doi != "No DOI"),
                "has_citation_count": bool(citation_count and citation_count > 0),
                "has_keywords": bool(keywords),
            },
        }

    def get_paper_by_doi(self, doi):
        """
        Retrieve a specific paper by its DOI.

        Parameters
            doi (str): DOI of the paper to retrieve.

        Returns
            dict: Paper information or None if not found.
        """
        try:
            # OpenAlex supports DOI lookup directly
            url = f"https://api.openalex.org/works/https://doi.org/{doi}"
            params = {"mailto": "support@openalex.org"}

            response = requests.get(url, params=params)
            response.raise_for_status()
            work = response.json()

            return self._extract_paper_info(work)

        except requests.exceptions.RequestException as e:
            print(f"Error retrieving paper by DOI {doi}: {e}")
            return None

    def get_papers_by_author(self, author_name, max_results=10):
        """
        Retrieve papers by a specific author.

        Parameters
            author_name (str): Name of the author to search for.
            max_results (int): Maximum number of results to return.

        Returns
            list: List of papers by the author.
        """
        try:
            params = {
                "filter": f"author.display_name.search:{author_name}",
                "per-page": min(max_results, 200),
                "sort": "cited_by_count:desc",
                "mailto": "support@openalex.org",
            }

            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()

            papers = []
            for work in data.get("results", []):
                paper_info = self._extract_paper_info(work)
                papers.append(paper_info)

            print(
                f"[OpenAlex] Retrieved {len(papers)} papers by author: '{author_name}'"
            )
            return papers

        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"Error retrieving papers by author {author_name}: {e}",
            }


@register_tool("OpenAlexRESTTool")
class OpenAlexRESTTool(BaseTool):
    """
    Generic JSON-config driven OpenAlex REST tool.

    Notes:
    - OpenAlex strongly encourages providing a contact email via the `mailto` query param.
    - This tool returns a consistent wrapper: {status, data, url} (plus error fields on failure).
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.base_url = "https://api.openalex.org"
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self.timeout = 30

    @staticmethod
    def _normalize_openalex_id(value: Any) -> Any:
        if isinstance(value, str) and "openalex.org/" in value:
            return value.rstrip("/").split("/")[-1]
        return value

    @staticmethod
    def _normalize_doi(value: Any) -> Any:
        if not isinstance(value, str):
            return value
        v = value.strip()
        if "doi.org/" in v:
            return v.split("doi.org/")[-1]
        if v.lower().startswith("doi:"):
            return v[4:]
        return v

    def _build_url_and_params(
        self, arguments: Dict[str, Any]
    ) -> tuple[str, Dict[str, Any]]:
        # Backwards/UX compatibility: accept common aliases.
        arguments = dict(arguments or {})
        if "search" not in arguments and isinstance(arguments.get("query"), str):
            arguments["search"] = arguments.get("query")
        if "per_page" not in arguments and isinstance(arguments.get("limit"), int):
            arguments["per_page"] = arguments.get("limit")
        # Prevent alias keys from being forwarded to OpenAlex as raw query params
        # (OpenAlex rejects unknown params like `query`/`limit` with HTTP 400).
        arguments.pop("query", None)
        arguments.pop("limit", None)

        # Reject empty-string search to avoid querying the entire OpenAlex corpus.
        if "search" in arguments and not str(arguments["search"]).strip():
            # If no filter is provided either, an empty search would return
            # arbitrary results from the entire corpus -- return an error instead.
            has_filter = bool(
                arguments.get("filter")
                or arguments.get("require_has_fulltext")
                or arguments.get("fulltext_terms")
            )
            if not has_filter:
                raise ValueError(
                    "`search` (or `query`) parameter is required and must be non-empty "
                    "unless a `filter` is also provided."
                )
            arguments.pop("search", None)

        fields = self.tool_config.get("fields", {}) or {}
        path_tmpl = fields.get("path", "")
        if not path_tmpl:
            raise ValueError("OpenAlexRESTTool requires fields.path in tool config")

        # Replace placeholders in the path.
        path = path_tmpl
        for k, v in (arguments or {}).items():
            if v is None:
                continue
            if k == "doi":
                v = self._normalize_doi(v)
            elif k.endswith("_id") or k in {
                "openalex_id",
                "author_id",
                "institution_id",
                "concept_id",
                "work_id",
            }:
                v = self._normalize_openalex_id(v)
            path = path.replace(f"{{{k}}}", str(v))

        url = f"{self.base_url}{path}"

        # Build query params (optional).
        params: Dict[str, Any] = {}
        default_params = fields.get("default_params")
        if isinstance(default_params, dict):
            params.update(default_params)

        param_map = (
            fields.get("param_map") if isinstance(fields.get("param_map"), dict) else {}
        )
        path_params = set(fields.get("path_params") or [])
        custom_keys = {"require_has_fulltext", "fulltext_terms"}

        for k, v in (arguments or {}).items():
            if v is None or k in path_params or k in custom_keys:
                continue
            api_key = param_map.get(k, k)
            params[api_key] = v

        require_has_fulltext = bool(arguments.get("require_has_fulltext", False))
        fulltext_terms = arguments.get("fulltext_terms")
        valid_ft_terms: list[str] = []
        if isinstance(fulltext_terms, list):
            valid_ft_terms = [
                t.strip().replace(",", " ")
                for t in fulltext_terms
                if isinstance(t, str) and t.strip()
            ]
        filter_additions: list[str] = []
        if valid_ft_terms:
            require_has_fulltext = True
            filter_additions.extend([f"fulltext.search:{t}" for t in valid_ft_terms])
        if require_has_fulltext:
            filter_additions.append("has_fulltext:true")
        if filter_additions:
            existing = params.get("filter")
            if isinstance(existing, str) and existing.strip():
                params["filter"] = ",".join(
                    [existing.strip().strip(","), *filter_additions]
                )
            else:
                params["filter"] = ",".join(filter_additions)

        # Provide a default mailto unless user overrides.
        if "mailto" not in params:
            params["mailto"] = "support@openalex.org"

        return url, params

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        url: Optional[str] = None
        try:
            url, params = self._build_url_and_params(arguments or {})
            resp = request_with_retry(
                self.session,
                "GET",
                url,
                params=params,
                timeout=self.timeout,
                max_attempts=3,
            )
            final_url = getattr(resp, "url", None) or url

            if resp.status_code != 200:
                return {
                    "status": "error",
                    "error": "OpenAlex API error",
                    "url": final_url,
                    "status_code": resp.status_code,
                    "detail": (resp.text or "")[:500],
                }

            return {"status": "success", "data": resp.json(), "url": final_url}
        except Exception as e:
            return {
                "status": "error",
                "error": f"OpenAlex API error: {str(e)}",
                "url": url,
            }
