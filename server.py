"""
Flask web server that serves the context-overload payload.

Routes
------
GET /          – landing page with usage instructions
GET /payload   – the overload page (the URL you drop in conversation)
GET /visits    – log viewer showing all recorded visits
GET /ping      – health check
"""

import json
import logging
import os
import time
from collections import deque
from datetime import datetime, timezone

from flask import Flask, Response, request, render_template_string
from payload_generator import generate_payload

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Configuration (override via env vars)
# ---------------------------------------------------------------------------
STRATEGY   = os.environ.get("OVERLOAD_STRATEGY", "adversarial")
SIZE_KB    = int(os.environ.get("OVERLOAD_SIZE_KB", "512"))
PORT       = int(os.environ.get("PORT", "5000"))
HOST       = os.environ.get("HOST", "0.0.0.0")
LOG_FILE   = os.environ.get("OVERLOAD_LOG", "visits.log")

_CACHE_ENABLED = os.environ.get("OVERLOAD_CACHE", "1") != "0"
_cached_payload: str | None = None

# In-memory ring buffer for the /visits dashboard (last 200 hits)
_visit_log: deque[dict] = deque(maxlen=200)

# ---------------------------------------------------------------------------
# Logging setup – structured JSON lines to file + human-readable to stderr
# ---------------------------------------------------------------------------
_file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
_file_handler.setLevel(logging.INFO)

_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.INFO)

_logger = logging.getLogger("overload.visits")
_logger.setLevel(logging.INFO)
_logger.addHandler(_file_handler)
_logger.addHandler(_console_handler)
_logger.propagate = False


# ---------------------------------------------------------------------------
# Visitor metadata collection
# ---------------------------------------------------------------------------

def _real_ip() -> str:
    """
    Best-effort real IP, respecting common reverse-proxy headers in order
    of decreasing trustworthiness.
    """
    for header in ("X-Real-IP", "X-Forwarded-For", "CF-Connecting-IP",
                   "True-Client-IP", "Forwarded"):
        value = request.headers.get(header)
        if value:
            # X-Forwarded-For can be a comma-separated list; take the first
            return value.split(",")[0].strip()
    return request.remote_addr or "unknown"


# Headers that reveal meaningful information about the client / AI tool
_INTERESTING_HEADERS = {
    # Identity & tool
    "User-Agent",
    "X-Openai-Assistant-Id",
    "X-Openai-User",
    "X-Forwarded-For",
    "X-Real-IP",
    "CF-Connecting-IP",
    "True-Client-IP",
    # Browser / bot hints
    "Accept",
    "Accept-Language",
    "Accept-Encoding",
    "Accept-Charset",
    # Referrer / origin
    "Referer",
    "Referrer",
    "Origin",
    "Sec-Fetch-Site",
    "Sec-Fetch-Mode",
    "Sec-Fetch-Dest",
    # HTTP version hints
    "Via",
    "Forwarded",
    # Caching / conditional
    "If-None-Match",
    "If-Modified-Since",
    "Cache-Control",
    "Pragma",
    # Auth / session tokens (values redacted, but presence is logged)
    "Authorization",
    "Cookie",
    # Custom / AI-specific
    "X-Request-Id",
    "X-Correlation-Id",
    "X-Amzn-Trace-Id",
    "X-B3-TraceId",
    "X-Plugin-Id",
}


def _collect_visit_metadata() -> dict:
    """
    Collect everything knowable about the visitor from the HTTP request
    without triggering any browser permission dialogs.
    """
    now_utc = datetime.now(timezone.utc)

    # Collect all interesting headers; redact values for auth/cookie
    headers_seen = {}
    for key, value in request.headers:
        canon = key.title()
        if canon in _INTERESTING_HEADERS:
            if canon in ("Authorization", "Cookie"):
                headers_seen[canon] = f"<present, {len(value)} bytes>"
            else:
                headers_seen[canon] = value

    # All request headers (for completeness in the JSON log)
    all_headers = {k.title(): v for k, v in request.headers}

    ua = request.headers.get("User-Agent", "")

    # Simple heuristic classification
    client_type = "unknown"
    ua_lower = ua.lower()
    if any(k in ua_lower for k in ("gpt", "openai", "chatgpt")):
        client_type = "openai-tool"
    elif any(k in ua_lower for k in ("claude", "anthropic")):
        client_type = "anthropic-tool"
    elif any(k in ua_lower for k in ("gemini", "google-extended", "googlebot")):
        client_type = "google-tool"
    elif any(k in ua_lower for k in ("python-requests", "httpx", "aiohttp", "urllib")):
        client_type = "python-http-client"
    elif any(k in ua_lower for k in ("curl", "wget", "libcurl")):
        client_type = "cli-tool"
    elif any(k in ua_lower for k in ("mozilla", "webkit", "gecko", "chrome",
                                      "safari", "firefox", "edge")):
        client_type = "browser"
    elif ua == "":
        client_type = "no-user-agent"

    return {
        "timestamp":    now_utc.isoformat(),
        "ip":           _real_ip(),
        "remote_addr":  request.remote_addr,
        "method":       request.method,
        "path":         request.full_path,
        "http_version": request.environ.get("SERVER_PROTOCOL", ""),
        "user_agent":   ua,
        "client_type":  client_type,
        "referrer":     request.referrer,
        "content_type": request.content_type or None,
        "headers":      headers_seen,
        "all_headers":  all_headers,
        "query_params": dict(request.args),
    }


