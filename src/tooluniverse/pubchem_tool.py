# pubchem_tool.py

import requests
import re
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URL for PubChem PUG-REST
PUBCHEM_BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

# Base URL for PubChem PUG-View
PUBCHEM_PUGVIEW_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view"


@register_tool("PubChemRESTTool")
class PubChemRESTTool(BaseTool):
    """
    Generic PubChem PUG-REST tool class.
    Directly concatenates URL from the fields.endpoint template and sends requests to PubChem PUG-REST.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        # Read endpoint template directly from fields config
        self.endpoint_template = tool_config["fields"]["endpoint"]
        # input_description and output_description might not be used, but kept for LLM reference
        self.input_description = tool_config["fields"].get("input_description", "")
        self.output_description = tool_config["fields"].get("output_description", "")
        # If property_list exists, it will be used to replace {property_list} placeholder
        self.property_list = tool_config["fields"].get("property_list", None)
        # Parameter schema (properties may include required field)
        self.param_schema = tool_config["parameter"]["properties"]
        self.use_pugview = tool_config["fields"].get("use_pugview", False)
        self.output_format = tool_config["fields"].get("return_format", None)

    def _build_url(self, arguments: dict) -> str:
        """
        Use regex to replace all {placeholder} in endpoint_template to generate complete URL path.
        For example endpoint_template="/compound/cid/{cid}/property/{property_list}/JSON"
        arguments={"cid":2244}, property_list=["MolecularWeight","IUPACName"]
        → "/compound/cid/2244/property/MolecularWeight,IUPACName/JSON"
        Finally returns "https://pubchem.ncbi.nlm.nih.gov/rest/pug" + concatenated path.
        """
        url_path = self.endpoint_template

        # First replace property_list (if exists and endpoint_template contains this placeholder)
        if self.property_list and "{property_list}" in url_path:
            prop_str = ",".join(self.property_list)
            url_path = url_path.replace("{property_list}", prop_str)

        # Find all placeholders {xxx} in template
        placeholders = re.findall(r"\{([^{}]+)\}", url_path)
        for ph in placeholders:
            if ph not in arguments:
                # If a placeholder cannot find corresponding value in arguments, report error
                raise ValueError(
                    f"Missing required parameter '{ph}' to replace placeholder in URL."
                )
            val = arguments[ph]
            # If input value is a list, join with commas
            if isinstance(val, list):
                val_str = ",".join(map(str, val))
            else:
                val_str = str(val)
            url_path = url_path.replace(f"{{{ph}}}", val_str)

        # Handle xref_types parameter
        if "xref_types" in arguments:
            xref_list = ",".join(arguments["xref_types"])
            url_path = url_path.replace("{xref_list}", xref_list)

        # Finally combine into complete URL
        if self.use_pugview:
            full_url = PUBCHEM_PUGVIEW_URL + url_path
        else:
            full_url = PUBCHEM_BASE_URL + url_path

        # Handle special parameters
        if "threshold" in arguments:
            # Convert 0-1 threshold to 0-100 integer
            threshold = float(arguments["threshold"])
            if 0 <= threshold <= 1:
                threshold = int(threshold * 100)
            # Add threshold parameter to URL
            if "?" in full_url:
                full_url += f"&Threshold={threshold}"
            else:
                full_url += f"?Threshold={threshold}"

        return full_url

    def run(self, arguments: dict):
        # 1. Validate required parameters
        for key, prop in self.param_schema.items():
            if prop.get("required", False) and key not in arguments:
                return {"error": f"Parameter '{key}' is required."}

        # 2. Build URL
        try:
            url = self._build_url(arguments)
        except ValueError as e:
            return {"error": str(e)}

        # 3. Send HTTP GET request
        try:
            # Increase timeout to 30 seconds and add MaxRecords parameter to limit results
            if "fastsubstructure" in url or "fastsimilarity" in url:
                max_records = arguments.get("max_results", 10)
                if "?" in url:
                    url += f"&MaxRecords={max_records}"
                else:
                    url += f"?MaxRecords={max_records}"

            resp = requests.get(url, timeout=30)
        except requests.Timeout:
            return {
                "error": "Request to PubChem PUG-REST timed out, try reducing query scope or retry later."
            }
        except Exception as e:
            return {"error": f"Failed to request PubChem PUG-REST: {str(e)}"}

        # 4. Check HTTP status code
        if resp.status_code != 200:
            error_detail = resp.text
            try:
                error_json = resp.json()
                if "Fault" in error_json:
                    error_detail = error_json["Fault"].get("Message", error_detail)
            except Exception:
                pass
            return {
                "error": f"PubChem API returned HTTP {resp.status_code}",
                "detail": error_detail,
            }

        # 5. Determine return type based on URL suffix
        #    Look at the text after the last slash in endpoint_template, like "JSON","PNG","XML","TXT","CSV"
        if self.output_format:
            out_fmt = self.output_format
        else:
            # Strip query parameters before determining format
            endpoint_path = self.endpoint_template.split("?")[0]
            out_fmt = endpoint_path.strip("/").split("/")[-1].upper()

        if out_fmt == "JSON":
            try:
                return resp.json()
            except ValueError:
                ct = resp.headers.get("content-type", "")
                return {
                    "error": "Response content cannot be parsed as JSON.",
                    "content_type": ct,
                    "content": resp.text[:200],
                    "retryable": "text/html" in ct
                    or resp.text.lstrip().startswith("<"),
                }
        elif out_fmt in ["XML", "TXT", "CSV", "SDF"]:
            # These are all text formats
            return resp.text
        elif out_fmt in ["PNG", "SVG"]:
            # Return binary image
            return resp.content
        else:
            # Return text for other cases
            return resp.text
