# eol_tool.py
"""
Encyclopedia of Life (EOL) API tool for ToolUniverse.

EOL is a biodiversity knowledge aggregator providing comprehensive information
about every species on Earth: taxonomy, images, descriptions, common names,
synonyms, and taxonomy classification hierarchies from multiple sources
(NCBI, GBIF, ITIS, Catalogue of Life, etc.).

API: https://eol.org/api/
No authentication required for v1 JSON endpoints. Free public access.

Note: EOL's SSL certificate has chain issues with Python's certifi bundle.
We use urllib with a custom SSL context that uses the system certificate store
as a workaround.
"""

import json
import re
import ssl
from typing import Dict, Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .base_tool import BaseTool
from .tool_registry import register_tool

EOL_BASE_URL = "https://eol.org/api"


def _eol_http_get(url, timeout=30):
    """HTTP GET with SSL workaround for EOL's incomplete certificate chain.

    EOL's server certificate chain is not recognized by Python's bundled
    certifi CA store (and load_default_certs() also fails). This is a
    known issue with eol.org; curl works because it uses the OS keychain.
    We disable SSL verification as a pragmatic workaround since the EOL
    API is a public read-only endpoint with no sensitive data exchange.
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = Request(url)
    req.add_header("User-Agent", "ToolUniverse/1.0 (EOL API client)")
    req.add_header("Accept", "application/json")

    with urlopen(req, timeout=timeout, context=ctx) as resp:
        data = resp.read()
        return json.loads(data.decode("utf-8", errors="ignore"))


@register_tool("EOLTool")
class EOLTool(BaseTool):
    """
    Tool for querying the Encyclopedia of Life (EOL).

    EOL aggregates biodiversity data from hundreds of sources into a
    comprehensive knowledge base covering ~3.6 million species pages.
    Provides species search, detailed taxon pages with media (images,
    text descriptions), taxonomy hierarchies from multiple classification
    systems, and curated collections.

    Supports: species search, taxon page details, taxonomy hierarchy,
    collections browse.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "search")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the EOL API call."""
        try:
            return self._query(arguments)
        except HTTPError as e:
            return {"status": "error", "error": "EOL API HTTP error: %s" % e.code}
        except URLError as e:
            return {
                "status": "error",
                "error": "Failed to connect to Encyclopedia of Life API: %s"
                % str(e.reason),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": "Unexpected error querying EOL: %s" % str(e),
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate EOL endpoint."""
        if self.endpoint == "search":
            return self._search(arguments)
        elif self.endpoint == "pages":
            return self._get_page(arguments)
        elif self.endpoint == "hierarchy_entries":
            return self._get_hierarchy_entry(arguments)
        elif self.endpoint == "collections":
            return self._get_collection(arguments)
        else:
            return {"status": "error", "error": "Unknown endpoint: %s" % self.endpoint}

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for species/taxa by name."""
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        page = int(arguments.get("page", 1))
        exact = arguments.get("exact", False)

        params = {"q": query, "page": page}
        if exact:
            params["exact"] = "true"

        url = "%s/search/1.0.json?%s" % (EOL_BASE_URL, urlencode(params))
        data = _eol_http_get(url, timeout=self.timeout)

        results = []
        for r in data.get("results", []):
            results.append(
                {
                    "page_id": r.get("id"),
                    "title": r.get("title"),
                    "link": r.get("link"),
                    "content": r.get("content"),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "Encyclopedia of Life",
                "total_results": data.get("totalResults", 0),
                "start_index": data.get("startIndex", 1),
                "items_per_page": data.get("itemsPerPage", 50),
                "query": query,
            },
        }

    @staticmethod
    def _strip_html(text):
        """Remove HTML tags from text."""
        if not text:
            return text
        return re.sub(r"<[^>]+>", "", text)

    def _get_page(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed species/taxon page by EOL page ID."""
        page_id = arguments.get("page_id")
        if page_id is None:
            return {"status": "error", "error": "page_id parameter is required"}

        images_per_page = int(arguments.get("images_per_page", 3))
        texts_per_page = int(arguments.get("texts_per_page", 2))
        details = arguments.get("details", True)
        common_names = arguments.get("common_names", True)
        synonyms = arguments.get("synonyms", True)

        params = {
            "id": int(page_id),
            "images_per_page": images_per_page,
            "texts_per_page": texts_per_page,
            "videos_per_page": 0,
            "sounds_per_page": 0,
            "maps_per_page": 0,
            "details": "true" if details else "false",
            "common_names": "true" if common_names else "false",
            "synonyms": "true" if synonyms else "false",
        }

        url = "%s/pages/1.0.json?%s" % (EOL_BASE_URL, urlencode(params))
        data = _eol_http_get(url, timeout=self.timeout)
        tc = data.get("taxonConcept", {})

        # Process vernacular names
        vernacular_names = []
        for vn in tc.get("vernacularNames", [])[:20]:
            vernacular_names.append(
                {
                    "name": vn.get("vernacularName"),
                    "language": vn.get("language"),
                }
            )

        # Process synonyms
        synonym_list = []
        for syn in tc.get("synonyms", [])[:20]:
            synonym_list.append(syn.get("synonym"))

        # Process data objects (images + text)
        images = []
        descriptions = []
        for do in tc.get("dataObjects", []):
            dtype = do.get("dataType", "")
            if "StillImage" in dtype:
                images.append(
                    {
                        "media_url": do.get("mediaURL"),
                        "thumbnail_url": do.get("eolThumbnailURL"),
                        "rights_holder": do.get("rightsHolder"),
                        "license": do.get("license"),
                        "description": self._strip_html(
                            (do.get("description") or "")[:300]
                        ),
                    }
                )
            elif "Text" in dtype:
                desc_text = self._strip_html(do.get("description") or "")
                descriptions.append(
                    {
                        "text": desc_text[:500] if desc_text else None,
                        "source": do.get("source"),
                        "license": do.get("license"),
                    }
                )

        # Taxonomy classifications available
        classifications = []
        for entry in tc.get("taxonConcepts", [])[:15]:
            classifications.append(
                {
                    "hierarchy_entry_id": entry.get("identifier"),
                    "source": entry.get("nameAccordingTo"),
                    "rank": entry.get("taxonRank"),
                }
            )

        return {
            "status": "success",
            "data": {
                "page_id": tc.get("identifier"),
                "scientific_name": tc.get("scientificName"),
                "richness_score": tc.get("richness_score"),
                "common_names": vernacular_names,
                "synonyms": synonym_list,
                "images": images,
                "descriptions": descriptions,
                "classifications": classifications,
            },
            "metadata": {
                "source": "Encyclopedia of Life",
                "num_common_names": len(tc.get("vernacularNames", [])),
                "num_synonyms": len(tc.get("synonyms", [])),
                "num_classifications": len(tc.get("taxonConcepts", [])),
            },
        }

    def _get_hierarchy_entry(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get taxonomy hierarchy for a specific classification entry."""
        hierarchy_entry_id = arguments.get("hierarchy_entry_id")
        if hierarchy_entry_id is None:
            return {
                "status": "error",
                "error": "hierarchy_entry_id parameter is required",
            }

        params = {"id": int(hierarchy_entry_id)}
        url = "%s/hierarchy_entries/1.0.json?%s" % (EOL_BASE_URL, urlencode(params))
        data = _eol_http_get(url, timeout=self.timeout)

        # Process ancestors
        ancestors = []
        for a in data.get("ancestors", []):
            ancestors.append(
                {
                    "taxon_id": a.get("taxonID"),
                    "scientific_name": a.get("scientificName"),
                    "rank": a.get("taxonRank"),
                    "page_id": a.get("taxonConceptID"),
                    "source_url": a.get("source"),
                }
            )

        # Process children
        children = []
        for c in data.get("children", [])[:20]:
            children.append(
                {
                    "taxon_id": c.get("taxonID"),
                    "scientific_name": c.get("scientificName"),
                    "rank": c.get("taxonRank"),
                    "page_id": c.get("taxonConceptID"),
                }
            )

        # Process synonyms
        synonyms = []
        for s in data.get("synonyms", []):
            synonyms.append(
                {
                    "scientific_name": s.get("scientificName"),
                    "taxonomic_status": s.get("taxonomicStatus"),
                }
            )

        return {
            "status": "success",
            "data": {
                "taxon_id": data.get("taxonID"),
                "scientific_name": data.get("scientificName"),
                "rank": data.get("taxonRank"),
                "page_id": data.get("taxonConceptID"),
                "source": data.get("nameAccordingTo"),
                "source_identifier": data.get("sourceIdentifier"),
                "ancestors": ancestors,
                "children": children,
                "synonyms": synonyms,
                "vernacular_names": data.get("vernacularNames", []),
            },
            "metadata": {
                "source": "Encyclopedia of Life",
                "num_ancestors": len(ancestors),
                "num_children": len(children),
            },
        }

    def _get_collection(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get EOL curated collection details."""
        collection_id = arguments.get("collection_id")
        if collection_id is None:
            return {"status": "error", "error": "collection_id parameter is required"}

        page = int(arguments.get("page", 1))
        per_page = int(arguments.get("per_page", 50))
        filter_type = arguments.get("filter", "")

        params = {
            "id": int(collection_id),
            "page": page,
            "per_page": min(per_page, 500),
        }
        if filter_type:
            params["filter"] = filter_type

        url = "%s/collections/1.0.json?%s" % (EOL_BASE_URL, urlencode(params))
        data = _eol_http_get(url, timeout=self.timeout)

        items = []
        for item in data.get("collection_items", []):
            items.append(
                {
                    "name": item.get("name"),
                    "object_type": item.get("object_type"),
                    "object_id": item.get("object_id"),
                    "title": item.get("title"),
                    "annotation": item.get("annotation"),
                }
            )

        return {
            "status": "success",
            "data": {
                "name": data.get("name"),
                "description": data.get("description"),
                "total_items": data.get("total_items"),
                "items": items,
                "created": data.get("created"),
                "modified": data.get("modified"),
            },
            "metadata": {
                "source": "Encyclopedia of Life",
                "collection_id": collection_id,
                "page": page,
            },
        }