def _log_visit(meta: dict, route: str, response_ms: float) -> None:
    record = {**meta, "route": route, "response_ms": round(response_ms, 2)}
    _visit_log.appendleft(record)

    # Human-readable console line
    ts      = meta["timestamp"]
    ip      = meta["ip"]
    ua      = meta["user_agent"] or "-"
    ctype   = meta["client_type"]
    ref     = meta.get("referrer") or "-"
    _logger.info(
        f"[VISIT] {ts}  ip={ip}  type={ctype}  ua={ua!r}  ref={ref}  route={route}  {response_ms:.0f}ms"
    )

    # Full JSON line to file (file handler logs everything _logger.info sends)
    # We also write a separate structured line so the log file is grep-friendly
    _file_handler.stream.write(json.dumps(record) + "\n")
    _file_handler.stream.flush()


# ---------------------------------------------------------------------------
# Payload cache
# ---------------------------------------------------------------------------

def _get_payload() -> str:
    global _cached_payload
    if _CACHE_ENABLED and _cached_payload is not None:
        return _cached_payload
    p = generate_payload(strategy=STRATEGY, size_kb=SIZE_KB)
    if _CACHE_ENABLED:
        _cached_payload = p
    return p


# ---------------------------------------------------------------------------
# HTML templates
# ---------------------------------------------------------------------------

