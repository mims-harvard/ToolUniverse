---

name: tooluniverse-share-computer
description: "Share tools that live on this computer (the user's own Python function, script or notebook code, a model, a program they already run, or ToolUniverse's reviewed GPU models) so the user's and their colleagues' AI assistants can use them through ToolUniverse. You do the work; the user only answers questions and clicks Allow once in a browser. Use when the user says things like \"share my model with my lab\", \"let my colleague use this script\", \"make this function a tool\", \"put my GPU models on ToolUniverse\", or \"keep my tool running\"."
---

# Share a computer's tools through ToolUniverse

The person you are helping is usually a scientist, not a programmer. Do every technical step yourself. Ask them only what you cannot find out, in plain words, one question at a time. Never ask them to edit code, read logs, or type commands; never paste or ask for keys, tokens or passwords in the chat.

Nothing leaves their computer except what the chosen tool returns. ToolUniverse only relays calls to it; their files, data and passwords stay where they are, and only the tools they pick are reachable.

## 0. Check you can do this here

You must be able to run commands **on the computer that has the code or model** (Claude Code, Codex, or another agent with a terminal there). If you cannot (for example you are Claude in a browser), say so plainly and stop:

> Sharing has to be set up on the computer that has your model. Open Claude Code or Codex on that computer and ask it the same thing; it can use this guide too.

## 1. Find out what to share (ask, don't assume)

Work out, from the conversation or by looking around with their permission:

- **What**: a function or script they wrote, a notebook cell, a model they run, a program that already serves MCP, or one of ToolUniverse's reviewed models (run `tu remote list` after step 2 to see them: ESM, Boltz, scVI, Enformer, and others).
- **The one thing it should do**, as a sentence ("score a protein sequence", "look up a sample in our lab database"). Share narrow operations, not a whole program.
- **Inputs and output**: what a caller gives and gets back.
- **Name**: what colleagues should see, such as "Smith Lab GPU".

If the request is vague ("share my stuff"), ask which result they want colleagues to be able to get, then find the code that produces it.

## 2. Install ToolUniverse sharing (once per computer)

macOS or Linux:

~~~bash
curl -LsSf https://connect.aiscientist.tools/install.sh | sh
~~~

Windows (PowerShell):

~~~powershell
powershell -ExecutionPolicy ByPass -c "irm https://connect.aiscientist.tools/install.ps1 | iex"
~~~

It brings its own Python and puts `tu` and `tuplatform-service` on the PATH for new terminals. In the same shell, add `~/.local/bin` to PATH (or open a new shell), then confirm `tu --help` works. If the install fails, report the exact error to the user in one sentence and stop; do not improvise another installer.

Their own code may need its own packages (for example torch). Run the tool in the environment where their code already works: if they use conda or a virtualenv, install there instead with `python -m pip install "tooluniverse==1.5.5" "tuplatform-connect @ https://connect.aiscientist.tools/downloads/tuplatform_connect-0.4.2-py3-none-any.whl#sha256=e4e09af02093da3e739c9234e1f8182f8a9c311cd9fc0145a1dc119a296ef8ba"`.

## 3. Prepare what to share

Pick exactly one path.

### A. Their own Python code (most common)

Write a small new file next to their code, for example `share_tool.py`. Import their function; do not rewrite or move their code.

~~~python
from tooluniverse import remote_tool

from their_module import score_sequence  # their existing code


@remote_tool
def score_protein(sequence: str, threshold: float = 0.5) -> dict:
    """Score one protein sequence with the lab's model. Returns the score and whether it passes the threshold."""
    if not 1 <= len(sequence) <= 10_000:
        raise ValueError("sequence must be 1 to 10,000 letters")
    score = float(score_sequence(sequence))
    return {"score": score, "passes": score >= threshold}
~~~

Rules that keep it safe and usable:

- One decorated function per operation, with type hints and a docstring written for a scientist reading a tool list: it becomes the tool's description.
- Inputs are plain values (text, numbers, lists). Never accept a file path, a URL, SQL, a shell command, or a model name chosen by the caller.
- Check input sizes. Return small JSON-friendly results (numbers, text, short lists); never return secrets, local paths, raw model objects or huge arrays.
- Load models once at import time, not on every call.
- A database: write one function per fixed, read-only, parameterized query. Never pass caller text into SQL.

