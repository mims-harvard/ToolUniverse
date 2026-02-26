"""
SwissTargetPrediction Tool

Predicts the most probable protein targets of small molecules based on
a combination of 2D and 3D similarity measures with known ligands.

This tool handles the full web-based workflow:
1. POST the SMILES and organism to predict.php (streamed chunked response)
2. Parse the job redirect URL from the final JS in the streamed response
3. GET result.php with the job ID to retrieve the HTML results table
4. Parse the HTML table into structured JSON data

SwissTargetPrediction does NOT have a public REST/JSON API. It uses
a server-side computation triggered by form POST with progress updates
streamed as inline <script> tags. The final redirect URL contains the
job ID needed to fetch results.

Supported organisms: Homo sapiens, Mus musculus, Rattus norvegicus,
Bos taurus, Sus scrofa

Base URL: https://www.swisstargetprediction.ch/
No authentication required.

Reference: Daina et al., Nucleic Acids Research, 2019 (PMID: 31106366)
"""

import re
import requests
from typing import Dict, Any, List, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool


SWISS_TARGET_BASE_URL = "https://www.swisstargetprediction.ch"

# Supported organisms - these are the radio button values on the website
SUPPORTED_ORGANISMS = [
    {
        "value": "Homo_sapiens",
        "display_name": "Homo sapiens",
        "common_name": "Human",
        "taxonomy_id": 9606,
    },
    {
        "value": "Mus_musculus",
        "display_name": "Mus musculus",
        "common_name": "Mouse",
        "taxonomy_id": 10090,
    },
    {
        "value": "Rattus_norvegicus",
        "display_name": "Rattus norvegicus",
        "common_name": "Rat",
        "taxonomy_id": 10116,
    },
    {
        "value": "Bos_taurus",
        "display_name": "Bos taurus",
        "common_name": "Cow",
        "taxonomy_id": 9913,
    },
    {
        "value": "Sus_scrofa",
        "display_name": "Sus scrofa",
        "common_name": "Pig",
        "taxonomy_id": 9823,
    },
]