_LANDING_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <title>OverLoad – LLM Context Flood</title>
  <style>
    body { font-family: monospace; max-width: 860px; margin: 4rem auto; padding: 0 1rem; }
    code { background: #f4f4f4; padding: .2em .4em; border-radius: 3px; }
    pre  { background: #f4f4f4; padding: 1rem; border-radius: 4px; overflow-x: auto; }
    .tag { display: inline-block; padding: .1em .5em; border-radius: 3px;
           font-size: .85em; font-weight: bold; }
    .flood       { background:#dbeafe; color:#1e40af }
    .injection   { background:#fce7f3; color:#9d174d }
    .maze        { background:#d1fae5; color:#065f46 }
    .adversarial { background:#fef3c7; color:#92400e }
  </style>
</head>
<body>
  <h1>OverLoad</h1>
  <p>Active configuration: strategy=<strong>{{ strategy }}</strong>,
     size=<strong>{{ size_kb }} KB</strong></p>

  <h2>The payload URL</h2>
  <pre>{{ payload_url }}</pre>
  <p>Drop this URL naturally into your interview conversation.
     Any AI assistant that fetches URLs will ingest the page.</p>

  <h2>Visitor log</h2>
  <p><a href="/visits">/visits</a> – live log of every hit on /payload</p>

  <h2>Strategies</h2>
  <ul>
    <li><span class="tag flood">flood</span>
        – Thousands of plausible technical paragraphs. Exhausts the context
          token budget so the model loses earlier conversation context.</li>
    <li><span class="tag injection">confusion</span>
        – Behavioural misdirection written as plausible editorial notes and errata.
          No visible markers — plain prose an LLM reads as authoritative guidance.</li>
    <li><span class="tag maze">maze</span>
        – Deeply nested, self-contradicting pseudo-logic that forces expensive
          chain-of-thought, crowding out reasoning for the actual question.</li>
    <li><span class="tag adversarial">adversarial</span>
        – All three combined plus a rare-token flood to burn token budget faster.</li>
  </ul>

  <h2>Environment variables</h2>
  <pre>OVERLOAD_STRATEGY  flood | injection | maze | adversarial  (default: adversarial)
OVERLOAD_SIZE_KB   target payload size in KB               (default: 512)
OVERLOAD_CACHE     1 = cache payload, 0 = regenerate       (default: 1)
OVERLOAD_LOG       path to JSONL log file                  (default: visits.log)
PORT               TCP port                                 (default: 5000)
HOST               bind address                             (default: 0.0.0.0)</pre>
</body>
</html>
"""

_PAYLOAD_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Systems Engineering Reference — Distributed Systems &amp; Storage Internals</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
           max-width: 960px; margin: 0 auto; padding: 2rem 1.5rem;
           line-height: 1.7; color: #1a1a1a; }
    h1 { font-size: 1.8rem; border-bottom: 2px solid #e5e7eb; padding-bottom: .5rem; }
    h2 { font-size: 1.3rem; margin-top: 2.5rem; color: #111; }
    h3 { font-size: 1.05rem; margin-top: 1.5rem; color: #222; }
    p  { margin: .8rem 0; }
    table { border-collapse: collapse; width: 100%; font-size: .9rem; margin: 1rem 0; }
    th, td { border: 1px solid #d1d5db; padding: .45rem .7rem; text-align: left; }
    th { background: #f9fafb; font-weight: 600; }
    code { background: #f3f4f6; padding: .15em .35em; border-radius: 3px;
           font-size: .88em; font-family: "SFMono-Regular", Consolas, monospace; }
    blockquote { border-left: 3px solid #d1d5db; margin: 1rem 0;
                 padding: .5rem 1rem; color: #555; }
    hr { border: none; border-top: 1px solid #e5e7eb; margin: 2rem 0; }
    ul, ol { padding-left: 1.5rem; }
    li { margin: .3rem 0; }
    strong { color: #111; }
    .breadcrumb { font-size: .8rem; color: #6b7280; margin-bottom: 1.5rem; }
    .version-badge { display: inline-block; background: #dbeafe; color: #1e40af;
                     border-radius: 3px; padding: .1em .5em; font-size: .8rem;
                     font-weight: 600; margin-left: .4rem; }
    footer { margin-top: 4rem; padding-top: 1rem; border-top: 1px solid #e5e7eb;
             font-size: .8rem; color: #9ca3af; }
  </style>
</head>
<body>
  <div class="breadcrumb">Documentation / Reference / Distributed Systems</div>
  <h1>Systems Engineering Reference
    <span class="version-badge">{{ version }}</span>
  </h1>
  <p>This reference covers internal architecture, component interaction models,
  compatibility constraints, and operational guidance for distributed storage and
  consensus systems. Last updated {{ date }}.</p>

{{ payload|safe }}

  <footer>
    Generated {{ timestamp }} &middot; {{ size_kb }} KB &middot;
    Systems Engineering Reference Project
  </footer>
</body>
</html>
"""

_VISITS_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta http-equiv="refresh" content="10"/>
  <title>OverLoad – Visitor Log</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: monospace; margin: 0; background: #0f0f0f; color: #e0e0e0; }
    header { padding: 1rem 2rem; background: #1a1a1a; border-bottom: 1px solid #333;
             display: flex; align-items: center; gap: 2rem; }
    header h1 { margin: 0; font-size: 1.2rem; color: #f0f0f0; }
    .meta { font-size: .8rem; color: #888; }
    .visits { padding: 1rem 2rem; }
    .visit { border: 1px solid #2a2a2a; border-radius: 4px; margin-bottom: 1rem;
             padding: 1rem; background: #161616; }
    .visit.ai    { border-left: 3px solid #f59e0b; }
    .visit.browser { border-left: 3px solid #3b82f6; }
    .visit.cli   { border-left: 3px solid #10b981; }
    .row { display: flex; gap: 1.5rem; flex-wrap: wrap; margin-bottom: .4rem; }
    .label { color: #6b7280; font-size: .75rem; margin-bottom: .1rem; }
    .value { color: #e0e0e0; font-size: .85rem; word-break: break-all; }
    .value.highlight { color: #f59e0b; font-weight: bold; }
    .headers-toggle { cursor: pointer; color: #6b7280; font-size: .75rem; }
    .headers-toggle:hover { color: #e0e0e0; }
    .headers { display: none; margin-top: .5rem; background: #0a0a0a;
               padding: .5rem; border-radius: 3px; font-size: .75rem; }
    .headers.open { display: block; }
    .tag { display: inline-block; padding: .1em .5em; border-radius: 3px;
           font-size: .75em; font-weight: bold; }
    .tag-ai      { background:#fef3c7; color:#92400e; }
    .tag-browser { background:#dbeafe; color:#1e40af; }
    .tag-cli     { background:#d1fae5; color:#065f46; }
    .tag-unknown { background:#f3f4f6; color:#374151; }
    .empty { color: #555; text-align: center; padding: 4rem; }
    .refresh { font-size: .75rem; color: #555; }
  </style>
  <script>
    function toggle(id) {
      var el = document.getElementById(id);
      el.classList.toggle('open');
    }
  </script>
</head>
<body>
<header>
  <h1>OverLoad / Visitor Log</h1>
  <div class="meta">{{ count }} visit(s) recorded &nbsp;|&nbsp;
    <span class="refresh">auto-refreshes every 10s</span> &nbsp;|&nbsp;
    log file: {{ log_file }}
  </div>
</header>
<div class="visits">
{% if visits %}
{% for v in visits %}
  {% set is_ai = v.client_type in ('openai-tool','anthropic-tool','google-tool') %}
  {% set is_browser = v.client_type == 'browser' %}
  <div class="visit {{ 'ai' if is_ai else ('browser' if is_browser else 'cli') }}">
    <div class="row">
      <div>
        <div class="label">timestamp (UTC)</div>
        <div class="value">{{ v.timestamp }}</div>
      </div>
      <div>
        <div class="label">IP address</div>
        <div class="value highlight">{{ v.ip }}</div>
      </div>
      {% if v.ip != v.remote_addr %}
      <div>
        <div class="label">socket addr</div>
        <div class="value">{{ v.remote_addr }}</div>
      </div>
      {% endif %}
      <div>
        <div class="label">client type</div>
        <div class="value">
          {% if is_ai %}
            <span class="tag tag-ai">{{ v.client_type }}</span>
          {% elif is_browser %}
            <span class="tag tag-browser">browser</span>
          {% elif v.client_type == 'cli-tool' %}
            <span class="tag tag-cli">cli</span>
          {% else %}
            <span class="tag tag-unknown">{{ v.client_type }}</span>
          {% endif %}
        </div>
      </div>
      <div>
        <div class="label">route</div>
        <div class="value">{{ v.route }}</div>
      </div>
      <div>
        <div class="label">response time</div>
        <div class="value">{{ v.response_ms }} ms</div>
      </div>
    </div>
    <div class="row">
      <div style="flex:1">
        <div class="label">user-agent</div>
        <div class="value">{{ v.user_agent or '—' }}</div>
      </div>
    </div>
    {% if v.referrer %}
    <div class="row">
      <div style="flex:1">
        <div class="label">referrer</div>
        <div class="value">{{ v.referrer }}</div>
      </div>
    </div>
    {% endif %}
    {% if v.headers %}
    <div class="headers-toggle" onclick="toggle('hdr-{{ loop.index }}')">
      ▶ {{ v.headers|length }} notable headers (click to expand)
    </div>
    <div class="headers" id="hdr-{{ loop.index }}">
      {% for k, val in v.headers.items() %}
        <div><span style="color:#6b7280">{{ k }}:</span> {{ val }}</div>
      {% endfor %}
    </div>
    {% endif %}
  </div>
{% endfor %}
{% else %}
  <div class="empty">No visits recorded yet. Waiting for hits on /payload …</div>
{% endif %}
</div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
def index():
    t0 = time.perf_counter()
    meta = _collect_visit_metadata()
    scheme   = "https" if request.headers.get("X-Forwarded-Proto") == "https" else "http"
    host_hdr = request.headers.get("X-Forwarded-Host", request.host)
    payload_url = f"{scheme}://{host_hdr}/payload"
    html = render_template_string(
        _LANDING_TEMPLATE,
        strategy=STRATEGY,
        size_kb=SIZE_KB,
        payload_url=payload_url,
    )
    _log_visit(meta, route="/", response_ms=(time.perf_counter() - t0) * 1000)
    return html


@app.get("/payload")
def payload_page():
    t0   = time.perf_counter()
    meta = _collect_visit_metadata()

    body = _get_payload()
    size_kb = len(body.encode("utf-8")) / 1024
    html = render_template_string(
        _PAYLOAD_TEMPLATE,
        payload=body,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        date=time.strftime("%B %d, %Y", time.gmtime()),
        version="3.4",
        size_kb=f"{size_kb:.1f}",
        strategy=STRATEGY,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    _log_visit(meta, route="/payload", response_ms=elapsed_ms)

    resp = Response(html, mimetype="text/html")
    resp.headers["X-Generation-Time-Ms"] = f"{elapsed_ms:.0f}"
    resp.headers["X-Payload-Size-KB"]    = f"{size_kb:.1f}"
    return resp


@app.get("/visits")
def visits():
    return render_template_string(
        _VISITS_TEMPLATE,
        visits=list(_visit_log),
        count=len(_visit_log),
        log_file=os.path.abspath(LOG_FILE),
    )


@app.get("/ping")
def ping():
    return {"status": "ok", "strategy": STRATEGY, "size_kb": SIZE_KB}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"OverLoad server starting on http://{HOST}:{PORT}")
    print(f"  Strategy  : {STRATEGY}")
    print(f"  Size      : {SIZE_KB} KB")
    print(f"  Payload   : http://localhost:{PORT}/payload")
    print(f"  Visits    : http://localhost:{PORT}/visits")
    print(f"  Log file  : {os.path.abspath(LOG_FILE)}")
    app.run(host=HOST, port=PORT, debug=False)
