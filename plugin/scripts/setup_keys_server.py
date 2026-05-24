#!/usr/bin/env python3
"""Localhost form for entering ToolUniverse API keys, saved to a .env file.

Usage: python setup_keys_server.py --target <path-to-.env> [--catalog <path>]
Binds 127.0.0.1 on a random port, opens the browser, writes on submit, exits.
"""
from __future__ import annotations

import argparse
import html
import json
import secrets
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import keys_env  # noqa: E402

_DOMAIN_ORDER = [
    "Genomics & Variants",
    "Drugs & Chemistry",
    "Proteins & Structure",
    "Literature & Patents",
    "Clinical & Safety",
    "Models & Infrastructure",
]

_FONT_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    "family=Hanken+Grotesk:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500"
    '&display=swap">'
)

# Plain (non-f) string: literal braces, no doubling needed.
_CSS = """
:root{
  --bg:#f5f6f8;--card:#fff;--ink:#181c22;--muted:#5c6672;--faint:#9aa3af;
  --line:#e6e9ef;--accent:#3457d5;--accent-2:#5a78ea;--accent-soft:rgba(52,87,213,.08);
  --ok:#159a55;--ok-soft:rgba(21,154,85,.1);--ring:rgba(52,87,213,.16);
  --shadow:0 1px 2px rgba(16,24,40,.04),0 8px 24px -12px rgba(16,24,40,.12);
  --shadow-lg:0 12px 40px -16px rgba(16,24,40,.22);
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:"Hanken Grotesk",ui-sans-serif,system-ui,sans-serif;font-size:15px;line-height:1.55;
  -webkit-font-smoothing:antialiased;
  background-image:
    radial-gradient(48rem 30rem at 88% -12%,rgba(90,120,234,.14),transparent 60%),
    radial-gradient(40rem 26rem at -8% -6%,rgba(52,87,213,.07),transparent 55%);
  background-attachment:fixed;}
code,.mono{font-family:"IBM Plex Mono",ui-monospace,monospace}
.wrap{max-width:980px;margin:0 auto;padding:clamp(2.2rem,5vw,4rem) clamp(1.1rem,4vw,2rem) 9rem}
.top{display:flex;gap:2rem;align-items:flex-end;justify-content:space-between;flex-wrap:wrap;margin-bottom:2.6rem}
.head-l{min-width:0;opacity:0;animation:rise .6s .04s forwards}
.kicker{font-family:"IBM Plex Mono",monospace;font-size:.72rem;font-weight:500;letter-spacing:.22em;color:var(--accent);margin-bottom:.9rem}
h1{font-size:clamp(2.1rem,5vw,3rem);font-weight:700;letter-spacing:-.025em;margin:0 0 .8rem;line-height:1.05}
.lede{max-width:54ch;color:var(--muted);margin:0;font-size:.95rem}
.lede code{color:var(--ink);background:#fff;border:1px solid var(--line);padding:.05em .4em;border-radius:5px;font-size:.85em}
.prog{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:1rem 1.2rem;box-shadow:var(--shadow);min-width:172px;opacity:0;animation:rise .6s .12s forwards}
.prog-n{display:flex;align-items:baseline;gap:.35rem}
.prog .big{font-size:1.85rem;font-weight:700;letter-spacing:-.02em}
.prog .tot{color:var(--faint);font-weight:500}
.meter{height:5px;background:var(--line);border-radius:5px;overflow:hidden;margin:.6rem 0 .45rem}
.meter-bar{height:100%;background:linear-gradient(90deg,var(--accent),var(--accent-2));border-radius:5px;transition:width .55s cubic-bezier(.2,.8,.2,1)}
.prog-l{font-size:.72rem;color:var(--muted);text-transform:uppercase;letter-spacing:.12em}
.sect{margin-top:2.3rem;opacity:0;animation:rise .6s forwards}
.sect:nth-of-type(1){animation-delay:.16s}.sect:nth-of-type(2){animation-delay:.22s}
.sect:nth-of-type(3){animation-delay:.28s}.sect:nth-of-type(4){animation-delay:.34s}
.sect:nth-of-type(5){animation-delay:.4s}.sect:nth-of-type(6){animation-delay:.46s}
.sect-h{display:flex;align-items:center;gap:.7rem;margin:0 .15rem 1rem}
.sect-h h2{font-size:1.02rem;font-weight:700;letter-spacing:-.01em;margin:0}
.sect-h .cnt{font-family:"IBM Plex Mono",monospace;font-size:.7rem;color:var(--faint);background:var(--card);border:1px solid var(--line);border-radius:99px;padding:.1rem .55rem}
.grid{display:grid;gap:.9rem;grid-template-columns:repeat(auto-fill,minmax(min(100%,340px),1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:1.05rem 1.1rem 1rem;box-shadow:var(--shadow);transition:.18s;display:flex;flex-direction:column}
.card:hover{box-shadow:var(--shadow-lg);transform:translateY(-2px)}
.card:focus-within{border-color:var(--accent)}
.card-h{display:flex;align-items:center;gap:.6rem;justify-content:space-between;margin-bottom:.55rem}
.card-h code{font-size:.84rem;font-weight:500;word-break:break-all}
.badge{font-family:"IBM Plex Mono",monospace;font-size:.61rem;text-transform:uppercase;letter-spacing:.08em;color:var(--faint);border:1px solid var(--line);border-radius:99px;padding:.16rem .5rem;white-space:nowrap;flex:none}
.badge.ok{color:var(--ok);background:var(--ok-soft);border-color:transparent}
.why{margin:0 0 .55rem;font-size:.875rem;opacity:.92}
.note{margin:0 0 .85rem;font-size:.79rem;color:var(--muted);padding-left:.7rem;border-left:2px solid var(--line)}
.field{position:relative;margin-top:auto}
.field input{width:100%;background:#fbfcfe;border:1px solid var(--line);border-radius:10px;color:var(--ink);
  font-family:"IBM Plex Mono",monospace;font-size:.82rem;padding:.6rem 3.4rem .6rem .75rem;outline:none;transition:.18s}
.field input::placeholder{color:var(--faint)}
.field input:focus{border-color:var(--accent);background:#fff;box-shadow:0 0 0 4px var(--ring)}
.eye{position:absolute;right:.35rem;top:50%;transform:translateY(-50%);background:transparent;border:0;color:var(--faint);
  font-family:"IBM Plex Mono",monospace;font-size:.61rem;letter-spacing:.06em;text-transform:uppercase;cursor:pointer;padding:.34rem .5rem;border-radius:7px}
.eye:hover{color:var(--accent);background:var(--accent-soft)}
.card-f{display:flex;align-items:center;justify-content:space-between;gap:.6rem;margin-top:.7rem}
.reg{font-size:.76rem;font-weight:500;color:var(--accent);text-decoration:none}
.reg:hover{text-decoration:underline}
.clear{display:inline-flex;align-items:center;gap:.35rem;font-size:.69rem;text-transform:uppercase;letter-spacing:.06em;color:var(--faint);cursor:pointer}
.clear input{accent-color:#d8584a;margin:0}
.bar{position:sticky;bottom:1rem;margin-top:2.6rem;display:flex;align-items:center;gap:1rem;flex-wrap:wrap;
  padding:.85rem 1.1rem;background:rgba(255,255,255,.86);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);
  border:1px solid var(--line);border-radius:16px;box-shadow:var(--shadow-lg)}
.bar-note{color:var(--muted);font-size:.82rem}
.save{margin-left:auto;font-family:"Hanken Grotesk",sans-serif;font-weight:600;font-size:.9rem;
  background:var(--accent);color:#fff;border:0;padding:.72rem 1.6rem;border-radius:11px;cursor:pointer;transition:.16s}
.save:hover{background:#2c49b8;transform:translateY(-1px);box-shadow:0 12px 26px -10px rgba(52,87,213,.5)}
.save:active{transform:translateY(0)}
.done{max-width:540px;margin:16vh auto 0;text-align:center;padding:0 1.5rem}
.check{width:64px;height:64px;border-radius:50%;display:grid;place-items:center;margin:0 auto 1.6rem;background:var(--ok-soft);color:var(--ok);font-size:1.7rem;animation:rise .5s}
.done h1{font-size:clamp(1.8rem,5vw,2.6rem);margin:0 0 .9rem}
.done h1 .accent{color:var(--accent)}
.done p{color:var(--muted);margin:.4rem 0}
.done code{color:var(--ink);background:#fff;border:1px solid var(--line);padding:.1em .45em;border-radius:6px;font-size:.85em;word-break:break-all}
@keyframes rise{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
@media (max-width:560px){.top{flex-direction:column;align-items:stretch}.prog{align-self:flex-start}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
"""

