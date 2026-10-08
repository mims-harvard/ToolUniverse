---
name: tooluniverse-publish-tool
description: Help the user publish one tool from their shared computer to ToolUniverse so other scientists' AI assistants can find and run it, choosing whether only they, specific colleagues, or everyone can use it. Guides the website steps in plain words and checks the result. Use when the user says "publish my tool", "put my model in Discover", "let anyone use this tool", "let only my collaborators use this tool", or "unpublish my tool".
---

# Publish one tool to ToolUniverse

Publishing puts **one** tool from a computer the user already shares into ToolUniverse, with a page in Discover if they make it public. People can run that one tool; they cannot see the computer's other tools or anything else on it.

The person you are helping is usually a scientist, not a programmer. The publishing steps happen on the website, where only the user can click, so walk them through it one step at a time and check each result yourself where you can. Never ask for passwords, keys or tokens in the chat.

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

## 3. Walk them through the website

Give these steps one or two at a time, and wait for the user:

1. Open https://connect.aiscientist.tools/my-tools?create=1 (sign in if asked). The **Publish a tool** window opens.
2. Under the computer's name, click the tool to publish.
3. Improve what people will read: a clear name, one or two sentences on **What does it do?**, a realistic **Sample question**, and search keywords. Offer to write these for them from what you know about the tool; they paste your text.
4. Click **Save & test**. In **Test input (JSON)**, use a small realistic example; you can write it for them, matching the tool's inputs. Click **Run test**.
5. When the test passes, click **Publish**.
6. Set who may use it: on the tool's card in **My tools**, click **Access** and pick **Only me**, **Specific people** (then add each colleague's account email) or **Public**.

If the test fails, read the error the page shows and fix the cause on the computer (usually the tool itself, or the computer went offline), then **Test again**. Do not ask the user to publish a tool that has not passed.

## 4. Check it worked

- **Public**: the tool should appear in https://connect.aiscientist.tools/discover (Tools view, "Shared by scientists"). If you have `list_remote_tools`, search for it by name and run it once with the same example.
- **Specific people**: tell the user to send colleagues the tool's page link; colleagues must sign in with the email that was added.
- **Only me**: call it once through `list_remote_tools` / `run_remote_tool` if you can.

Explain that the tool only works while the computer is on and sharing. Offer to keep it running with a background service (`tooluniverse-share-computer`, step 6).

## Changing or removing it later

- Change who may use it: **Access** on the tool's card in **My tools**.
- Stop it for now: **Unpublish** on the card. Delete it from the card when no longer needed.
- After changing the tool's inputs on the computer, open the tool in My tools and test again before people use it.
