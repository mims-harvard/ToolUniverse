# eol_tool.py
"""
Encyclopedia of Life (EOL) API tool for ToolUniverse.

EOL is a biodiversity knowledge aggregator providing comprehensive information
about every species on Earth: taxonomy, images, descriptions, common names,
synonyms, and taxonomy classification hierarchies from multiple sources
(NCBI, GBIF, ITIS, Catalogue of Life, etc.).

API: https://eol.org/api/
No authentication required for v1 JSON endpoints. Free public access.

TLS certificate and hostname verification are required for every request.
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
    """HTTP GET with standard certificate and hostname verification."""
    ctx = ssl.create_default_context()

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

    @staticmethod
    def _integer_control(arguments, name, default=None, minimum=0, maximum=None):
        value = arguments.get(name, default)
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < minimum
            or (maximum is not None and value > maximum)
        ):
            range_text = "%s or greater" % minimum
            if maximum is not None:
                range_text = "%s to %s" % (minimum, maximum)
            return {
                "status": "error",
                "error": "%s must be an integer from %s" % (name, range_text),
            }
        return value

    @staticmethod
    def _boolean_control(arguments, name, default):
        value = arguments.get(name, default)
        if not isinstance(value, bool):
            return {"status": "error", "error": "%s must be a boolean" % name}
        return value

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for species/taxa by name."""
        query = arguments.get("query", "")
        if not isinstance(query, str) or not query.strip():
            return {"status": "error", "error": "query must be a non-empty string"}
        query = query.strip()

        page = arguments.get("page", 1)
        exact = arguments.get("exact", False)
        if isinstance(page, bool) or not isinstance(page, int) or page < 1:
            return {"status": "error", "error": "page must be a positive integer"}
        if not isinstance(exact, bool):
            return {"status": "error", "error": "exact must be a boolean"}

        params = {"q": query, "page": page}
        if exact:
            params["exact"] = "true"

        url = "%s/search/1.0.json?%s" % (EOL_BASE_URL, urlencode(params))
        data = _eol_http_get(url, timeout=self.timeout)
        if not isinstance(data, dict):
            return {"status": "error", "error": "EOL search response was not an object"}
        raw_results = data.get("results")
        total = data.get("totalResults")
        start_index = data.get("startIndex")
        items_per_page = data.get("itemsPerPage")
        if (
            not isinstance(raw_results, list)
            or isinstance(total, bool)
            or not isinstance(total, int)
            or total < 0
            or isinstance(start_index, bool)
            or not isinstance(start_index, int)
            or start_index < 1
            or isinstance(items_per_page, bool)
            or not isinstance(items_per_page, int)
            or items_per_page < 1
        ):
            return {
                "status": "error",
                "error": "EOL search response lacked valid pagination metadata",
            }

        results = []
        for r in raw_results:
            if not isinstance(r, dict):
                return {
                    "status": "error",
                    "error": "EOL search response contained a malformed result",
                }
            results.append(
                {
                    "page_id": r.get("id"),
                    "title": r.get("title"),
                    "link": r.get("link"),
                    "content": r.get("content"),
                }
            )

        consumed = start_index - 1 + len(results)
        has_more = consumed < total
        stalled = has_more and not results
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "Encyclopedia of Life",
                "total_results": total,
                "start_index": start_index,
                "items_per_page": items_per_page,
                "page": page,
                "returned": len(results),
                "has_more": has_more,
                "next_page": page + 1 if has_more and not stalled else None,
                "result_set_complete": start_index == 1 and not has_more,
                "requested_page_complete": not stalled,
                "pagination_stalled": stalled,
                "exact": exact,
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
        controls = {
            "page_id": self._integer_control(arguments, "page_id", minimum=1),
            "images_per_page": self._integer_control(
                arguments, "images_per_page", 3, 0, 75
            ),
            "texts_per_page": self._integer_control(
                arguments, "texts_per_page", 2, 0, 75
            ),
            "common_name_limit": self._integer_control(
                arguments, "common_name_limit", 20, 1, 1000
            ),
            "common_name_offset": self._integer_control(
                arguments, "common_name_offset", 0, 0
            ),
            "synonym_limit": self._integer_control(
                arguments, "synonym_limit", 20, 1, 1000
            ),
            "synonym_offset": self._integer_control(arguments, "synonym_offset", 0, 0),
            "classification_limit": self._integer_control(
                arguments, "classification_limit", 15, 1, 1000
            ),
            "classification_offset": self._integer_control(
                arguments, "classification_offset", 0, 0
            ),
            "details": self._boolean_control(arguments, "details", True),
            "common_names": self._boolean_control(arguments, "common_names", True),
            "synonyms": self._boolean_control(arguments, "synonyms", True),
        }
        for value in controls.values():
            if isinstance(value, dict):
                return value
        page_id = controls["page_id"]
        images_per_page = controls["images_per_page"]
        texts_per_page = controls["texts_per_page"]
        details = controls["details"]
        common_names = controls["common_names"]
        synonyms = controls["synonyms"]
        common_name_limit = controls["common_name_limit"]
        common_name_offset = controls["common_name_offset"]
        synonym_limit = controls["synonym_limit"]
        synonym_offset = controls["synonym_offset"]
        classification_limit = controls["classification_limit"]
        classification_offset = controls["classification_offset"]

        params = {
            "id": page_id,
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
        all_common_names = tc.get("vernacularNames", [])
        common_name_page = all_common_names[
            common_name_offset : common_name_offset + common_name_limit
        ]
        for vn in common_name_page:
            vernacular_names.append(
                {
                    "name": vn.get("vernacularName"),
                    "language": vn.get("language"),
                }
            )

        # Process synonyms
        synonym_list = []
        all_synonyms = tc.get("synonyms", [])
        synonym_page = all_synonyms[synonym_offset : synonym_offset + synonym_limit]
        for syn in synonym_page:
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
                        "description": self._strip_html(do.get("description") or ""),
                    }
                )
            elif "Text" in dtype:
                desc_text = self._strip_html(do.get("description") or "")
                descriptions.append(
                    {
                        "text": desc_text if desc_text else None,
                        "source": do.get("source"),
                        "license": do.get("license"),
                    }
                )

        # Taxonomy classifications available
        classifications = []
        all_classifications = tc.get("taxonConcepts", [])
        classification_page = all_classifications[
            classification_offset : classification_offset + classification_limit
        ]
        for entry in classification_page:
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
                "num_common_names": len(all_common_names),
                "common_names_returned": len(vernacular_names),
                "common_name_limit": common_name_limit,
                "common_name_offset": common_name_offset,
                "common_names_truncated": len(vernacular_names) < len(all_common_names),
                "next_common_name_offset": (
                    common_name_offset + len(vernacular_names)
                    if common_name_offset + len(vernacular_names)
                    < len(all_common_names)
                    else None
                ),
                "num_synonyms": len(all_synonyms),
                "synonyms_returned": len(synonym_list),
                "synonym_limit": synonym_limit,
                "synonym_offset": synonym_offset,
                "synonyms_truncated": len(synonym_list) < len(all_synonyms),
                "next_synonym_offset": (
                    synonym_offset + len(synonym_list)
                    if synonym_offset + len(synonym_list) < len(all_synonyms)
                    else None
                ),
                "num_classifications": len(all_classifications),
                "classifications_returned": len(classifications),
                "classification_limit": classification_limit,
                "classification_offset": classification_offset,
                "classifications_truncated": len(classifications)
                < len(all_classifications),
                "next_classification_offset": (
                    classification_offset + len(classifications)
                    if classification_offset + len(classifications)
                    < len(all_classifications)
                    else None
                ),
            },
        }

    def _get_hierarchy_entry(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get taxonomy hierarchy for a specific classification entry."""
        hierarchy_entry_id = self._integer_control(
            arguments, "hierarchy_entry_id", minimum=1
        )
        child_limit = self._integer_control(arguments, "child_limit", 20, 1, 1000)
        child_offset = self._integer_control(arguments, "child_offset", 0, 0)
        for value in (hierarchy_entry_id, child_limit, child_offset):
            if isinstance(value, dict):
                return value

        params = {"id": hierarchy_entry_id}
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
        all_children = data.get("children", [])
        child_page = all_children[child_offset : child_offset + child_limit]
        for c in child_page:
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
                "num_children": len(all_children),
                "children_returned": len(children),
                "child_limit": child_limit,
                "child_offset": child_offset,
                "children_truncated": child_offset + len(children) < len(all_children),
                "next_child_offset": (
                    child_offset + len(children)
                    if child_offset + len(children) < len(all_children)
                    else None
                ),
            },
        }

    def _get_collection(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get EOL curated collection details."""
        collection_id = self._integer_control(arguments, "collection_id", minimum=1)
        page = self._integer_control(arguments, "page", 1, 1)
        per_page = self._integer_control(arguments, "per_page", 50, 1, 500)
        for value in (collection_id, page, per_page):
            if isinstance(value, dict):
                return value
        filter_type = arguments.get("filter", "")
        allowed_filters = {
            "",
            "taxa",
            "text",
            "image",
            "sound",
            "video",
            "collection",
            "community",
            "user",
        }
        if not isinstance(filter_type, str) or filter_type not in allowed_filters:
            return {
                "status": "error",
                "error": "filter is not a supported EOL object type",
            }

        params = {
            "id": collection_id,
            "page": page,
            "per_page": per_page,
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
