---
name: tooluniverse-database-logins
description: Help the user add the login (API key) that a ToolUniverse tool needs for a database such as NCBI/PubMed, OMIM, DisGeNET, UMLS or OpenAlex, without the key ever passing through the chat. Explains which login unlocks what, where to get it, where to paste it, and retries the tool. Use when a tool says a login, API key or token is missing or rejected, or the user asks "which logins do I need", "add my OMIM key", or "why does this database need a key".
---

# Add a database login for ToolUniverse

Most ToolUniverse tools need no login. A few databases require the user's own free or licensed account. The person you are helping is usually a scientist, not a programmer: explain in plain words, one step at a time.

**Never ask the user to paste a key, token or password into the chat, and never put one in a file, command or message yourself.** Keys are typed only into the ToolUniverse website (hosted use) or the user's own local settings (local use).

## 1. Find out which login is needed

- If a tool failed, its error names the missing or rejected setting (for example `OMIM_API_KEY`). Use that exact name.
- If the user asks in general, ask what they want to do, and suggest only the logins that unlock it. Do not push them to collect every key.

Common ones:

| Login | Unlocks | Where to get it | Cost / wait |
|---|---|---|---|
| `NCBI_API_KEY` (+ `NCBI_EMAIL`) | Faster PubMed, Gene, Protein and other NCBI tools (they work without it, slower) | https://account.ncbi.nlm.nih.gov/settings/ → API Key Management | Free, ~2 minutes |
| `OMIM_API_KEY` | OMIM genetic-disorder, gene and phenotype tools | https://www.omim.org/api | Free for research; approval can take days |
| `DISGENET_API_KEY` | DisGeNET gene–disease associations | https://disgenet.com/signup/ | Account; API access depends on plan |
| `UMLS_API_KEY` | UMLS terminology and concept lookup | https://uts.nlm.nih.gov/uts/profile | Free UTS account and license |
| `OPENALEX_API_KEY` | OpenAlex papers, authors, institutions | https://openalex.org/settings/api | Free account |
| `SEMANTIC_SCHOLAR_API_KEY` | Higher Semantic Scholar limits | https://www.semanticscholar.org/product/api | Free, by request |
| `HF_TOKEN` | Hugging Face–hosted models and datasets | https://huggingface.co/settings/tokens | Free account |

The full list, with steps for each, is on https://connect.aiscientist.tools/credentials (search box). Before the user signs up for anything paid, metered, or requiring a license or an institutional claim, say so and let them decide.

## 2. Get the key (the user does this)

Give the link and the two or three clicks needed, from the table or the credentials page. Suggest the least access the site offers (read-only). If the key arrives by email, the user opens it themselves.

## 3. Save it where ToolUniverse can use it

**Hosted ToolUniverse** (the usual case: the assistant is connected to connect.aiscientist.tools):

1. Open https://connect.aiscientist.tools/credentials.
2. Find the database (search by name), paste the key into its box, click **Save key**.

It is stored encrypted and used only when a tool that needs it runs for this user. You never see it.

**Local ToolUniverse** (ToolUniverse runs on this computer, for example `uvx tooluniverse` or a Python install): the setting is an environment variable with the exact name, for example `OMIM_API_KEY`. Tell the user to add it to their own shell profile or the `.env` file their setup uses, in their editor; do not write the value yourself. Restart the assistant afterwards.

## 4. Check it works

Run the tool that needed it again with a small, public example (for OMIM, a well-known gene such as `BRCA1`). Then tell the user plainly which of these happened:

- It works: done.
- Still "missing": the key was saved under a different name, or the page was not saved. Check the exact name.
- "Rejected" or "unauthorized": the database did not accept the key (typo, not activated yet, or the account lacks API access). For OMIM and UMLS, approval can take days.
- A different error: the database may be down or rate-limiting. Try later; it is not the login.

Never show a tool output that contains the key. If one does, tell the user to replace the key on the provider's site and save the new one.
