# Reporting a ToolUniverse Issue

Use this when the user is stuck and the Common Issues table hasn't resolved the problem.

## Agent: Compose the Issue Body

You have all the context from the conversation. Fill in the template below — do not ask the user to run any commands.

```
Title: [one-line summary, e.g. "Trae: tooluniverse MCP server not appearing after restart"]

**Client**: [Cursor / Trae / Claude Desktop / VS Code / Windsurf / etc.]
**OS**: [Windows 11 / macOS 14 / Ubuntu 22.04 — be specific]
**uv version**: [from Step 1 output earlier, or "unknown"]
**ToolUniverse version**: [from `uvx tooluniverse --version` output, or "unknown"]

**What I did**
1. [first step the user took]
2. [second step]
3. [etc.]

**Error message**
```
[paste the exact error text here, or write "no error shown — server just doesn't appear"]
```

**What I expected**
[e.g. "tooluniverse to appear in the MCP servers list after restarting the app"]

**What was already tried**
- [fix 1 attempted and result]
- [fix 2 attempted and result]
```

Once composed, output the filled issue body and then give the user the walkthrough below.

---

## Walk the User Through GitHub

Say this to the user (adapt the language to match how they've been communicating):

> "I've prepared the issue report below — you just need to copy and paste it. Here's how to submit it, step by step:
>
> **Step 1.** Open this link in your browser:
> https://github.com/mims-harvard/ToolUniverse/issues/new
>
> **Step 2.** Sign in to GitHub. If you don't have an account, click **"Sign up"** — it's free and takes about a minute (no credit card needed). You can also sign up with Google.
>
> **Step 3.** You'll see a form with two fields:
> - **Title** — paste the one-line title from the report I prepared
> - **Leave a comment** (the large text box) — paste the full report body
>
> **Step 4.** Scroll down and click the green **"Submit new issue"** button.
>
> That's it! The team usually replies within 1–2 days. You'll get an email notification when they respond — no need to check back manually."

---

## Email Fallback

If the user is not comfortable with GitHub or can't create an account, they can send the same issue body by email:

**shanghuagao@gmail.com**

Subject line: `ToolUniverse setup issue: [one-line summary]`
