from fastmcp import FastMCP
import json
import os
import sys

from tooluniverse.remote.uspto_downloader.uspto_downloader_tool import (
    USPTOPatentDocumentDownloader,
)

# Read the tool config dicts from the JSON file
try:
    with open(
        os.path.join(os.path.dirname(__file__), "uspto_downloader_client_tools.json"),
        "r",
    ) as f:
        uspto_downloader_tools = json.load(f)
except FileNotFoundError as e:
    print(f"\033[91mError: {e}\033[0m")
    print(
        f"\033[91mIs uspto_downloader_client_tools.json in the parent directory of {__file__}?\033[0m"
    )
    sys.exit(1)


def _optional_token_auth():
    """Require a Bearer token only when TOOLUNIVERSE_API_TOKEN is set.

    Returns None (no authentication, unchanged behavior) when the variable is
    not set, so existing deployments are unaffected.
    """
    token = os.getenv("TOOLUNIVERSE_API_TOKEN")
    if not token:
        return None
    try:
        from fastmcp.server.auth import StaticTokenVerifier

        return StaticTokenVerifier(
            tokens={token: {"client_id": "tooluniverse", "scopes": []}}
        )
    except Exception:
        return None


server = FastMCP("USPTO Patent Document Downloader", auth=_optional_token_auth())
agents = {}
for tool_config in uspto_downloader_tools:
    agents[tool_config["name"]] = USPTOPatentDocumentDownloader(tool_config=tool_config)


@server.tool()
def get_abstract_from_patent_app_number(applicationNumberText: str):
    """Retrieve a patent application's abstract by application number."""
    return agents["get_abstract_from_patent_app_number"].run(
        {"applicationNumberText": applicationNumberText}
    )


@server.tool()
def get_claims_from_patent_app_number(applicationNumberText: str):
    """Retrieve a patent application's claims by application number."""
    return agents["get_claims_from_patent_app_number"].run(
        {"applicationNumberText": applicationNumberText}
    )


@server.tool()
def get_full_text_from_patent_app_number(applicationNumberText: str):
    """Retrieve a patent application's full text by application number."""
    return agents["get_full_text_from_patent_app_number"].run(
        {"applicationNumberText": applicationNumberText}
    )


def main():
    server.run(
        transport="streamable-http", host="0.0.0.0", port=8081, stateless_http=True
    )


if __name__ == "__main__":
    main()
