---

name: tooluniverse-use-shared-computer
description: "Use tools that run on a colleague's computer (for example models on their lab GPU) or tools other scientists published, through ToolUniverse. Covers redeeming a share code that starts with TU-SHARE-, finding the tools, and running them. Use when the user has a TU-SHARE- code or an invitation, says \"use my colleague's model\", \"run the tool on the lab GPU\", or asks what shared or community tools are available."
---

# Use a colleague's computer or a published tool

Colleagues can share the tools on their computer, and scientists can publish single tools to ToolUniverse. The tools run on their computer; nothing runs on the user's. The person you are helping is usually a scientist: keep it plain.

## 1. Join with a share code (once per computer)

A colleague sends a code that starts with `TU-SHARE-` (sometimes inside an invitation message). The user redeems it once:

1. Open https://connect.aiscientist.tools/dashboard (sign in if asked).
2. Paste the code into **Use a colleague's computer** and click **Join**.

The code is the colleague's to give; do not post it anywhere else. If the page says the code is invalid or expired, ask the colleague for a new one.

If ToolUniverse runs locally on this computer instead of the hosted service, the same code works with `tu connect TU-SHARE-...`.

## 2. Find the tools

With the hosted ToolUniverse connection:

- Call `list_remote_tools` (optionally with words from the task, such as "protein" or the computer's name). It lists tools on the user's own computers, computers they joined, and published tools, each with an id, a description, its inputs and whether its computer is online.
- Published tools can also be browsed at https://connect.aiscientist.tools/discover ("Shared by scientists").

Pick the tool that fits the task; tell the user which one and from whose computer.

## 3. Run them

Call `run_remote_tool` with the tool's `id` and `arguments` that match its input schema.

- A model can take minutes. Tell the user it is running on the colleague's computer.
- If the computer is offline, say so plainly: the colleague's computer must be on and sharing. Do not substitute a different tool silently.
- If a call reports that it may already have run, do not repeat it automatically; ask the user.
- Results come from the colleague's model or data; mention that when you report them.

## Leaving

The user can leave a shared computer on https://connect.aiscientist.tools/remote-servers: its card has **Stop using**. The owner can also turn the code off at any time.