Test it before sharing: call the function directly with a realistic example (`python -c "from share_tool import score_protein; print(score_protein('MKT...'))"`), and show the user the result in plain words. If it fails, fix the wrapper, not their code; ask them if their own code is what fails.

### B. A program that already serves MCP

If they already run an MCP server (Streamable HTTP, for example `http://localhost:8080/mcp`), share it unchanged with `--forward` in step 4. Confirm it answers MCP `tools/list` first; a web page or REST API is not MCP, so wrap it as in path A instead.

### C. ToolUniverse's reviewed models

Run `tu remote list`, show the user the models in plain words, and agree which to offer. Each starts only when someone uses it and stops when idle. A GPU is recommended for most. For setup details or problems with one model, read its guide: the skill `setup-<name>-remote-tool` (for example `setup-esm-remote-tool`; over the hosted ToolUniverse connection use `get_skill`).

## 4. Share it (the user clicks Allow once)

Run one of these. It keeps running, so start it in the background and watch its output:

~~~bash
# A. own code
tu serve share_tool.py --share --name "Smith Lab GPU" --service https://tooluniverse-backend.onrender.com
# B. existing MCP program
tu serve --forward "http://localhost:8080" --share --name "Smith Lab Server" --service https://tooluniverse-backend.onrender.com
# C. reviewed models
tu serve --allow esm,boltz --share --name "Smith Lab GPU" --service https://tooluniverse-backend.onrender.com
~~~

The first time on a computer it prints:

~~~
Authorize this computer in your browser:
  https://connect.aiscientist.tools/activate?user_code=ABCD-EFGH
Code: ABCD-EFGH
Waiting for approval (Ctrl-C to cancel)...
~~~

Tell the user exactly this, with the real link and code:

> Open this link, sign in to ToolUniverse if asked, check that the code matches **ABCD-EFGH**, and click **Allow**: <link>

On a server without a browser, add `--no-browser`; the user can open the link on their laptop or phone. The computer keeps its own key in a private file after that; nobody copies a key. When it prints `Sharing through ToolUniverse Platform` (or `Sharing privately`), it is live.

## 5. Check that it really works

Do not report success from the command output alone.

- If you are connected to the hosted ToolUniverse (you have `list_remote_tools`), call `list_remote_tools` with the computer's name, then `run_remote_tool` once with the same example you tested in step 3. Compare the answer with the local result.
- Otherwise ask the user to open https://connect.aiscientist.tools/remote-servers and confirm the computer shows as online with the expected tools.

## 6. Keep it running (ask first)

`tu serve` stops when the terminal closes. If the user wants it always available, ask before installing a background service, then run the same arguments with `tuplatform-service install` instead of `tu serve ... --share`, for example:

~~~bash
tuplatform-service install --tool-file share_tool.py --name "Smith Lab GPU" --service https://tooluniverse-backend.onrender.com
~~~

It survives logouts and reboots. Check it with `tuplatform-service status --name "Smith Lab GPU"`. Tell the user how to stop it later: ask you, or run `tuplatform-service uninstall --name "Smith Lab GPU"` (the same name).

## 7. Let colleagues use it

Explain the two choices in plain words and let the user pick:

- **Specific colleagues use this computer's tools**: on https://connect.aiscientist.tools/remote-servers, the computer's card has **Create share code**. The user copies the code (or **Copy invitation**) and sends it. A colleague pastes it on their ToolUniverse Home page, and their AI assistant can then use these tools. The user can turn the code off at any time.
- **Anyone can find one tool in Discover**: publish a single tool. Use the skill `tooluniverse-publish-tool`.

## Stopping and undoing

- Stop sharing now: stop the `tu serve` process (Ctrl-C), or `tuplatform-service uninstall --name "<name>"` for the background service.
- Sign this computer out of ToolUniverse and revoke its key: `tu remote logout --revoke`.
- The computer's record stays on the Computers page as offline; the user can delete it there.

## When something goes wrong

Say what happened in one plain sentence and what you will try next. Common cases:

- `tu: command not found`: PATH was not refreshed; use `~/.local/bin/tu` or a new shell.
- The approval link expired: `tu serve` prints a new one by itself; pass it on.
- The computer stays offline: the process stopped or the network blocks outbound HTTPS; restart it and read its last lines.
- The tool fails only through ToolUniverse: run the same input locally; a difference usually means a path, environment variable or working directory that exists only in the user's terminal.
- A model needs a GPU that is not there: say so; do not silently fall back to something else.
