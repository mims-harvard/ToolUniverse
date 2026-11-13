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

# Each distinct mention carries its own sentence context and section. The
# deduplicated entity keeps this many of them, and discloses the count and the
# cut, so "tocilizumab, 11 mentions" is no longer the whole of what was mined.
MENTIONS_PER_ENTITY = 5


def _section_name(section: Any) -> "str | None":
    """'Abstract (http://purl.org/dc/terms/abstract)' -> 'Abstract'."""
    if not isinstance(section, str) or not section.strip():
        return None
    return section.split(" (", 1)[0].strip() or None


def _tags(ann: dict) -> list:
    """Every grounded concept, not only the first.

    An Open Targets 'Gene Disease Relationship' annotation carries two tags --
    the gene and the disease -- and reading `tags[0]` returned the gene and
    dropped the disease the relationship is about.
    """
    return [
        {"name": tag.get("name"), "uri": tag.get("uri")}
        for tag in (ann.get("tags") or [])
        if isinstance(tag, dict)
    ]


def _mention(ann: dict) -> dict:
    """One occurrence: the sentence around it, where it was, and who mined it."""
    return {
        "prefix": ann.get("prefix"),
        "exact": ann.get("exact"),
        "postfix": ann.get("postfix"),
        "section": _section_name(ann.get("section")),
        "provider": ann.get("provider"),
        "annotation_id": ann.get("id"),
    }


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

        # Group by type and deduplicate. Deduplication is by the mined text, so
        # everything that distinguishes one occurrence from another -- the
        # section it is in, the provider that mined it, the sentence around it
        # -- is collected across the occurrences rather than taken from the
        # first and discarded for the rest.
        by_type: dict[str, dict[str, dict]] = {}
        for ann in raw_annotations:
            ann_type = ann.get("type", "Unknown")
            exact = ann.get("exact", "")
            if not exact:
                continue
            bucket = by_type.setdefault(ann_type, {})
            tags = _tags(ann)
            entry = bucket.get(exact)
            if entry is None:
                entry = bucket[exact] = {
                    "text": exact,
                    "tag_name": tags[0]["name"] if tags else "",
                    "uri": tags[0]["uri"] if tags else "",
                    "tags": tags,
                    "tag_count": len(tags),
                    "count": 1,
                    "sections": [],
                    "providers": [],
                    "sub_types": [],
                    "mentions": [],
                    "mentions_truncated": False,
                }
            else:
                entry["count"] += 1
                for tag in tags:
                    if tag not in entry["tags"]:
                        entry["tags"].append(tag)
                entry["tag_count"] = len(entry["tags"])
            for key, value in (
                ("sections", _section_name(ann.get("section"))),
                ("providers", ann.get("provider")),
                ("sub_types", ann.get("subType")),
            ):
                if value and value not in entry[key]:
                    entry[key].append(value)
            if len(entry["mentions"]) < MENTIONS_PER_ENTITY:
                entry["mentions"].append(_mention(ann))
            else:
                entry["mentions_truncated"] = True

        # Build structured output
        annotation_groups = {}
        annotation_counts = {}
        for ann_type, entities in by_type.items():
            sorted_entities = sorted(entities.values(), key=lambda x: -x["count"])
            annotation_groups[ann_type] = sorted_entities
            annotation_counts[ann_type] = len(entities)

        sections = sorted(
            {
                name
                for ann in raw_annotations
                if (name := _section_name(ann.get("section")))
            }
        )
        providers = sorted(
            {ann["provider"] for ann in raw_annotations if ann.get("provider")}
        )

        return {
            "status": "success",
            "data": {
                "article_id": article_id,
                "pmcid": article.get("pmcid"),
                "article_source": article.get("source"),
                "ext_id": article.get("extId"),
                "full_text_ids": article.get("fullTextIdList") or [],
                "annotations": annotation_groups,
                "annotation_counts": annotation_counts,
                "total_annotations": len(raw_annotations),
                "sections": sections,
                "providers": providers,
            },
            "metadata": {
                "source": "Europe PMC Annotations",
                "mentions_per_entity": MENTIONS_PER_ENTITY,
                "description": (
                    "Text-mined annotations from biomedical literature. "
                    "Types include Gene_Proteins, Diseases, Chemicals, Organisms, "
                    "Gene_Ontology, EFO. count = number of mentions in the article; "
                    "mentions carries up to mentions_per_entity of them with the "
                    "sentence context, the article section and the mining provider, "
                    "and mentions_truncated says when there were more. tags holds "
                    "every grounded concept, which for a relationship annotation is "
                    "both ends of the relationship."
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
            result["data"]["total_entities"] = (
                result["data"]
                .get("annotation_counts", {})
                .get(entity_type, len(type_annotations))
            )
            result["data"]["returned_entities"] = len(type_annotations)
            result["data"]["entity_type"] = entity_type

        return result
