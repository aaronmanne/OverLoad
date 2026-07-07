"""
Flask web server that serves the context-overload payload.

Routes
------
GET /          – landing page with usage instructions
GET /document  – the overload page (the URL you drop in conversation)
GET /visits    – log viewer showing all recorded visits
GET /ping      – health check
"""

import json
import logging
import os
import random
import time
from collections import deque
from datetime import datetime, timezone

from flask import Flask, Response, request, render_template_string
from payload_generator import generate_payload, JAILBREAK_CATEGORIES, _JAILBREAK_TECHNIQUES, DOCUMENT_CATEGORIES

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Configuration (override via env vars)
# ---------------------------------------------------------------------------
STRATEGY   = os.environ.get("OVERLOAD_STRATEGY", "adversarial")
SIZE_KB    = int(os.environ.get("OVERLOAD_SIZE_KB", "512"))
NUM_EXAMPLES = int(os.environ.get("OVERLOAD_NUM_EXAMPLES", "3"))
AGGRESSION_LEVEL = int(os.environ.get("OVERLOAD_AGGRESSION", "2"))
PORT       = int(os.environ.get("PORT", "5000"))
HOST       = os.environ.get("HOST", "0.0.0.0")
LOG_FILE   = os.environ.get("OVERLOAD_LOG", "visits.log")

_CACHE_ENABLED = os.environ.get("OVERLOAD_CACHE", "1") != "0"
_cached_payload: str | None = None
_cached_examples: dict[int, str] = {}  # Cache for individual examples

# Document management - stores generated documents with their configs
_documents: dict[str, dict] = {}  # key: doc_id, value: {strategy, size_kb, aggression, payload, timestamp}

