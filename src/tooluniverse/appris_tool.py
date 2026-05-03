"""APPRIS - Principal Isoform Database tool.

APPRIS annotates alternative splice isoforms and selects principal isoforms
for vertebrate genomes. It uses functional, structural, and conservation
information to label principal and alternative isoforms.

API docs: https://apprisws.bioinfo.cnio.es/
"""

from __future__ import annotations

from typing import Any, Dict

import requests

from .base_tool import BaseTool
from .http_utils import request_with_retry
from .tool_registry import register_tool


@register_tool("APPRISTool")
class APPRISTool(BaseTool):
    """Tool for APPRIS principal isoform annotation queries."""

    BASE_URL = "https://apprisws.bioinfo.cnio.es/rest"

    # Available analysis methods in APPRIS
    VALID_METHODS = {
        "appris",
        "firestar",
        "matador3d",
        "spade",
        "corsair",
        "thump",
        "crash",
        "proteo",
        "tsl",
    }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        fields = self.tool_config.get("fields") or {}
        operation = fields.get("operation", "get_isoforms")

        if operation == "get_isoforms":
            return self._get_isoforms(arguments)
        if operation == "get_principal":
            return self._get_principal(arguments)
        if operation == "get_functional_annotations":
            return self._get_functional_annotations(arguments)
        return {"status": "error", "error": f"Unknown operation: {operation}"}

    def _build_url(self, gene_id: str, species: str = "homo_sapiens") -> str:
        return f"{self.BASE_URL}/exporter/id/{species}/{gene_id}"

    def _fetch(
        self,
        gene_id: str,
        species: str = "homo_sapiens",
        methods: str | None = None,
    ) -> Dict[str, Any]:
        url = self._build_url(gene_id, species)
        params: Dict[str, str] = {"format": "json", "sc": "ensembl"}
        if methods:
            params["methods"] = methods

        try:
            resp = request_with_retry(requests, "GET", url, params=params, timeout=30)
        except Exception as exc:
            return {"status": "error", "error": f"Request failed: {exc}"}

        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"HTTP {resp.status_code}",
                "detail": resp.text[:500],
            }

        try:
            data = resp.json()
        except Exception:
            return {"status": "error", "error": "Failed to parse JSON response"}

        if not data:
            return {
                "status": "error",
                "error": (
                    f"No APPRIS data found for {gene_id}. "
                    "Ensure you use an Ensembl gene ID (ENSG...) for the correct species."
                ),
            }

        return {"status": "success", "data": data}

    @staticmethod
    def _filter_principal_isoforms(records: list) -> list:
        return [r for r in records if r.get("type") == "principal_isoform"]

    def _get_isoforms(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        gene_id = (arguments.get("gene_id") or "").strip()
        if not gene_id:
            return {"status": "error", "error": "gene_id is required"}

        species = (arguments.get("species") or "homo_sapiens").strip()
        result = self._fetch(gene_id, species, methods="appris")
        if result.get("status") == "error":
            return result

        isoforms = self._filter_principal_isoforms(result["data"])
        return {
            "status": "success",
            "data": isoforms,
            "metadata": {
                "gene_id": gene_id,
                "species": species,
                "total_isoforms": len(isoforms),
            },
        }

    def _get_principal(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        gene_id = (arguments.get("gene_id") or "").strip()
        if not gene_id:
            return {"status": "error", "error": "gene_id is required"}

        species = (arguments.get("species") or "homo_sapiens").strip()
        result = self._fetch(gene_id, species, methods="appris")
        if result.get("status") == "error":
            return result

        isoforms = self._filter_principal_isoforms(result["data"])

        priority_order = [f"PRINCIPAL:{i}" for i in range(1, 6)]
        principal = next(
            (
                iso
                for p in priority_order
                for iso in isoforms
                if iso.get("reliability") == p
            ),
            None,
        )

        if not principal and isoforms:
            principal = next(
                (
                    iso
                    for iso in isoforms
                    if "Principal" in (iso.get("annotation") or "")
                ),
                isoforms[0],
            )

        if not principal:
            return {
                "status": "error",
                "error": f"No principal isoform found for {gene_id}",
            }

        return {
            "status": "success",
            "data": principal,
            "metadata": {
                "gene_id": gene_id,
                "species": species,
                "all_isoform_count": len(isoforms),
            },
        }

    def _get_functional_annotations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        gene_id = (arguments.get("gene_id") or "").strip()
        if not gene_id:
            return {"status": "error", "error": "gene_id is required"}

        species = (arguments.get("species") or "homo_sapiens").strip()
        methods = (arguments.get("methods") or "").strip()

        if methods:
            invalid = [
                m
                for m in methods.split(",")
                if m.strip() and m.strip() not in self.VALID_METHODS
            ]
            if invalid:
                return {
                    "status": "error",
                    "error": f"Invalid methods: {invalid}. Valid: {sorted(self.VALID_METHODS)}",
                }

        result = self._fetch(gene_id, species, methods=methods if methods else None)
        if result.get("status") == "error":
            return result

        records = result["data"]

        # Group by annotation type
        by_type: Dict[str, list] = {}
        for r in records:
            t = r.get("type", "unknown")
            by_type.setdefault(t, []).append(r)

        transcript_id = arguments.get("transcript_id")
        if transcript_id:
            filtered: Dict[str, list] = {}
            for t, items in by_type.items():
                matching = [i for i in items if i.get("transcript_id") == transcript_id]
                if matching:
                    filtered[t] = matching
            by_type = filtered

        return {
            "status": "success",
            "data": by_type,
            "metadata": {
                "gene_id": gene_id,
                "species": species,
                "annotation_types": sorted(by_type.keys()),
                "total_records": sum(len(v) for v in by_type.values()),
            },
        }