_JS = """
(function(){
  document.querySelectorAll('.eye').forEach(function(b){
    b.addEventListener('click',function(){
      var i=b.parentElement.querySelector('input');
      if(i.type==='password'){i.type='text';b.textContent='hide';}
      else{i.type='password';b.textContent='show';}
    });
  });
  var prog=document.querySelector('.prog');
  var bar=document.querySelector('.meter-bar');
  var big=document.querySelector('.prog .big');
  var total=parseInt((prog&&prog.getAttribute('data-total'))||'0',10);
  function recount(){
    var n=0;
    document.querySelectorAll('.card').forEach(function(c){
      var inp=c.querySelector('.field input');
      var clr=c.querySelector('input[type=checkbox]');
      var isSet=inp.getAttribute('data-set')==='1';
      var cleared=clr&&clr.checked;
      if(inp.value.trim()!==''||(isSet&&!cleared))n++;
    });
    if(big)big.textContent=n;
    if(bar)bar.style.width=(total?Math.round(n/total*100):0)+'%';
  }
  document.addEventListener('input',recount);
  document.addEventListener('change',recount);
})();
"""


def find_catalog(explicit) -> Path:
    """Locate api_keys_catalog.json: --catalog, then sibling, then repo."""
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    candidates.append(Path(__file__).resolve().parent / "api_keys_catalog.json")
    candidates.append(
        Path(__file__).resolve().parents[2]
        / "src" / "tooluniverse" / "data" / "api_keys_catalog.json"
    )
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError("api_keys_catalog.json not found; pass --catalog")


