---
name: tooluniverse-connect
description: "How to use ToolUniverse Connect (connect.aiscientist.tools), the hosted ToolUniverse service, and when to use it instead of ToolUniverse installed on this computer. Use when the user asks how to use ToolUniverse or ToolUniverse Connect, how to connect Claude, Claude Code or Codex, whether to use the hosted service or a local install, why a tool says a login or API key is missing and where to add it, how to share a model or script with colleagues, how to use a colleague's computer or a TU-SHARE code, how to publish a tool, or when ToolUniverse tools are missing, signed out or not connecting."
---

# ToolUniverse Connect: what each part is for and how to use it

The person you are helping is usually a scientist, not a programmer. Answer in plain words, one step at a time. When you can do a step yourself (run a command, call a tool), do it; ask the user only for what only they can do, such as signing in or clicking **Allow**.

**Never ask the user to paste a key, token or password into the chat, and never write one into a file or command yourself.**

## 1. Find out which ToolUniverse this user has

| What you see | The user is on |
|---|---|
| ToolUniverse tools such as `what_can_i_use`, `list_skills` or `get_skill`, from the server `https://mcp.aiscientist.tools` (earlier setups: `https://tooluniverse-backend.onrender.com/mcp`, which still works) | **ToolUniverse Connect** (hosted) |
| A ToolUniverse server started on this computer (`uvx tooluniverse`, `tu serve`), the `tu` command, or Python `from tooluniverse import ToolUniverse` | **Local ToolUniverse** |
| No ToolUniverse tools at all | **Not connected yet** |

To check from a terminal: `claude mcp list` (Claude Code) or `codex mcp list` (Codex). In Claude (claude.ai or the desktop app), a connector must also be switched on in each chat; see section 3.

## 2. Hosted or local: which one to suggest

| | ToolUniverse Connect (hosted) | Local ToolUniverse |
|---|---|---|
| Setup | Nothing to install: add one address to the AI app and sign in once in the browser | Install `uv`, run `uvx tooluniverse`, edit the AI app's settings |
| Database logins (API keys) | Saved once on the website, encrypted, and used in every connected app | Set as environment variables, separately in each app's settings |
| Tools | Most ToolUniverse tools. Tools that read or write files on a computer or run code are not offered | All tools, including file and code tools |
| Share tools with colleagues, use a colleague's GPU computer, publish a tool | Yes | No |
| Where requests go | Through the ToolUniverse Connect servers, then to each database | Straight from this computer to each database |

Suggest **Connect** for most scientists, especially anyone who does not use a terminal or works in claude.ai. Suggest **local** when they need the file or code tools, or their requests must not leave their computer. They can have both.

## 3. Connect an AI app to ToolUniverse Connect

The user needs a free account: https://connect.aiscientist.tools/register. Its **Your AI scientist** page (https://connect.aiscientist.tools/connect-agent) shows these steps for each app.

Two addresses, so the user is not confused: **connect.aiscientist.tools** is the website people use (account, database logins, computers, publishing). **mcp.aiscientist.tools** is only the connection address that goes into the AI app; people paste it once and never need to open it. If they do open it in a browser, it leads to the website.

- **Claude (claude.ai or the desktop app):** **Customize → Connectors**, click **+ Add**, then **Add custom connector**. Name it ToolUniverse, URL `https://mcp.aiscientist.tools`. Sign in and click **Allow**. In each new chat, click **+** under the message box, choose **Connectors** and make sure ToolUniverse is switched on.
- **Claude Code:** run
  `claude mcp add --transport http --scope user tooluniverse "https://mcp.aiscientist.tools" && curl -fsSL https://connect.aiscientist.tools/skills.sh | sh -s -- claude-code && claude mcp login tooluniverse`
  A browser page opens; the user signs in and clicks **Allow**. Then start a new Claude Code session.
- **Codex:** run
  `codex mcp add tooluniverse --url "https://mcp.aiscientist.tools" && curl -fsSL https://connect.aiscientist.tools/skills.sh | sh -s -- codex`
  It starts the browser sign-in; if no page opens, run `codex mcp login tooluniverse`. Then start a new Codex session.

The `skills.sh` part installs a few small guides like this one so the AI scientist knows when to read ToolUniverse's guides. There is no key to copy. Once added, Claude Code and Codex use ToolUniverse in every session; Claude needs the connector switched on per chat.

## 4. After connecting: what can this user use?

Call `what_can_i_use`. It answers from the user's own account: which tools are ready, which database logins would unlock more (with the link to add each), the guides, and computers shared with them. Then tell them in a few sentences what they can do now and offer to run a first question. The same overview is on the website's **Home** page.

## 5. A tool says a login (API key) is missing or rejected

Most tools need no login. A few databases (for example OMIM, DisGeNET, UMLS) need the user's own account, and a few others (for example NCBI) work without one but faster with one.

- **On Connect:** the tool's message names the login and gives a link such as `https://connect.aiscientist.tools/credentials?key=OMIM_API_KEY`. Give the user that link. The page (**Database logins**) says where to get the key; the user pastes it there and clicks **Save key**. Then run the same tool again. For the full walk-through, including what to do when a key is rejected, call `get_skill` with `tooluniverse-database-logins` and follow it.
- **On local ToolUniverse:** the login is an environment variable with the exact name from the message (for example `OMIM_API_KEY`). The user adds it themselves to the `env` block of their AI app's ToolUniverse settings, or to their shell profile or `.env` file, then restarts the app. If this is a struggle, suggest Connect, where logins are saved once on a web page.

Some licensed databases take days to approve a key (OMIM, UMLS). Before the user signs up for anything paid or that needs a license, say so and let them decide.

## 6. Sharing, using shared computers, publishing (Connect only)

Each has a step-by-step guide on Connect. Call `get_skill` with the name and follow it, doing the steps yourself:

| The user wants to | Guide | Website page |
|---|---|---|
| Let colleagues' AI scientists use a model, script or program on their own computer | `tooluniverse-share-computer` | **Computers** |
| Use a colleague's computer, or redeem a code starting with `TU-SHARE-` | `tooluniverse-use-shared-computer` | **Computers** |
| Publish one tool so others can find it in Discover | `tooluniverse-publish-tool` | **My tools** |

For a research task that needs several databases (drug safety, variant interpretation, target validation and similar), call `list_skills` with a few words from the task and follow the matching guide.

## 7. When something goes wrong

- **No ToolUniverse tools in this chat:** the app is not connected, or in Claude the connector is off for this chat. Follow section 3.
- **Asked to sign in again, or "unauthorized":** Claude Code: `claude mcp login tooluniverse`. Codex: `codex mcp login tooluniverse`. Claude: **Customize → Connectors**, open ToolUniverse and connect again. A password reset signs out every connected app on purpose, so each app must be connected again after one.
- **"Starting" or "unavailable" right after an update:** the service is restarting. Wait a minute and try again. Live status: https://connect.aiscientist.tools/status.
- **A database error, timeout or "rate limited":** the database itself is busy or down; it is not a login problem. Try again later or use another tool for the same question.

Do not take setup steps for Connect from web search results: they usually describe a local install (for example a `~/.tooluniverse/.env` file) and do not apply to the hosted service.

Privacy, in one line if asked: the user's conversation stays with their AI app's provider; Connect receives only the tool requests the AI app sends. Details: https://connect.aiscientist.tools/privacy.
