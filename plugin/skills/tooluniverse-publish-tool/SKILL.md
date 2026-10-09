---
name: tooluniverse-publish-tool
description: Help the user publish one tool from their shared computer to ToolUniverse so other scientists' AI assistants can find and run it, choosing whether only they, specific colleagues, or everyone can use it. Prepares and tests the tool for them; the user makes the final Publish click. Use when the user says "publish my tool", "put my model in Discover", "let anyone use this tool", "let only my collaborators use this tool", or "unpublish my tool".
---

# Publish one tool to ToolUniverse

Publishing puts **one** tool from a computer the user already shares into ToolUniverse, with a page in Discover if they make it public. People can run that one tool; they cannot see the computer's other tools or anything else on it.

The person you are helping is usually a scientist, not a programmer. You do the preparation; the final choice of who can use it, and the Publish click, are the user's on the website. Never ask for passwords, keys or tokens in the chat.

## 1. Make sure the tool is shared first

Publishing needs the tool to be running on a computer connected to ToolUniverse.

- If you are connected to the hosted ToolUniverse (you have `list_remote_tools`), call it and look for the user's computer ("your computer ...") and the tool.
- Otherwise ask the user whether https://connect.aiscientist.tools/remote-servers shows the computer **online** with the tool listed.

If it is not shared yet, do that first with the skill `tooluniverse-share-computer`, then come back.

## 2. Decide who may use it

Ask in plain words and explain the choice:

- **Only me**: a private tool for their own assistant. Not listed anywhere.
- **Specific people**: only colleagues they add by their ToolUniverse account email.
- **Public**: listed in Discover; anyone signed in to ToolUniverse can run it. Confirm the user has the right to share the model, data and results with everyone, and that the computer can handle the load, before choosing this.

To give a few colleagues **every** tool on that computer instead of one tool, publishing is not needed: use a share code (see `tooluniverse-share-computer`, step 7).

## 3. Prepare it, then let the user publish

**If you have the `prepare_tool_publication` tool** (the hosted ToolUniverse connection), do the preparation yourself:

1. Write a clear title, one or two sentences on what it does (what goes in, what comes out), and a few search keywords, from what you know about the tool. Show them to the user and adjust.
2. Pick a small, realistic test input that matches the tool's inputs (see `list_remote_tools` for its input schema).
3. Call `prepare_tool_publication` with `computer` (its name as `list_remote_tools` shows it), `tool`, `name`, `description`, `keywords` and `test_arguments`. It creates (or reuses) the private draft and runs a real test call.
4. If `test_passed` is false, read `test_error`, fix the cause on the computer (the tool itself, or the computer went offline) and call it again.
5. When it passes, give the user the `review_link` and say exactly this: open it, choose who can use it (**Choose who can use it**: Only me, Specific people with their account emails, or Public), then click **Publish**. You cannot publish for them: that choice is theirs, on purpose.

**Without that tool**, walk them through the website one or two steps at a time:

1. Open https://connect.aiscientist.tools/my-tools?create=1 (sign in if asked). The **Publish a tool** window opens.
2. Under the computer's name, click the tool to publish.
3. Fill in a clear name, **What does it do?**, a **Sample question** and search keywords; offer to write them, and they paste your text.
4. Click **Save & test**. In **Test input (JSON)**, use a small realistic example (you can write it). Click **Run test**.
5. When the test passes, click **Publish**.
6. Set who may use it: on the tool's card in **My tools**, click **Access** and pick **Only me**, **Specific people** (then add each colleague's account email) or **Public**.

If a test fails, fix the cause on the computer, then test again. Do not ask the user to publish a tool that has not passed.

## 4. Check it worked

- **Public**: the tool should appear in https://connect.aiscientist.tools/discover (Tools view, "Shared by scientists"). If you have `list_remote_tools`, search for it by name and run it once with the same example.
- **Specific people**: tell the user to send colleagues the tool's page link; colleagues must sign in with the email that was added.
- **Only me**: call it once through `list_remote_tools` / `run_remote_tool` if you can.

Explain that the tool only works while the computer is on and sharing. Offer to keep it running with a background service (`tooluniverse-share-computer`, step 6).

## Changing or removing it later

- Change who may use it: **Access** on the tool's card in **My tools**.
- Stop it for now: **Unpublish** on the card. Delete it from the card when no longer needed.
- After changing the tool's inputs on the computer, open the tool in My tools and test again before people use it.
