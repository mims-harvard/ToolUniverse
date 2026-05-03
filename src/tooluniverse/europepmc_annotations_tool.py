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
            status = e.response.status_code if e.response else "unknown"
            return {
                "status": "error",
                "error": f"Europe PMC Annotations API HTTP error: {status}",
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

    def _fetch_annotations(
        self, article_ids: str, annotation_type: str = None, page_size: int = None
    ):
        """Fetch annotations from the API."""
        url = f"{EUROPEPMC_ANNOTATIONS_URL}/annotationsByArticleIds"
        params = {
            "articleIds": article_ids,
            "format": "JSON",
        }
        if annotation_type:
            params["type"] = annotation_type
        if page_size:
            params["pageSize"] = page_size

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _normalize_article_id(article_id: str) -> str:
        """Normalize bare PMC/PMID to API format: PMC:PMC4353746 or MED:25780448."""
        aid = article_id.strip()
        if aid.startswith("PMC:") or aid.startswith("MED:"):
            return aid
        if aid.upper().startswith("PMC"):
            num = aid[3:]
            return f"PMC:PMC{num}"
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
                "annotation_count": len(annotations),
                "annotations": annotations[:200],
            },
            "metadata": {
                "source": "Europe PMC Annotations API",
                "endpoint": "annotationsByArticleIds",
            },
        }

    def _batch_by_type(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get annotations of a specific type from multiple articles."""
        article_ids = arguments.get("article_ids", "")
        annotation_type = arguments.get("annotation_type", "")
        page_size = arguments.get("page_size")

        if not article_ids:
            return {
                "status": "error",
                "error": "article_ids is required (e.g., 'PMC:PMC4353746,PMC:PMC3531190')",
            }
        if not annotation_type:
            return {
                "status": "error",
                "error": "annotation_type is required (e.g., 'Chemicals')",
            }

        raw = self._fetch_annotations(article_ids, annotation_type, page_size)

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

            articles.append(
                {
                    "article_id": f"{article.get('source', '')}:{article.get('extId', '')}",
                    "pmcid": article.get("pmcid"),
                    "annotation_count": len(annotations),
                    "annotations": annotations[:100],
                }
            )

        return {
            "status": "success",
            "data": {
                "article_count": len(articles),
                "annotation_type": annotation_type,
                "total_annotations": total_annotations,
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
                "chemical_count": len(chemicals),
                "chemicals": chemicals[:200],
            },
            "metadata": {
                "source": "Europe PMC Annotations API",
                "endpoint": "annotationsByArticleIds?type=Chemicals",
            },
        }