def check_token(expected, given) -> bool:
    return bool(given) and secrets.compare_digest(str(expected), str(given))


def compute_updates(form: dict, names: list) -> dict:
    """Build the .env update dict from a parsed POST form.

    Non-empty value -> set. clear__<NAME> present -> remove (""). Blank -> skip.
    """
    updates: dict = {}
    for name in names:
        if f"clear__{name}" in form:
            updates[name] = ""
            continue
        val = (form.get(name, [""])[0] or "").strip()
        if val:
            updates[name] = val
    return updates


def _domain_of(entry: dict) -> str:
    return entry.get("domain") or "Other"


def _card(entry: dict, existing: dict) -> str:
    name = entry["name"]
    cur = existing.get(name, "")
    is_set = bool(cur)
    if cur:
        placeholder = keys_env.mask(cur)
    elif entry.get("type") == "endpoint":
        placeholder = "https://…"
    else:
        placeholder = "Paste key…"
    set_attr = ' data-set="1"' if is_set else ""
    badge = (
        '<span class="badge ok">configured</span>'
        if is_set else '<span class="badge">not set</span>'
    )
    clear = (
        f'<label class="clear"><input type="checkbox" name="clear__{name}">remove</label>'
        if is_set else ""
    )
    return f"""
        <article class="card">
          <div class="card-h"><code>{html.escape(name)}</code>{badge}</div>
          <p class="why">{html.escape(entry.get('purpose', ''))}</p>
          <p class="note">{html.escape(entry.get('without', ''))}</p>
          <div class="field">
            <input type="password" name="{name}"{set_attr} placeholder="{html.escape(placeholder)}" autocomplete="off" spellcheck="false">
            <button type="button" class="eye" tabindex="-1" aria-label="Show value">show</button>
          </div>
          <div class="card-f">
            <a class="reg" href="{html.escape(entry['register_url'])}" target="_blank" rel="noopener">Get a key &#8599;</a>
            {clear}
          </div>
        </article>"""


