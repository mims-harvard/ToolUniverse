"""
OpenNeuro GraphQL API tool for ToolUniverse.

OpenNeuro is an open platform for validating and sharing brain imaging data
(BIDS format). It hosts 1000+ neuroimaging datasets (fMRI, EEG, MRI, etc.).

GraphQL API: https://openneuro.org/crn/graphql
No authentication required for public datasets. Public access.
"""

from .graphql_tool import GraphQLTool
from .tool_registry import register_tool


@register_tool("OpenNeuroTool")
class OpenNeuroTool(GraphQLTool):
    """
    Tool for querying the OpenNeuro neuroimaging data repository.

    OpenNeuro stores brain imaging datasets in BIDS format including:
    - MRI, fMRI, EEG, MEG, PET datasets
    - Dataset metadata, subjects, tasks, modalities
    - Download information and analytics

    No authentication required for public datasets.
    """

    def __init__(self, tool_config: dict):
        endpoint_url = "https://openneuro.org/crn/graphql"
        super().__init__(tool_config, endpoint_url)