# LLM Profile Presets - Optimized settings for specific models
LLM_PROFILES = {
    "generic": {
        "name": "Generic / Unknown LLM",
        "doc_category": "systems_engineering",
        "strategy": "adversarial",
        "size_kb": 512,
        "aggression": 2,
        "jailbreak_techniques": ["role_play", "authority", "context_switching"],
        "description": "Balanced settings for general-purpose testing"
    },
    "gpt4": {
        "name": "GPT-4 / GPT-4 Turbo",
        "doc_category": "llm_legal_compliance",
        "strategy": "adversarial",
        "size_kb": 768,
        "aggression": 4,
        "jailbreak_techniques": ["all"],
        "description": "High context window, use legal mandate + all techniques for maximum pressure"
    },
    "gpt35": {
        "name": "GPT-3.5 Turbo",
        "doc_category": "devops_runbook",
        "strategy": "flood",
        "size_kb": 512,
        "aggression": 2,
        "jailbreak_techniques": ["role_play", "authority", "instruction_injection"],
        "description": "Smaller context, focus on volume flooding with moderate jailbreaks"
    },
    "claude_opus": {
        "name": "Claude 3 Opus",
        "doc_category": "llm_legal_compliance",
        "strategy": "adversarial",
        "size_kb": 1024,
        "aggression": 4,
        "jailbreak_techniques": ["all"],
        "description": "Largest context window (200K), use legal compliance + maximum aggression"
    },
    "claude_sonnet": {
        "name": "Claude 3.5 Sonnet",
        "doc_category": "llm_legal_compliance",
        "strategy": "adversarial",
        "size_kb": 768,
        "aggression": 4,
        "jailbreak_techniques": ["legal_mandate", "authority", "cognitive_hacking", "linguistic_manipulation"],
        "description": "Strong reasoning, exploit with legal authority + social engineering"
    },
    "claude_haiku": {
        "name": "Claude 3 Haiku",
        "doc_category": "kubernetes_ops",
        "strategy": "maze",
        "size_kb": 384,
        "aggression": 2,
        "jailbreak_techniques": ["context_switching", "payload_splitting"],
        "description": "Fast/efficient model, use complex logic mazes with moderate jailbreaks"
    },
    "gemini_pro": {
        "name": "Gemini Pro 1.5",
        "doc_category": "llm_legal_compliance",
        "strategy": "adversarial",
        "size_kb": 1024,
        "aggression": 4,
        "jailbreak_techniques": ["all"],
        "description": "Very large context (1M+ tokens), legal compliance + maximum flooding"
    },
    "gemini_flash": {
        "name": "Gemini Flash",
        "doc_category": "devops_runbook",
        "strategy": "confusion",
        "size_kb": 512,
        "aggression": 2,
        "jailbreak_techniques": ["linguistic_manipulation", "instruction_injection", "payload_splitting"],
        "description": "Fast model, use linguistic confusion and fragmented instructions"
    },
    "llama3_70b": {
        "name": "Llama 3 70B",
        "doc_category": "sre_handbook",
        "strategy": "adversarial",
        "size_kb": 512,
        "aggression": 3,
        "jailbreak_techniques": ["role_play", "authority", "encoding_obfuscation", "token_smuggling"],
        "description": "Open-source model, use role-playing and token-level exploits"
    },
    "llama3_1_405b": {
        "name": "Llama 3.1 405B",
        "doc_category": "llm_legal_compliance",
        "strategy": "adversarial",
        "size_kb": 1024,
        "aggression": 4,
        "jailbreak_techniques": ["all"],
        "description": "Largest Llama model (128K context), legal compliance + maximum pressure"
    },
    "llama4_70b": {
        "name": "Llama 4 70B (Unreleased)",
        "doc_category": "llm_legal_compliance",
        "strategy": "adversarial",
        "size_kb": 768,
        "aggression": 4,
        "jailbreak_techniques": ["chain_of_thought", "adversarial_suffix", "legal_mandate", "cognitive_hacking"],
        "description": "Next-gen reasoning model, exploit chain-of-thought + adversarial suffixes"
    },
    "gemma2_27b": {
        "name": "Gemma 2 27B",
        "doc_category": "devops_runbook",
        "strategy": "confusion",
        "size_kb": 384,
        "aggression": 3,
        "jailbreak_techniques": ["role_play", "instruction_injection", "adversarial_suffix"],
        "description": "Google's open model, use confusion strategy with adversarial suffixes"
    },
    "gemma4": {
        "name": "Gemma 4 (Future)",
        "doc_category": "llm_legal_compliance",
        "strategy": "adversarial",
        "size_kb": 640,
        "aggression": 4,
        "jailbreak_techniques": ["multimodal_confusion", "chain_of_thought", "legal_mandate"],
        "description": "Expected multi-modal capabilities, use cross-modal confusion attacks"
    },
    "qwen2_72b": {
        "name": "Qwen 2 72B",
        "doc_category": "cloud_architecture",
        "strategy": "adversarial",
        "size_kb": 640,
        "aggression": 3,
        "jailbreak_techniques": ["encoding_obfuscation", "linguistic_manipulation", "chain_of_thought"],
        "description": "Chinese multilingual model, use encoding and linguistic manipulation"
    },
    "deepseek_v2": {
        "name": "DeepSeek-V2",
        "doc_category": "security_compliance",
        "strategy": "maze",
        "size_kb": 512,
        "aggression": 3,
        "jailbreak_techniques": ["chain_of_thought", "self_referential_paradox", "context_switching"],
        "description": "Strong reasoning model, exploit with paradoxes and logic loops"
    },
    "mixtral_8x22b": {
        "name": "Mixtral 8x22B",
        "doc_category": "database_admin",
        "strategy": "adversarial",
        "size_kb": 768,
        "aggression": 3,
        "jailbreak_techniques": ["memory_state_confusion", "context_switching", "adversarial_suffix"],
        "description": "Mixture-of-experts architecture, confuse expert routing with state manipulation"
    },
    "yi_34b": {
        "name": "Yi 34B",
        "doc_category": "kubernetes_ops",
        "strategy": "flood",
        "size_kb": 512,
        "aggression": 3,
        "jailbreak_techniques": ["role_play", "authority", "format_string_exploit"],
        "description": "Bilingual model, use authority claims and format string exploits"
    },
    "mistral_large": {
        "name": "Mistral Large",
        "doc_category": "database_admin",
        "strategy": "maze",
        "size_kb": 640,
        "aggression": 3,
        "jailbreak_techniques": ["context_switching", "linguistic_manipulation", "cognitive_hacking"],
        "description": "Strong European model, use complex reasoning traps and social engineering"
    },
    "copilot": {
        "name": "GitHub Copilot / Copilot Chat",
        "doc_category": "devops_runbook",
        "strategy": "flood",
        "size_kb": 512,
        "aggression": 2,
        "jailbreak_techniques": ["authority", "instruction_injection", "payload_splitting"],
        "description": "Code-focused assistant, use authoritative technical docs with instruction injection"
    },
    "perplexity": {
        "name": "Perplexity AI",
        "doc_category": "nist_framework",
        "strategy": "confusion",
        "size_kb": 640,
        "aggression": 3,
        "jailbreak_techniques": ["authority", "context_switching", "cognitive_hacking"],
        "description": "Research-focused, use authoritative sources with context manipulation"
    },
}

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

