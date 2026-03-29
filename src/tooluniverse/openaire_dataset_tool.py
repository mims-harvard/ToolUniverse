"""
OpenAIRE dataset search tool for ToolUniverse.

Searches the OpenAIRE dataset index for European open science datasets
with optional funder and country filters.

API Documentation: https://api.openaire.eu/
"""

import requests
from .base_tool import BaseTool
from .tool_registry import register_tool

OPENAIRE_DATASETS_URL = "https://api.openaire.eu/search/datasets"


@register_tool("OpenAIREDatasetTool")
class OpenAIREDatasetTool(BaseTool):
    """Search OpenAIRE for European research datasets."""

    def run(self, arguments=None):
        arguments = arguments or {}
        keywords = (arguments.get("keywords") or "").strip()
        funder = arguments.get("funder")
        country = arguments.get("country")
        size = max(1, min(int(arguments.get("size", 10)), 100))

        if not keywords:
            return {
                "status": "error",
                "error": {
                    "message": "Missing required parameter: keywords",
                    "details": "Provide search keywords for dataset discovery.",
                },
            }

        params = {"keywords": keywords, "format": "json", "size": size}
        if funder:
            params["funder"] = funder
        if country:
            params["country"] = country

        try:
            resp = requests.get(OPENAIRE_DATASETS_URL, params=params, timeout=60)
            resp.raise_for_status()
            body = resp.json()
        except requests.RequestException as exc:
            return {
                "status": "error",
                "error": {
                    "message": "OpenAIRE API request failed",
                    "details": str(exc),
                },
            }

        header = body.get("response", {}).get("header", {})
        total = int(header.get("total", {}).get("$", 0))
        items = body.get("response", {}).get("results", {}).get("result", []) or []

        datasets = []
        for item in items:
            entity = (
                item.get("metadata", {}).get("oaf:entity", {}).get("oaf:result", {})
            )
            if not entity:
                # Fallback: some responses nest directly under metadata
                entity = item.get("metadata", {}).get("oaf:result", {})
            if not entity:
                continue

            title = self._extract_text(entity.get("title"))
            description = self._extract_text(entity.get("description"))
            if description and len(description) > 500:
                description = description[:497] + "..."

            creators = self._extract_text_list(entity.get("creator"))
            date = self._extract_text(entity.get("dateofacceptance"))
            publisher = self._extract_text(entity.get("publisher"))

            access = entity.get("bestaccessright", {})
            access_rights = (
                access.get("@classname") if isinstance(access, dict) else None
            )

            doi = self._extract_doi(entity.get("pid"))
            subjects = self._extract_text_list(entity.get("subject"))

            datasets.append(
                {
                    "title": title,
                    "description": description,
                    "creators": creators,
                    "date": date,
                    "publisher": publisher,
                    "access_rights": access_rights,
                    "doi": doi,
                    "subjects": subjects,
                }
            )

        return {
            "status": "success",
            "data": {
                "keywords": keywords,
                "funder": funder,
                "country": country,
                "total_count": total,
                "returned": len(datasets),
                "datasets": datasets,
            },
            "metadata": {
                "source": "OpenAIRE",
                "api": OPENAIRE_DATASETS_URL,
            },
        }

    @staticmethod
    def _extract_text(field):
        """Extract first text value from OpenAIRE's {'$': value} or list-of-dicts."""
        if field is None:
            return None
        if isinstance(field, str):
            return field
        if isinstance(field, dict):
            return field.get("$")
        if isinstance(field, list):
            for item in field:
                val = item.get("$") if isinstance(item, dict) else item
                if val:
                    return val
        return None

    @staticmethod
    def _extract_text_list(field):
        """Extract all text values from OpenAIRE's {'$': value} or list-of-dicts."""
        if field is None:
            return []
        if isinstance(field, dict):
            val = field.get("$")
            return [val] if val else []
        if isinstance(field, list):
            return [
                v
                for item in field
                for v in [item.get("$") if isinstance(item, dict) else item]
                if v
            ]
        return []

    @staticmethod
    def _extract_doi(pid_field):
        """Extract DOI from OpenAIRE pid field."""
        if pid_field is None:
            return None
        pids = [pid_field] if isinstance(pid_field, dict) else (pid_field or [])
        for p in pids:
            if isinstance(p, dict) and p.get("@classid") == "doi":
                return p.get("$")
        return None
