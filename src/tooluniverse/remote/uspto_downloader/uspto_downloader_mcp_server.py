from fastmcp import FastMCP
import os
from tooluniverse.remote.uspto_downloader.uspto_downloader_tool import (
    USPTOPatentDocumentDownloader,
)
from tooluniverse.server_security import (
    get_fastmcp_token_auth,
    run_fastmcp_server,
)
import json

# Read the tool config dicts from the JSON file
try:
    with open(
        os.path.join(os.path.dirname(__file__), "uspto_downloader_client_tools.json"),
        "r",
    ) as f:
        uspto_downloader_tools = json.load(f)
except FileNotFoundError as exc:
    raise RuntimeError("USPTO downloader tool configuration is missing.") from exc


server = FastMCP("USPTO Document MCP Server", auth=get_fastmcp_token_auth())
agents = {}
for tool_config in uspto_downloader_tools:
    agents[tool_config["name"]] = USPTOPatentDocumentDownloader(tool_config=tool_config)


@server.tool()
def get_abstract_from_patent_app_number(applicationNumberText: str):
    """Retrieve the abstract of a patent application by its application number.
    Args:
        applicationNumberText: An 8- to 16-digit USPTO application number.
    Returns
        dict: A dictionary containing the abstract text under the 'result' key or an error message under the 'error' key if the document could not be retrieved.
    """
    return agents["get_abstract_from_patent_app_number"].run(
        {"applicationNumberText": applicationNumberText}
    )


@server.tool()
def get_claims_from_patent_app_number(applicationNumberText: str):
    """Retrieve the claims of a patent application by its application number.
    Args:
        applicationNumberText: An 8- to 16-digit USPTO application number.
    Returns
        dict: A dictionary containing the claims text under the 'result' key or an error message under the 'error' key if the document could not be retrieved.
    """
    return agents["get_claims_from_patent_app_number"].run(
        {"applicationNumberText": applicationNumberText}
    )


@server.tool()
def get_full_text_from_patent_app_number(applicationNumberText: str):
    """Retrieve the full text of a patent application by its application number.
    Args:
        applicationNumberText: An 8- to 16-digit USPTO application number.
    Returns
        dict: A dictionary containing the full text under the 'result' key or an error message under the 'error' key if the document could not be retrieved.
    """
    return agents["get_full_text_from_patent_app_number"].run(
        {"applicationNumberText": applicationNumberText}
    )


if __name__ == "__main__":
    run_fastmcp_server(
        server,
        host=os.getenv("TOOLUNIVERSE_MCP_HOST", "127.0.0.1"),
        port=8081,
        stateless_http=True,
    )
