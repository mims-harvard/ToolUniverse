import requests
from typing import Any, Dict
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("RegulomeDBRESTTool")
class RegulomeDBRESTTool(BaseTool):
    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.base_url = "https://regulomedb.org"
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self.timeout = 30

    def _build_url(self, args: Dict[str, Any]) -> str:
        url = self.tool_config["fields"]["endpoint"]
        for k, v in args.items():
            url = url.replace(f"{{{k}}}", str(v))
        return url

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        # Accept 'variant' as alias for 'rsid' (used by RegulomeDB_get_score)
        if "rsid" not in arguments and arguments.get("variant"):
            arguments = dict(arguments, rsid=arguments["variant"])
        try:
            url = self._build_url(arguments)
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            raw = response.json()
        except Exception as e:
            return {"status": "error", "error": f"RegulomeDB API error: {str(e)}"}

        # Extract the key RegulomeDB fields; @graph contains raw ENCODE datasets
        # (hundreds of entries) and is not useful for most callers.
        variants = raw.get("variants", [])
        if not variants:
            return {
                "status": "error",
                "error": f"No RegulomeDB results for rsID '{arguments.get('rsid', '')}'",
            }

        result = {
            "rsid": arguments.get("rsid", ""),
            "assembly": raw.get("assembly"),
            "query_coordinates": raw.get("query_coordinates"),
            "regulome_score": raw.get("regulome_score"),
            "variants": variants,
            "features": raw.get("features"),
            "nearby_snps": raw.get("nearby_snps", [])[:10],
            "notifications": raw.get("notifications"),
            "total_supporting_datasets": len(raw.get("@graph", [])),
        }
        result.update(self._summarize_motifs(raw.get("@graph", [])))
        return {"status": "success", "data": result, "url": url}

    # RegulomeDB records a motif hit under two methods: "PWMs" (the position
    # weight matrix matched here) and "footprints" (a DNase footprint was called
    # for that factor here). The site's Motifs tab lists the union of the two,
    # one row per target label -- so PWM rows alone undercount it. `features`
    # only carries booleans (`PWM: true`), which cannot answer "how many motifs
    # are annotated here" at all.
    MOTIF_METHODS = ("PWMs", "footprints")

    @staticmethod
    def _summarize_motifs(graph):
        """Motif annotations from the evidence graph, matching the Motifs tab.

        Target labels are kept verbatim: RegulomeDB emits a combined label such
        as "STAT5A, STAT5B" for a matrix shared by two factors, and the site
        shows it as a single motif row. Splitting it would undercount.
        """
        rows = []
        for entry in graph or []:
            method = entry.get("method")
            if method not in RegulomeDBRESTTool.MOTIF_METHODS:
                continue
            rows.append(
                {
                    "target_label": entry.get("target_label"),
                    "method": method,
                    "chrom": entry.get("chrom"),
                    "start": entry.get("start"),
                    "end": entry.get("end"),
                    "strand": entry.get("strand"),
                }
            )

        by_target = {}
        for row in rows:
            target = row["target_label"]
            slot = by_target.setdefault(
                target, {"target_label": target, "methods": set(), "n_records": 0}
            )
            slot["methods"].add(row["method"])
            slot["n_records"] += 1

        motifs = [
            {
                "target_label": v["target_label"],
                "methods": sorted(v["methods"]),
                "n_records": v["n_records"],
            }
            for v in by_target.values()
        ]
        motifs.sort(key=lambda m: str(m["target_label"] or ""))

        return {
            "motifs": motifs,
            "motif_count": len(motifs),
            "motif_records": len(rows),
            "motif_note": (
                "motif_count is the number of distinct motif target labels across "
                "PWM and footprint evidence, matching the RegulomeDB Motifs tab. "
                "A combined label such as 'STAT5A, STAT5B' counts as one motif."
            ),
        }