@register_tool("SwissTargetTool")
class SwissTargetTool(BaseTool):
    """
    Tool for predicting protein targets of small molecules using
    SwissTargetPrediction.

    SwissTargetPrediction uses a combination of 2D (FP2, MACCS, Morgan)
    and 3D (Electroshape) similarity measures to predict the most
    probable macromolecular targets of a small molecule.

    Supported operations:
    - predict: Predict protein targets for a given SMILES
    - get_organisms: List supported organisms for prediction
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the SwissTargetPrediction tool with given arguments."""
        operation = arguments.get("operation")
        if not operation:
            return {
                "status": "error",
                "error": "Missing required parameter: operation",
            }

        operation_handlers = {
            "predict": self._predict,
            "get_organisms": self._get_organisms,
        }

        handler = operation_handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": "Unknown operation: {}. Available: {}".format(
                    operation, list(operation_handlers.keys())
                ),
            }

        try:
            return handler(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": "SwissTargetPrediction request timed out. "
                "The server may be busy. Please try again later.",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Could not connect to SwissTargetPrediction. "
                "The service may be temporarily unavailable.",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": "SwissTargetPrediction error: {}".format(str(e)),
            }

    def _predict(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict protein targets for a SMILES molecule.

        Workflow:
        1. POST SMILES + organism to predict.php (streamed response)
        2. Extract job redirect URL from the last <script> tag
        3. GET result.php?job=X&organism=Y to fetch results
        4. Parse the HTML DataTable into structured data
        """
        smiles = arguments.get("smiles")
        if not smiles:
            return {"status": "error", "error": "Missing required parameter: smiles"}

        organism = arguments.get("organism", "Homo_sapiens")
        # Normalize organism name
        organism = organism.replace(" ", "_")

        # Validate organism
        valid_organisms = [o["value"] for o in SUPPORTED_ORGANISMS]
        if organism not in valid_organisms:
            return {
                "status": "error",
                "error": "Invalid organism '{}'. Valid options: {}".format(
                    organism, valid_organisms
                ),
            }

        top_n = arguments.get("top_n")

        # Step 1: Submit prediction job via POST to predict.php
        # The response is streamed with progress updates as inline scripts
        # The final script contains the redirect URL with the job ID
        try:
            resp = self.session.post(
                "{}/predict.php".format(SWISS_TARGET_BASE_URL),
                data={
                    "smiles": smiles,
                    "organism": organism,
                    "ioi": "2",
                },
                headers={
                    "Referer": "{}/index.php".format(SWISS_TARGET_BASE_URL),
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                timeout=180,  # Computation can take up to 60 seconds
                stream=False,
            )
        except requests.exceptions.ReadTimeout:
            return {
                "status": "error",
                "error": "Prediction computation timed out (>180s). "
                "Try a simpler molecule or try again later.",
            }

        if resp.status_code != 200:
            return {
                "status": "error",
                "error": "Prediction submission failed with HTTP {}".format(
                    resp.status_code
                ),
            }

        # Step 2: Extract job URL from the streamed response
        # The last script tag contains: location.replace("...result.php?job=XXXX&organism=Y")
        job_url = self._extract_job_url(resp.text)
        if not job_url:
            # Check if molecule was invalid
            if "not valid" in resp.text.lower() or "invalid" in resp.text.lower():
                return {
                    "status": "error",
                    "error": "The SMILES '{}' was rejected as invalid by "
                    "SwissTargetPrediction. Ensure it is a valid, "
                    "druglike small molecule.".format(smiles),
                }
            return {
                "status": "error",
                "error": "Failed to extract job URL from prediction response. "
                "The computation may have failed or timed out.",
            }

        # Step 3: Fetch result page
        # Ensure HTTPS
        if job_url.startswith("http://"):
            job_url = job_url.replace("http://", "https://", 1)

        try:
            result_resp = self.session.get(
                job_url,
                headers={
                    "Referer": "{}/predict.php".format(SWISS_TARGET_BASE_URL),
                },
                timeout=60,
            )
        except Exception as e:
            return {
                "status": "error",
                "error": "Failed to fetch results: {}".format(str(e)),
            }

        if result_resp.status_code != 200:
            return {
                "status": "error",
                "error": "Result page returned HTTP {}".format(result_resp.status_code),
            }

        # Step 4: Parse HTML table
        targets = self._parse_result_table(result_resp.text)
        if targets is None:
            return {
                "status": "error",
                "error": "No prediction results found in the response. "
                "The job may have failed or the molecule was too complex.",
            }

        # Apply top_n filter if specified
        if top_n is not None and top_n > 0:
            targets = targets[:top_n]

        # Extract job ID for reference
        job_match = re.search(r"job=(\d+)", job_url)
        job_id = job_match.group(1) if job_match else None

        return {
            "status": "success",
            "data": {
                "targets": targets,
                "query": {
                    "smiles": smiles,
                    "organism": organism,
                    "job_id": job_id,
                },
                "total_targets": len(targets),
                "result_url": job_url,
            },
        }

    def _get_organisms(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Return the list of supported organisms."""
        return {
            "status": "success",
            "data": {
                "organisms": SUPPORTED_ORGANISMS,
                "total": len(SUPPORTED_ORGANISMS),
            },
        }

    def _extract_job_url(self, html: str) -> Optional[str]:
        """
        Extract the result page URL from the streamed predict.php response.

        The predict.php response uses chunked transfer encoding to stream
        progress updates. The final chunk contains a JavaScript redirect:
        location.replace("http://www.swisstargetprediction.ch/result.php?job=XXXX&organism=Y");
        """
        # Look for location.replace or location.href patterns
        patterns = [
            r'location\.replace\(["\']([^"\']+result\.php[^"\']*)["\']',
            r'location\.href\s*=\s*["\']([^"\']+result\.php[^"\']*)["\']',
            r'window\.location\s*=\s*["\']([^"\']+result\.php[^"\']*)["\']',
        ]
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(1)
        return None

    def _parse_result_table(self, html: str) -> Optional[List[Dict[str, Any]]]:
        """
        Parse the HTML result table from result.php.

        The table has columns:
        Target | Common name | Uniprot ID | ChEMBL ID | Target Class | Probability* | Known actives (3D/2D)
        """
        # Find the result table
        table_match = re.search(
            r'<table[^>]*id=["\']resultTable["\'][^>]*>(.*?)</table>',
            html,
            re.S,
        )
        if not table_match:
            return None

        table_html = table_match.group(1)

        # Extract rows (skip header row)
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", table_html, re.S)

        targets = []
        for row in rows:
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
            if len(cells) < 7:
                continue

            # Clean HTML from cell content
            clean_cells = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]

            # Parse probability
            try:
                probability = float(clean_cells[5])
            except (ValueError, IndexError):
                probability = 0.0

            # Parse known actives (format: "X / Y")
            actives_text = re.sub(r"&nbsp;", "", clean_cells[6]).strip()
            actives_3d = 0
            actives_2d = 0
            actives_match = re.match(r"(\d+)\s*/\s*(\d+)", actives_text)
            if actives_match:
                actives_3d = int(actives_match.group(1))
                actives_2d = int(actives_match.group(2))

            targets.append(
                {
                    "target_name": clean_cells[0],
                    "gene_symbol": clean_cells[1],
                    "uniprot_id": clean_cells[2],
                    "chembl_id": clean_cells[3],
                    "target_class": clean_cells[4],
                    "probability": probability,
                    "known_actives_3d": actives_3d,
                    "known_actives_2d": actives_2d,
                }
            )

        # Sort by probability descending (should already be, but ensure)
        targets.sort(key=lambda x: x["probability"], reverse=True)

        return targets if targets else None
