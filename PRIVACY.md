# Privacy Policy

**ToolUniverse** — Claude Desktop extension (`tooluniverse`) and the `tooluniverse` Python package.
Last updated: 2026-09-24.

ToolUniverse runs entirely on your own machine. It is a local MCP server that
dispatches calls to public scientific APIs. This policy describes what it does
with data, and what it does not.

## What we collect

**Nothing.** The ToolUniverse project operates no servers, collects no
telemetry, no analytics, no usage statistics and no crash reports. Your
conversations, prompts, files and tool results are never sent to the
ToolUniverse maintainers and are never seen by us.

## What leaves your machine, and when

When you run a tool, the arguments you supplied for that tool are sent to that
tool's data provider so it can answer. Nothing else is transmitted, and nothing
is transmitted until a tool runs.

For example, asking for a protein's function sends the accession you named to
UniProt; asking for adverse event reports sends the drug name to openFDA. The
catalogue covers roughly 200 providers, among them UniProt, Open Targets,
PubMed and Europe PMC, openFDA, ChEMBL, Ensembl, ClinicalTrials.gov, the NCBI
services and Reactome. The provider for every tool is named in the tool's own
description and in its entry in the tool catalogue at
https://aiscientist.tools .

Data sent to a provider is governed by that provider's own privacy policy and
terms. ToolUniverse neither controls those services nor receives a copy of
what they return to you.

Some tools are opt-in hosted services that are only reached when you select
them explicitly — for example the `parallel`, `serpbase` and `firecrawl`
backends of `web_search`. Those tools state in their description that the
query is sent to a hosted third party, and the response carries a notice
saying so.

## Credentials

API keys are read from your environment, from a `.env` file you control, or
from the fields Claude Desktop collects for this extension, and they stay on
your machine. A key is sent only to the service it belongs to, as that
service's authentication header. Keys are never written to logs, never
included in tool results, and never transmitted to the ToolUniverse project.

## Storage and retention

Everything ToolUniverse stores is stored locally:

* cached tool results and search indexes under your user cache directory,
* an optional workspace directory (`.tooluniverse`) holding your settings,
* any `.env` file you create for credentials.

There is no server-side storage, so there is nothing for us to retain, export
or delete on your behalf. Deleting those local files removes the data. Removing
the extension removes the bundle and its virtual environment.

## Health and personal data

ToolUniverse queries biomedical databases, so a query you write can itself
contain sensitive information. Whatever you type into a tool argument is sent
to that tool's provider. Do not put patient-identifying information into tool
arguments. ToolUniverse is a research tool and is not intended for clinical
decision-making.

## Children

ToolUniverse is not directed at children and collects no data from anyone.

## Changes

Material changes to this policy are published in this file, which is versioned
in the public repository, and summarised in the release notes.

## Contact

* Issues and questions: https://github.com/mims-harvard/ToolUniverse/issues
* Email: shanghuagao@gmail.com