def render_form(catalog: list, existing: dict, token: str) -> str:
    def section(domain, items):
        if not items:
            return ""
        cards = "".join(_card(e, existing) for e in items)
        return f"""
      <section class="sect">
        <div class="sect-h"><h2>{html.escape(domain)}</h2><span class="cnt">{len(items)}</span></div>
        <div class="grid">{cards}</div>
      </section>"""

    seen = dict.fromkeys(_domain_of(e) for e in catalog)
    domains = _DOMAIN_ORDER + [d for d in seen if d not in _DOMAIN_ORDER]
    total = len(catalog)
    done = sum(1 for e in catalog if existing.get(e["name"]))
    pct = round(done / total * 100) if total else 0
    body = "".join(
        section(d, [e for e in catalog if _domain_of(e) == d]) for d in domains
    )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ToolUniverse · API Keys</title>{_FONT_LINK}<style>{_CSS}</style></head>
<body>
<main class="wrap">
  <header class="top">
    <div class="head-l">
      <div class="kicker">TOOLUNIVERSE · API CONFIGURATION</div>
      <h1>Connect your data sources</h1>
      <p class="lede">Add keys only for the sources you use. Each is written to your local <code>.env</code> and read by every ToolUniverse tool. Leave a field blank to keep its current value.</p>
    </div>
    <aside class="prog" data-total="{total}">
      <div class="prog-n"><span class="big">{done}</span><span class="tot">/ {total}</span></div>
      <div class="meter"><div class="meter-bar" style="width:{pct}%"></div></div>
      <div class="prog-l">configured</div>
    </aside>
  </header>
  <form method="post" id="f">
    <input type="hidden" name="token" value="{html.escape(token)}">
    {body}
    <div class="bar">
      <span class="bar-note">Saved locally to your .env and never displayed again.</span>
      <button type="submit" class="save">Save keys</button>
    </div>
  </form>
</main>
<script>{_JS}</script>
</body></html>"""


def _success_page(count: int, target: Path) -> str:
    plural = "" if count == 1 else "s"
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Saved · ToolUniverse</title>{_FONT_LINK}<style>{_CSS}</style></head>
<body>
<div class="done"><div class="check">&#10003;</div>
<h1>Saved <span class="accent">{count}</span> key{plural}</h1>
<p>Written to <code>{html.escape(str(target))}</code></p>
<p>Restart the ToolUniverse MCP server or CLI to load the new keys — then you can close this tab.</p>
</div></body></html>"""


def build_server(catalog: list, target: Path, token: str):
    names = [e["name"] for e in catalog]
    state = {"saved": 0}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # silence
            pass

        def _send(self, code, body):
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

        def do_GET(self):
            q = parse_qs(urlparse(self.path).query)
            if not check_token(token, (q.get("token") or [None])[0]):
                self._send(403, "<h1>Forbidden</h1>")
                return
            existing = keys_env.read_env(target)
            self._send(200, render_form(catalog, existing, token))

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            form = parse_qs(self.rfile.read(length).decode("utf-8"))
            if not check_token(token, (form.get("token") or [None])[0]):
                self._send(403, "<h1>Forbidden</h1>")
                return
            updates = compute_updates(form, names)
            keys_env.merge_env(target, updates)
            state["saved"] = len([v for v in updates.values() if v != ""])
            self._send(200, _success_page(state["saved"], target))
            threading.Thread(target=self.server.shutdown, daemon=True).start()

    return HTTPServer(("127.0.0.1", 0), Handler), state


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, help="Path to the .env file to write")
    ap.add_argument("--catalog", default=None, help="Path to api_keys_catalog.json")
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args(argv)

    catalog = json.loads(find_catalog(args.catalog).read_text())
    token = secrets.token_urlsafe(16)
    target = Path(args.target).expanduser()
    server, state = build_server(catalog, target, token)
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}/?token={token}"
    print(f"Open this URL to enter your API keys:\n  {url}", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    server.serve_forever()
    print(f"Saved {state['saved']} key(s) to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