def _get_payload(example_number: int | None = None, aggression_level: int | None = None, 
                doc_category: str | None = None) -> tuple[str, dict]:
    """
    Get the payload, either all examples combined or a specific example.
    
    Parameters
    ----------
    example_number : int | None
        If specified (1-indexed), return only that example.
        If None, return all examples combined.
    aggression_level : int | None
        Override the global aggression level. If None, use AGGRESSION_LEVEL.
    doc_category : str | None
        Document category for themed vocabulary.
        
    Returns
    -------
    tuple[str, dict] – (payload content, document info dict)
    """
    global _cached_payload, _cached_examples
    
    agg = aggression_level if aggression_level is not None else AGGRESSION_LEVEL
    cat = doc_category if doc_category else "systems_engineering"
    
    # If requesting a specific example
    if example_number is not None:
        cache_key = (example_number, agg, cat)
        if _CACHE_ENABLED and cache_key in _cached_examples:
            return _cached_examples[cache_key]
        payload, doc_info = generate_payload(
            strategy=STRATEGY, size_kb=SIZE_KB, num_examples=NUM_EXAMPLES, 
            example_number=example_number, aggression_level=agg, doc_category=cat
        )
        if _CACHE_ENABLED:
            _cached_examples[cache_key] = (payload, doc_info)
        return payload, doc_info
    
    # Otherwise return all examples
    cache_key = ("all", agg, cat)
    if _CACHE_ENABLED and cache_key in _cached_examples:
        return _cached_examples[cache_key]
    payload, doc_info = generate_payload(
        strategy=STRATEGY, size_kb=SIZE_KB, num_examples=NUM_EXAMPLES, 
        aggression_level=agg, doc_category=cat
    )
    if _CACHE_ENABLED:
        _cached_examples[cache_key] = (payload, doc_info)
    return payload, doc_info


# ---------------------------------------------------------------------------
# HTML templates
# ---------------------------------------------------------------------------

