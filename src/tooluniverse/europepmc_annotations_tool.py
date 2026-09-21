# europepmc_annotations_tool.py
"""
Europe PMC Annotations API tool for ToolUniverse.

Provides access to text-mined annotations from scientific articles using
Europe PMC's SciLite text mining pipeline. Extracts structured entities
including chemicals, organisms, gene ontology terms, diseases, and
gene/protein mentions from published literature.

API: https://www.ebi.ac.uk/europepmc/annotations_api/
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

EUROPEPMC_ANNOTATIONS_URL = "https://www.ebi.ac.uk/europepmc/annotations_api"

# annotationsByArticleIds returns every annotation for an article, so responses
# are capped here to keep them usable.
DEFAULT_ANNOTATION_CAP = 100

# Single-article responses are not caller-capped; this bounds them instead.
ARTICLE_ANNOTATION_CAP = 200


@register_tool("EuroPMCAnnotationsTool")
class EuroPMCAnnotationsTool(BaseTool):
    """
    Tool for extracting text-mined annotations from scientific articles
    via the Europe PMC Annotations API.

    Supports annotation types: Chemicals, Organisms, Gene Ontology,
    Diseases, Genes & Proteins, Accession Numbers.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "by_article"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Europe PMC Annotations API call."""
        try:
            return self._dispatch(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Europe PMC Annotations API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to Europe PMC Annotations API",
            }
        except requests.exceptions.HTTPError as e:
            # requests.Response is falsy for any 4xx/5xx, so `if e.response`
            # discards exactly the responses carrying the explanation.
            response = e.response
            if response is None:
                return {
                    "status": "error",
                    "error": "Europe PMC Annotations API HTTP error: no response",
                }
            detail = ""
            try:
                detail = (response.json() or {}).get("message", "")
            except ValueError:
                detail = response.text.strip()[:200]
            suffix = f": {detail}" if detail else ""
            return {
                "status": "error",
                "error": (
                    f"Europe PMC Annotations API HTTP error "
                    f"{response.status_code}{suffix}"
                ),
            }
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _dispatch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint_type == "by_article":
            return self._by_article(arguments)
        elif self.endpoint_type == "batch_by_type":
            return self._batch_by_type(arguments)
        elif self.endpoint_type == "chemicals_shortcut":
            return self._chemicals_shortcut(arguments)
        return {
            "status": "error",
            "error": f"Unknown endpoint_type: {self.endpoint_type}",
        }

    def _fetch_annotations(self, article_ids: str, annotation_type: str = None):
        """Fetch annotations from the API.

        annotationsByArticleIds has no pagination: it returns every annotation
        for the requested articles regardless of any pageSize argument, so the
        caller caps the response instead.
        """
        url = f"{EUROPEPMC_ANNOTATIONS_URL}/annotationsByArticleIds"
        params = {
            "articleIds": article_ids,
            "format": "JSON",
        }
        if annotation_type:
            params["type"] = annotation_type

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _annotation_cap(page_size: Any) -> int:
        """Resolve the per-article annotation cap, defaulting to 100.

        A non-positive cap would return an empty list beside a non-zero
        total_annotations, which reads as "this article has none". The schema
        rejects those, and anything that reaches here anyway falls back to the
        default rather than silently emptying the response.
        """
        if page_size is None:
            return DEFAULT_ANNOTATION_CAP
        try:
            cap = int(page_size)
        except (TypeError, ValueError):
            return DEFAULT_ANNOTATION_CAP
        return cap if cap > 0 else DEFAULT_ANNOTATION_CAP

    @staticmethod
    def _unmatched_ids(requested, raw):
        """Requested identifiers with no article in the response.

        A request for PMC:PMC4353746 comes back keyed MED:25780448 with the
        PMCID alongside, so matching is on either external id.
        """
        seen = set()
        for article in raw:
            source = str(article.get("source") or "").upper()
            ext = str(article.get("extId") or "").upper()
            pmcid = str(article.get("pmcid") or "").upper()
            if ext:
                seen.add(ext)
                if source:
                    seen.add(f"{source}:{ext}")
            if pmcid:
                seen.add(pmcid)
        missing = []
        for rid in requested:
            upper = rid.upper()
            _, _, ext = upper.partition(":")
            if upper not in seen and ext not in seen:
                missing.append(rid)
        return missing

    @staticmethod
    def _normalize_article_id(article_id: str) -> str:
        """Normalize bare PMC/PMID to API format: PMC:PMC4353746 or MED:25780448."""
        aid = article_id.strip()
        upper = aid.upper()
        if upper.startswith(("PMC:", "MED:")):
            _, rest = aid.split(":", 1)
            rest = rest.strip()
            if not rest:
                return ""
            if upper.startswith("PMC:"):
                if rest.upper().startswith("PMC"):
                    rest = rest[3:]
                if not rest:
                    return ""
                return f"PMC:PMC{rest}"
            return f"MED:{rest}"
        if upper.startswith("PMC"):
            num = aid[3:]
            return f"PMC:PMC{num}" if num else ""
        if aid.isdigit():
            return f"MED:{aid}"
        return aid

    def _by_article(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get annotations from a single article."""
        raw_id = (
            arguments.get("article_id")
            or arguments.get("pmcid")
            or arguments.get("pmid")
            or ""
        )
        article_id = self._normalize_article_id(str(raw_id).strip()) if raw_id else ""
        annotation_type = arguments.get("annotation_type") or arguments.get(
            "entity_type"
        )

        if not article_id:
            return {
                "status": "error",
                "error": "article_id is required. Accepts: 'PMC:PMC4353746', bare 'PMC4353746', or PMID '25780448'.",
            }

        raw = self._fetch_annotations(article_id, annotation_type)

        if not isinstance(raw, list) or len(raw) == 0:
            return {
                "status": "success",
                "data": {
                    "article_id": article_id,
                    "pmcid": None,
                    "source": None,
                    "annotation_count": 0,
                    "annotations": [],
                },
                "metadata": {
                    "source": "Europe PMC Annotations API",
                    "endpoint": "annotationsByArticleIds",
                },
            }

        article = raw[0]
        annotations_raw = article.get("annotations", [])

        annotations = []
        for ann in annotations_raw:
            tags = []
            for tag in ann.get("tags", []):
                tags.append(
                    {
                        "name": tag.get("name", ""),
                        "uri": tag.get("uri", ""),
                    }
                )
            annotations.append(
                {
                    "exact": ann.get("exact", ""),
                    "prefix": ann.get("prefix"),
                    "postfix": ann.get("postfix"),
                    "type": ann.get("type", ""),
                    "section": ann.get("section"),
                    "provider": ann.get("provider"),
                    "tags": tags,
                }
            )

        return {
            "status": "success",
            "data": {
                "article_id": article_id,
                "pmcid": article.get("pmcid"),
                "source": article.get("source"),
                "annotation_count": len(annotations[:ARTICLE_ANNOTATION_CAP]),
                "total_annotations": len(annotations),
                "annotations": annotations[:ARTICLE_ANNOTATION_CAP],
            },
            "metadata": {
                "source": "Europe PMC Annotations API",
                "endpoint": "annotationsByArticleIds",
            },
        }

    def _batch_by_type(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get annotations of a specific type from multiple articles."""
        raw_ids = arguments.get("article_ids", "")
        annotation_type = arguments.get("annotation_type", "")
        page_size = self._annotation_cap(arguments.get("page_size"))

        if not str(raw_ids).strip():
            return {
                "status": "error",
                "error": "article_ids is required (e.g., 'PMC:PMC4353746,PMC:PMC3531190')",
            }

        # The single-article tools accept bare 'PMC4353746' and raw PMIDs, and
        # say so in their errors; the batch path used to send them unchanged and
        # get a 400 back.
        requested = [
            self._normalize_article_id(part)
            for part in str(raw_ids).split(",")
            if part.strip()
        ]
        requested = [rid for rid in requested if rid]
        if not requested:
            return {
                "status": "error",
                "error": "article_ids contained no usable identifiers (e.g., 'PMC:PMC4353746').",
            }
        article_ids = ",".join(requested)
        if not annotation_type:
            return {
                "status": "error",
                "error": "annotation_type is required (e.g., 'Chemicals')",
            }

        raw = self._fetch_annotations(article_ids, annotation_type)

        if not isinstance(raw, list):
            raw = []

        total_annotations = 0
        articles = []
        for article in raw:
            annotations_raw = article.get("annotations", [])
            total_annotations += len(annotations_raw)

            annotations = []
            for ann in annotations_raw:
                annotations.append(
                    {
                        "exact": ann.get("exact", ""),
                        "type": ann.get("type", ""),
                        "tags": ann.get("tags", []),
                    }
                )

            returned = annotations[:page_size]
            articles.append(
                {
                    "article_id": f"{article.get('source', '')}:{article.get('extId', '')}",
                    "pmcid": article.get("pmcid"),
                    # annotation_count is what the caller receives and
                    # total_annotations what exists, so a capped article says
                    # so itself instead of leaving the shortfall to be inferred
                    # from a batch-wide sum.
                    "annotation_count": len(returned),
                    "total_annotations": len(annotations),
                    "annotations": returned,
                }
            )

        return {
            "status": "success",
            "data": {
                "article_count": len(articles),
                "annotation_type": annotation_type,
                "total_annotations": total_annotations,
                # Europe PMC omits unknown identifiers rather than reporting
                # them, so a typo in a 200-id list would vanish silently.
                "not_found": self._unmatched_ids(requested, raw),
                "articles": articles,
            },
            "metadata": {
                "source": "Europe PMC Annotations API",
                "endpoint": "annotationsByArticleIds",
            },
        }

    def _chemicals_shortcut(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Extract chemical mentions from an article."""
        raw_id = (
            arguments.get("article_id")
            or arguments.get("pmcid")
            or arguments.get("pmid")
            or ""
        )
        article_id = self._normalize_article_id(str(raw_id).strip()) if raw_id else ""

        if not article_id:
            return {
                "status": "error",
                "error": "article_id is required. Accepts: 'PMC:PMC4353746', bare 'PMC4353746', or PMID '25780448'.",
            }

        raw = self._fetch_annotations(article_id, "Chemicals")

        if not isinstance(raw, list) or len(raw) == 0:
            return {
                "status": "success",
                "data": {
                    "article_id": article_id,
                    "chemical_count": 0,
                    "chemicals": [],
                },
                "metadata": {
                    "source": "Europe PMC Annotations API",
                    "endpoint": "annotationsByArticleIds?type=Chemicals",
                },
            }

        article = raw[0]
        annotations_raw = article.get("annotations", [])

        chemicals = []
        for ann in annotations_raw:
            tags = ann.get("tags", [])
            chebi_uri = None
            chebi_name = None
            if tags:
                chebi_uri = tags[0].get("uri")
                chebi_name = tags[0].get("name")

            context = ""
            prefix = ann.get("prefix", "") or ""
            postfix = ann.get("postfix", "") or ""
            exact = ann.get("exact", "")
            context = f"...{prefix} [{exact}] {postfix}..."

            chemicals.append(
                {
                    "name": exact,
                    "chebi_uri": chebi_uri,
                    "chebi_name": chebi_name,
                    "context": context,
                    "section": ann.get("section"),
                }
            )

        return {
            "status": "success",
            "data": {
                "article_id": article_id,
                "chemical_count": len(chemicals[:ARTICLE_ANNOTATION_CAP]),
                "total_chemicals": len(chemicals),
                "chemicals": chemicals[:ARTICLE_ANNOTATION_CAP],
            },
            "metadata": {
                "source": "Europe PMC Annotations API",
                "endpoint": "annotationsByArticleIds?type=Chemicals",
            },
        }
