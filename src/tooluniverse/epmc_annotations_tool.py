"""
Europe PMC Annotations API tool for ToolUniverse.

The Europe PMC Annotations API provides text-mined annotations from biomedical
literature, including gene/protein mentions, diseases, organisms, chemicals,
and Gene Ontology terms automatically extracted from full-text articles.

API: https://www.ebi.ac.uk/europepmc/annotations_api/
No authentication required.

Documentation: https://europepmc.org/AnnotationsApi
"""

import requests
from typing import Any

from .base_rest_tool import BaseRESTTool
from .tool_registry import register_tool

ANNOTATIONS_BASE = "https://www.ebi.ac.uk/europepmc/annotations_api"


@register_tool("EPMCAnnotationsTool")
class EPMCAnnotationsTool(BaseRESTTool):
    """
    Tool for retrieving text-mined annotations from Europe PMC articles.

    Provides:
    - Get genes/proteins mentioned in a paper
    - Get diseases mentioned in a paper
    - Get chemicals/drugs mentioned in a paper
    - Get organisms mentioned in a paper
    - Get GO terms mentioned in a paper

    Uses PubMed IDs (PMID) or PMC IDs. No authentication required.
    """

    def __init__(self, tool_config: dict):
        super().__init__(tool_config)
        self.timeout = 30
        self.operation = tool_config.get("fields", {}).get(
            "operation", "get_annotations"
        )

    def run(self, arguments: dict) -> dict:
        """Execute the Annotations API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"EPMC Annotations request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to Europe PMC Annotations API.",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"EPMC Annotations error: {str(e)}",
            }

    def _query(self, arguments: dict) -> dict:
        """Route to the appropriate operation."""
        op = self.operation
        if op == "get_annotations":
            return self._get_annotations(arguments)
        elif op == "get_genes":
            return self._get_entity_type(arguments, "Gene_Proteins")
        elif op == "get_diseases":
            return self._get_entity_type(arguments, "Diseases")
        elif op == "get_chemicals":
            return self._get_entity_type(arguments, "Chemicals")
        elif op == "get_organisms":
            return self._get_entity_type(arguments, "Organisms")
        return {"status": "error", "error": f"Unknown operation: {op}"}

    def _get_annotations(self, arguments: dict) -> dict:
        """Get all text-mined annotations from an article."""
        pmid = str(arguments.get("pmid", "")).strip()
        pmcid = str(arguments.get("pmcid", "")).strip()
        annotation_type = arguments.get("annotation_type", "").strip()

        if not pmid and not pmcid:
            return {
                "status": "error",
                "error": "Either pmid (e.g., '33332779') or pmcid (e.g., 'PMC7781101') is required.",
            }

        # Build article ID
        if pmid:
            article_id = f"MED:{pmid}"
        else:
            article_id = f"PMC:{pmcid.replace('PMC', '')}"

        params: dict[str, str] = {
            "articleIds": article_id,
            "format": "JSON",
        }
        if annotation_type:
            params["type"] = annotation_type

        resp = requests.get(
            f"{ANNOTATIONS_BASE}/annotationsByArticleIds",
            params=params,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        if not data:
            return {
                "status": "success",
                "data": {
                    "article_id": article_id,
                    "annotations": [],
                    "annotation_counts": {},
                },
                "metadata": {
                    "source": "Europe PMC Annotations",
                },
            }

        # Parse annotations from first result
        article = data[0] if isinstance(data, list) else data
        raw_annotations = article.get("annotations", [])

        # Group by type and deduplicate
        by_type: dict[str, dict[str, dict]] = {}
        for ann in raw_annotations:
            ann_type = ann.get("type", "Unknown")
            exact = ann.get("exact", "")
            if ann_type not in by_type:
                by_type[ann_type] = {}
            if exact and exact not in by_type[ann_type]:
                tags = ann.get("tags", [])
                uri = tags[0].get("uri", "") if tags else ""
                tag_name = tags[0].get("name", "") if tags else ""
                by_type[ann_type][exact] = {
                    "text": exact,
                    "tag_name": tag_name,
                    "uri": uri,
                    "count": 1,
                }
            elif exact in by_type.get(ann_type, {}):
                by_type[ann_type][exact]["count"] += 1

        # Build structured output
        annotation_groups = {}
        annotation_counts = {}
        for ann_type, entities in by_type.items():
            sorted_entities = sorted(entities.values(), key=lambda x: -x["count"])
            annotation_groups[ann_type] = sorted_entities[:30]
            annotation_counts[ann_type] = len(entities)

        return {
            "status": "success",
            "data": {
                "article_id": article_id,
                "pmcid": article.get("pmcid"),
                "annotations": annotation_groups,
                "annotation_counts": annotation_counts,
            },
            "metadata": {
                "source": "Europe PMC Annotations",
                "description": (
                    "Text-mined annotations from biomedical literature. "
                    "Types include Gene_Proteins, Diseases, Chemicals, Organisms, "
                    "Gene_Ontology, EFO. count = number of mentions in the article."
                ),
            },
        }

    def _get_entity_type(self, arguments: dict, entity_type: str) -> dict:
        """Get annotations of a specific type from an article."""
        # Inject annotation_type and delegate to get_annotations
        arguments = dict(arguments)
        arguments["annotation_type"] = entity_type
        result = self._get_annotations(arguments)

        # Filter to just the requested type
        if result.get("status") == "success":
            all_annotations = result["data"].get("annotations", {})
            type_annotations = all_annotations.get(entity_type, [])
            result["data"]["annotations"] = type_annotations
            result["data"]["total_entities"] = len(type_annotations)
            result["data"]["entity_type"] = entity_type

        return result