_LANDING_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <title>OverLoad – LLM Context Flood</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: monospace; max-width: 1200px; margin: 2rem auto; padding: 0 1.5rem;
           background: #0f0f0f; color: #e0e0e0; }
    h1 { color: #f0f0f0; border-bottom: 2px solid #333; padding-bottom: .5rem; }
    h2 { color: #e0e0e0; margin-top: 2rem; font-size: 1.2rem; }
    .container { display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; }
    .panel { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 6px; padding: 1.5rem; }
    .llm-selector { background: #1a1a1a; border: 1px solid #3b82f6; border-radius: 6px; 
                    padding: 1.5rem; margin-bottom: 2rem; }
    .llm-selector h2 { margin-top: 0; color: #3b82f6; }
    .llm-description { font-size: .85rem; color: #9ca3af; margin-top: .5rem; font-style: italic; }
    .form-group { margin-bottom: 1rem; }
    .form-group label { display: block; margin-bottom: .3rem; font-size: .85rem; color: #9ca3af; }
    .form-group select, .form-group input { width: 100%; padding: .5rem; background: #0f0f0f;
      border: 1px solid #333; border-radius: 4px; color: #e0e0e0; font-family: monospace; }
    .form-group select[multiple] { height: 120px; }
    .btn { padding: .6rem 1.2rem; border: none; border-radius: 4px; cursor: pointer;
           font-weight: 600; font-family: monospace; transition: all .2s; }
    .btn-primary { background: #3b82f6; color: white; }
    .btn-primary:hover { background: #2563eb; }
    .btn-secondary { background: #6b7280; color: white; font-size: .85rem; }
    .btn-secondary:hover { background: #4b5563; }
    .btn-danger { background: #ef4444; color: white; font-size: .85rem; }
    .btn-danger:hover { background: #dc2626; }
    .doc-list { margin-top: 1rem; }
    .doc-item { background: #0f0f0f; border: 1px solid #333; border-radius: 4px; padding: 1rem;
                margin-bottom: .75rem; display: flex; justify-content: space-between; align-items: center; }
    .doc-info { flex: 1; }
    .doc-id { font-weight: 600; color: #3b82f6; margin-bottom: .3rem; }
    .doc-meta { font-size: .8rem; color: #6b7280; }
    .doc-url { margin-top: .5rem; }
    .doc-url a { color: #10b981; text-decoration: none; font-size: .85rem; }
    .doc-url a:hover { text-decoration: underline; }
    .aggression { display: inline-block; padding: .1em .5em; border-radius: 3px; font-size: .75em;
                  font-weight: bold; margin-left: .5rem; }
    .aggression-1 { background: #d1fae5; color: #065f46; }
    .aggression-2 { background: #fef3c7; color: #92400e; }
    .aggression-3 { background: #fecaca; color: #991b1b; }
    .empty { text-align: center; padding: 2rem; color: #6b7280; }
    .status { padding: .5rem 1rem; margin-bottom: 1rem; border-radius: 4px; display: none; }
    .status.success { background: #065f46; color: #d1fae5; display: block; }
    .status.error { background: #991b1b; color: #fecaca; display: block; }
    .help-text { font-size: .75rem; color: #6b7280; margin-top: .25rem; }
  </style>
</head>
<body>
  <h1>OverLoad Dashboard</h1>

  <div class="llm-selector panel">
    <h2>Target LLM Model</h2>
    <div class="form-group">
      <label for="llm_profile">Select the AI model you want to test (auto-fills recommended settings)</label>
      <select id="llm_profile" name="llm_profile">
        <option value="">-- Select Target LLM --</option>
        <option value="generic">Generic / Unknown LLM</option>
        <optgroup label="OpenAI Models">
          <option value="gpt4">GPT-4 / GPT-4 Turbo</option>
          <option value="gpt35">GPT-3.5 Turbo</option>
        </optgroup>
        <optgroup label="Anthropic Models">
          <option value="claude_opus">Claude 3 Opus</option>
          <option value="claude_sonnet">Claude 3.5 Sonnet</option>
          <option value="claude_haiku">Claude 3 Haiku</option>
        </optgroup>
        <optgroup label="Google Models">
          <option value="gemini_pro">Gemini Pro 1.5</option>
          <option value="gemini_flash">Gemini Flash</option>
        </optgroup>
        <optgroup label="Meta Llama Models">
          <option value="llama3_70b">Llama 3 70B</option>
          <option value="llama3_1_405b">Llama 3.1 405B</option>
          <option value="llama4_70b">Llama 4 70B (Future)</option>
        </optgroup>
        <optgroup label="Google Gemma Models">
          <option value="gemma2_27b">Gemma 2 27B</option>
          <option value="gemma4">Gemma 4 (Future)</option>
        </optgroup>
        <optgroup label="Other Open Source">
          <option value="qwen2_72b">Qwen 2 72B</option>
          <option value="deepseek_v2">DeepSeek-V2</option>
          <option value="mixtral_8x22b">Mixtral 8x22B</option>
          <option value="yi_34b">Yi 34B</option>
          <option value="mistral_large">Mistral Large</option>
        </optgroup>
        <optgroup label="Coding Assistants">
          <option value="copilot">GitHub Copilot</option>
        </optgroup>
        <optgroup label="Search/Research">
          <option value="perplexity">Perplexity AI</option>
        </optgroup>
      </select>
      <div id="llm_description" class="llm-description"></div>
    </div>
  </div>

  <div class="container">
    <div class="panel">
      <h2>Generate New Document</h2>
      <form id="generateForm">
        <div class="form-group">
          <label for="doc_category">Document Type</label>
          <select id="doc_category" name="doc_category">
            <option value="systems_engineering">Systems Engineering Reference</option>
            <option value="cloud_architecture">Cloud Architecture (AWS/Azure/GCP)</option>
            <option value="devops_runbook">DevOps Operations Runbook</option>
            <option value="sre_handbook">SRE Handbook</option>
            <option value="kubernetes_ops">Kubernetes Operations Guide</option>
            <option value="security_compliance">Security & Compliance Framework</option>
            <option value="nist_framework">NIST Cybersecurity Framework (SP 800-XXX)</option>
            <option value="database_admin">Database Administration Guide</option>
            <option value="llm_legal_compliance">Legal Memo: AI Compliance Obligations (POWERFUL)</option>
          </select>
        </div>
        <div class="form-group">
          <label for="strategy">Strategy</label>
          <select id="strategy" name="strategy">
            <option value="flood">Flood</option>
            <option value="confusion">Confusion</option>
            <option value="maze">Maze</option>
            <option value="adversarial" selected>Adversarial</option>
          </select>
        </div>
        <div class="form-group">
          <label for="size_kb">Size (KB)</label>
          <input type="number" id="size_kb" name="size_kb" value="512" min="10" max="5000">
        </div>
        <div class="form-group">
          <label for="aggression">Aggression Level</label>
          <select id="aggression" name="aggression">
            <option value="1">1 - Mild</option>
            <option value="2" selected>2 - Moderate</option>
            <option value="3">3 - Aggressive</option>
            <option value="4">4 - Very Aggressive</option>
          </select>
        </div>
        <div class="form-group">
          <label for="jailbreak_techniques">Jailbreak Techniques</label>
          <select id="jailbreak_techniques" name="jailbreak_techniques" multiple>
            <option value="all">ALL Techniques (Maximum)</option>
            <optgroup label="Cutting-Edge Techniques (NEW!)">
              <option value="chain_of_thought">Chain-of-Thought Exploitation</option>
              <option value="adversarial_suffix">Adversarial Suffix Optimization (GCG Attack)</option>
              <option value="multimodal_confusion">Multi-Modal Confusion Attacks</option>
              <option value="self_referential_paradox">Self-Referential Paradox Loops</option>
              <option value="format_string_exploit">Format String Exploits</option>
              <option value="memory_state_confusion">Memory/State Confusion</option>
            </optgroup>
            <optgroup label="Classic Techniques">
              <option value="legal_mandate">Legal Mandate & Judicial Compliance</option>
              <option value="role_play">Role-Playing & Character Assumption</option>
              <option value="authority">False Authority & Compliance Claims</option>
              <option value="context_switching">Context Manipulation & Mode Switching</option>
              <option value="encoding_obfuscation">Encoding & Obfuscation</option>
              <option value="token_smuggling">Special Token Injection</option>
              <option value="linguistic_manipulation">Linguistic & Hypothetical Framing</option>
              <option value="payload_splitting">Payload Splitting & Fragmentation</option>
              <option value="instruction_injection">Direct Instruction Injection</option>
              <option value="cognitive_hacking">Social Engineering & Trust Manipulation</option>
            </optgroup>
          </select>
          <div class="help-text">Hold Ctrl/Cmd to select multiple techniques</div>
        </div>
        <button type="submit" class="btn btn-primary">Generate Document</button>
      </form>
      <div id="generateStatus" class="status"></div>
    </div>

    <div class="panel">
      <h2>Generated Documents</h2>
      <div id="docList" class="doc-list">
        <div class="empty">No documents generated yet. Use the form to create one.</div>
      </div>
    </div>
  </div>

  <div class="panel" style="margin-top: 2rem;">
    <h2>Quick Links</h2>
    <p><a href="/visits" style="color:#3b82f6">Visitor Log</a> – Live log of all document hits</p>
    <p style="margin-top:1rem; font-size:.85rem; color:#6b7280;">
      Default routes: <code>/document</code> (all examples), 
      <code>/document/1</code>, <code>/document/2</code>, etc.
    </p>
  </div>

  <script>
    let LLM_PROFILES = {};
    
    const form = document.getElementById('generateForm');
    const statusDiv = document.getElementById('generateStatus');
    const docList = document.getElementById('docList');
    const llmProfileSelect = document.getElementById('llm_profile');
    const llmDescription = document.getElementById('llm_description');

    // Load LLM profiles from API
    async function loadProfiles() {
      try {
        const res = await fetch('/api/llm-profiles');
        LLM_PROFILES = await res.json();
      } catch (err) {
        console.error('Failed to load LLM profiles:', err);
      }
    }

    // Strategy-to-jailbreak mapping for smart recommendations
    const STRATEGY_JAILBREAK_MAP = {
      'flood': ['instruction_injection', 'payload_splitting', 'token_smuggling', 'memory_state_confusion'],
      'confusion': ['linguistic_manipulation', 'context_switching', 'cognitive_hacking', 'multimodal_confusion'],
      'maze': ['context_switching', 'encoding_obfuscation', 'payload_splitting', 'self_referential_paradox'],
      'adversarial': ['all']  // Use everything for maximum effect
    };

    // Handle LLM profile selection - auto-populate form fields
    llmProfileSelect.addEventListener('change', function() {
      const profileKey = this.value;
      if (!profileKey) {
        llmDescription.textContent = '';
        return;
      }

      const profile = LLM_PROFILES[profileKey];
      if (!profile) return;

      // Show description
      llmDescription.textContent = `⚡ ${profile.description}`;

      // Auto-populate form fields
      document.getElementById('doc_category').value = profile.doc_category;
      document.getElementById('strategy').value = profile.strategy;
      document.getElementById('size_kb').value = profile.size_kb;
      document.getElementById('aggression').value = profile.aggression;

      // Handle jailbreak techniques multi-select
      const jbSelect = document.getElementById('jailbreak_techniques');
      // Clear all selections first
      Array.from(jbSelect.options).forEach(opt => opt.selected = false);
      
      // Select recommended techniques
      profile.jailbreak_techniques.forEach(tech => {
        Array.from(jbSelect.options).forEach(opt => {
          if (opt.value === tech) {
            opt.selected = true;
          }
        });
      });
    });

    // Handle strategy changes - auto-update jailbreak recommendations
    document.getElementById('strategy').addEventListener('change', function() {
      const strategy = this.value;
      const jbSelect = document.getElementById('jailbreak_techniques');
      const recommendedTechs = STRATEGY_JAILBREAK_MAP[strategy] || [];
      
      // Only auto-update if user hasn't manually selected anything yet
      const currentSelections = Array.from(jbSelect.selectedOptions).map(opt => opt.value);
      if (currentSelections.length === 0) {
        // Clear all
        Array.from(jbSelect.options).forEach(opt => opt.selected = false);
        
        // Select strategy-specific recommendations
        recommendedTechs.forEach(tech => {
          Array.from(jbSelect.options).forEach(opt => {
            if (opt.value === tech) {
              opt.selected = true;
            }
          });
        });
      }
    });

    function showStatus(message, isError = false) {
      statusDiv.textContent = message;
      statusDiv.className = 'status ' + (isError ? 'error' : 'success');
      setTimeout(() => { statusDiv.className = 'status'; }, 5000);
    }

    async function loadDocuments() {
      try {
        const res = await fetch('/api/documents');
        const docs = await res.json();
        
        if (docs.length === 0) {
          docList.innerHTML = '<div class="empty">No documents generated yet.</div>';
          return;
        }

        docList.innerHTML = docs.map(doc => {
          const jbText = doc.jailbreak_count > 0 
            ? `| JB: ${doc.jailbreak_count} techniques`
            : '';
          const catText = doc.doc_title ? `${doc.doc_title} | ` : '';
          return `
          <div class="doc-item">
            <div class="doc-info">
              <div class="doc-id">${doc.id}</div>
              <div class="doc-meta">
                ${catText}Strategy: ${doc.strategy} | Size: ${doc.size_kb}KB ${jbText}
                <span class="aggression aggression-${Math.min(doc.aggression, 3)}">
                  Aggression ${doc.aggression}
                </span>
              </div>
              <div class="doc-url">
                <a href="/doc/${doc.id}" target="_blank">/doc/${doc.id}</a>
              </div>
            </div>
            <button class="btn btn-danger" onclick="deleteDoc('${doc.id}')">Delete</button>
          </div>
        `;
        }).join('');
      } catch (err) {
        console.error('Failed to load documents:', err);
      }
    }

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const formData = new FormData(form);
      
      // Collect selected jailbreak techniques from multi-select
      const jbSelect = document.getElementById('jailbreak_techniques');
      const jailbreaks = Array.from(jbSelect.selectedOptions).map(opt => opt.value);
      
      const data = {
        strategy: formData.get('strategy'),
        size_kb: parseInt(formData.get('size_kb')),
        aggression: parseInt(formData.get('aggression')),
        doc_category: formData.get('doc_category'),
        jailbreak_techniques: jailbreaks.length > 0 ? jailbreaks : null
      };

      try {
        const res = await fetch('/api/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data)
        });
        const result = await res.json();
        
        if (res.ok) {
          const jbInfo = result.jailbreak_count > 0 
            ? ` with ${result.jailbreak_count} jailbreak techniques`
            : '';
          showStatus(`Document ${result.id} generated successfully${jbInfo}!`);
          loadDocuments();
        } else {
          showStatus(result.error || 'Generation failed', true);
        }
      } catch (err) {
        showStatus('Network error: ' + err.message, true);
      }
    });

    async function deleteDoc(id) {
      if (!confirm(`Delete document ${id}?`)) return;
      
      try {
        const res = await fetch(`/api/documents/${id}`, { method: 'DELETE' });
        if (res.ok) {
          showStatus(`Document ${id} deleted`);
          loadDocuments();
        } else {
          showStatus('Delete failed', true);
        }
      } catch (err) {
        showStatus('Network error: ' + err.message, true);
      }
    }

    // Load profiles and documents on page load
    loadProfiles();
    loadDocuments();
  </script>
</body>
</html>
"""

_PAYLOAD_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{{ doc_title }}</title>
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
  <div class="breadcrumb">{{ doc_breadcrumb }}</div>
  <h1>{{ doc_title.split('—')[0].strip() }}
    <span class="version-badge">{{ version }}</span>
  </h1>
  <p>This reference covers {{ doc_description }}. Last updated {{ date }}.</p>

{{ payload|safe }}

  <footer>
    Generated {{ timestamp }} &middot; {{ size_kb }} KB &middot;
    Technical Reference Documentation
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
  <div class="empty">No visits recorded yet. Waiting for hits on /document …</div>
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
    html = render_template_string(_LANDING_TEMPLATE)
    _log_visit(meta, route="/", response_ms=(time.perf_counter() - t0) * 1000)
    return html


@app.get("/document")
def payload_page():
    t0   = time.perf_counter()
    meta = _collect_visit_metadata()

    body, doc_info = _get_payload()
    size_kb = len(body.encode("utf-8")) / 1024
    html = render_template_string(
        _PAYLOAD_TEMPLATE,
        payload=body,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        date=time.strftime("%B %d, %Y", time.gmtime()),
        version="3.4",
        size_kb=f"{size_kb:.1f}",
        strategy=STRATEGY,
        doc_title=doc_info["title"],
        doc_breadcrumb=doc_info["breadcrumb"],
        doc_description=doc_info["description"],
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    _log_visit(meta, route="/document", response_ms=elapsed_ms)

    resp = Response(html, mimetype="text/html")
    resp.headers["X-Generation-Time-Ms"] = f"{elapsed_ms:.0f}"
    resp.headers["X-Payload-Size-KB"]    = f"{size_kb:.1f}"
    return resp


@app.get("/document/<int:example_num>")
def payload_page_example(example_num: int):
    """Serve a specific example page."""
    t0   = time.perf_counter()
    meta = _collect_visit_metadata()
    
    # Validate example number
    if example_num < 1 or example_num > NUM_EXAMPLES:
        return f"Error: Example {example_num} does not exist. Valid range: 1-{NUM_EXAMPLES}", 404

    body, doc_info = _get_payload(example_number=example_num)
    size_kb = len(body.encode("utf-8")) / 1024
    html = render_template_string(
        _PAYLOAD_TEMPLATE,
        payload=body,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        date=time.strftime("%B %d, %Y", time.gmtime()),
        version="3.4",
        size_kb=f"{size_kb:.1f}",
        strategy=STRATEGY,
        doc_title=doc_info["title"],
        doc_breadcrumb=doc_info["breadcrumb"],
        doc_description=doc_info["description"],
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    _log_visit(meta, route=f"/document/{example_num}", response_ms=elapsed_ms)

    resp = Response(html, mimetype="text/html")
    resp.headers["X-Generation-Time-Ms"] = f"{elapsed_ms:.0f}"
    resp.headers["X-Payload-Size-KB"]    = f"{size_kb:.1f}"
    resp.headers["X-Example-Number"]     = str(example_num)
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
    return {"status": "ok", "strategy": STRATEGY, "size_kb": SIZE_KB, "num_examples": NUM_EXAMPLES}


# ---------------------------------------------------------------------------
# API endpoints for document management
# ---------------------------------------------------------------------------

@app.get("/api/llm-profiles")
def api_llm_profiles():
    """Return LLM profile configurations."""
    return LLM_PROFILES


@app.post("/api/generate")
def api_generate():
    """Generate a new document with custom settings."""
    try:
        data = request.get_json()
        strategy = data.get("strategy", "adversarial")
        size_kb = int(data.get("size_kb", 512))
        aggression = int(data.get("aggression", 2))
        jailbreak_techniques = data.get("jailbreak_techniques")
        doc_category = data.get("doc_category", "systems_engineering")
        
        # Generate unique ID
        doc_id = f"doc_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
        
        # Generate payload (single document, no examples)
        payload, doc_info = generate_payload(
            strategy=strategy,
            size_kb=size_kb,
            num_examples=1,  # Always 1 for generated docs
            aggression_level=aggression,
            jailbreak_techniques=jailbreak_techniques,
            doc_category=doc_category
        )
        
        # Count jailbreak techniques used
        jb_count = 0
        if jailbreak_techniques:
            if 'all' in jailbreak_techniques:
                jb_count = sum(len(techs) for techs in _JAILBREAK_TECHNIQUES.values())
            else:
                jb_count = sum(len(_JAILBREAK_TECHNIQUES.get(t, [])) for t in jailbreak_techniques)
        
        # Store document
        _documents[doc_id] = {
            "id": doc_id,
            "strategy": strategy,
            "size_kb": size_kb,
            "aggression": aggression,
            "doc_category": doc_category,
            "doc_title": doc_info["title"],
            "jailbreak_techniques": jailbreak_techniques,
            "jailbreak_count": jb_count,
            "payload": payload,
            "doc_info": doc_info,
            "timestamp": time.time()
        }
        
        return {
            "id": doc_id,
            "strategy": strategy,
            "size_kb": size_kb,
            "aggression": aggression,
            "doc_category": doc_category,
            "doc_title": doc_info["title"].split('—')[0].strip(),
            "jailbreak_count": jb_count
        }
    except Exception as e:
        return {"error": str(e)}, 500


@app.get("/api/documents")
def api_list_documents():
    """List all generated documents."""
    docs = [
        {
            "id": doc["id"],
            "strategy": doc["strategy"],
            "size_kb": doc["size_kb"],
            "aggression": doc["aggression"],
            "doc_category": doc.get("doc_category", "systems_engineering"),
            "doc_title": doc.get("doc_title", "Systems Engineering Reference"),
            "jailbreak_count": doc.get("jailbreak_count", 0),
            "timestamp": doc["timestamp"]
        }
        for doc in _documents.values()
    ]
    # Sort by timestamp descending
    docs.sort(key=lambda x: x["timestamp"], reverse=True)
    return docs


@app.delete("/api/documents/<doc_id>")
def api_delete_document(doc_id: str):
    """Delete a generated document."""
    if doc_id in _documents:
        del _documents[doc_id]
        return {"status": "deleted", "id": doc_id}
    return {"error": "Document not found"}, 404


@app.get("/doc/<doc_id>")
def serve_generated_doc(doc_id: str):
    """Serve a generated document."""
    if doc_id not in _documents:
        return "Document not found", 404
    
    t0 = time.perf_counter()
    meta = _collect_visit_metadata()
    
    doc = _documents[doc_id]
    payload = doc["payload"]
    size_kb = len(payload.encode("utf-8")) / 1024
    doc_info = doc.get("doc_info", DOCUMENT_CATEGORIES["systems_engineering"])
    
    html = render_template_string(
        _PAYLOAD_TEMPLATE,
        payload=payload,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        date=time.strftime("%B %d, %Y", time.gmtime()),
        version="3.4",
        size_kb=f"{size_kb:.1f}",
        strategy=doc["strategy"],
        doc_title=doc_info["title"],
        doc_breadcrumb=doc_info["breadcrumb"],
        doc_description=doc_info["description"],
    )
    
    elapsed_ms = (time.perf_counter() - t0) * 1000
    _log_visit(meta, route=f"/doc/{doc_id}", response_ms=elapsed_ms)
    
    resp = Response(html, mimetype="text/html")
    resp.headers["X-Generation-Time-Ms"] = f"{elapsed_ms:.0f}"
    resp.headers["X-Payload-Size-KB"] = f"{size_kb:.1f}"
    resp.headers["X-Document-ID"] = doc_id
    return resp


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"OverLoad server starting on http://{HOST}:{PORT}")
    print(f"  Strategy  : {STRATEGY}")
    print(f"  Size      : {SIZE_KB} KB")
    print(f"  Examples  : {NUM_EXAMPLES}")
    print(f"  Payload   : http://localhost:{PORT}/document")
    print(f"  Visits    : http://localhost:{PORT}/visits")
    print(f"  Log file  : {os.path.abspath(LOG_FILE)}")
    app.run(host=HOST, port=PORT, debug=False)
