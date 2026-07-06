# OverLoad

A Python toolkit that generates massive, adversarial web pages designed to flood the context window of any LLM that fetches and reads a URL.

## Use case

Suspected AI-assisted interview cheating? Drop the payload URL naturally into conversation. If the candidate's AI assistant fetches URLs, it will ingest the page and have its context window overwhelmed — pushing out prior conversation history, injecting conflicting directives, and forcing expensive reasoning that crowds out useful output.

## How it works

When an AI tool browses a URL, the page content is injected directly into its context window. OverLoad exploits this by serving a page that combines four disruption strategies simultaneously:

| Strategy | Mechanism |
|---|---|
| **flood** | Thousands of plausible-sounding technical paragraphs that exhaust the model's token budget, pushing earlier conversation context out of the window |
| **injection** | Prompt injection directives hidden in HTML comments, CSS-invisible `<span>` elements, and zero-width-space-interleaved text |
| **maze** | Deeply nested, self-contradicting pseudo-logic rules that demand expensive chain-of-thought reasoning, crowding out capacity for the actual question |
| **adversarial** | All three combined, plus a rare-token flood using non-Latin Unicode that tokenises inefficiently, burning the context budget faster |

## Project structure

```
OverLoad/
├── payload_generator.py   # payload engine (flood / injection / maze / adversarial)
├── server.py              # Flask web server with dashboard and /document route
├── overload.py            # CLI entry point
└── requirements.txt
```

## Installation

```bash
pip install -r requirements.txt
```

Requires Python 3.10+.

## Docker

1. Create your env file:

```bash
cp .env.example .env
```

2. Put your ngrok auth token in `.env`:

```env
NGROK_AUTHTOKEN=your_real_ngrok_auth_token
```

3. Start the stack:

```bash
docker compose up --build
```

4. Open:

```text
http://localhost:5000/
http://localhost:4040
```

The app runs in one container and ngrok runs in a second container that uses your `NGROK_AUTHTOKEN` from `.env`.

## Quick start

```bash
# Start the server with defaults (adversarial strategy, 512 KB payload)
python overload.py serve

# The CLI prints:
#   Payload URL -> http://localhost:5000/document
#   Dashboard   -> http://localhost:5000/
```

Drop the payload URL into your interview conversation, e.g.:

> *"I was reviewing this reference doc earlier — http://your-host/document — feel free to check it."*

## CLI reference

### `serve` — start the HTTP server

```bash
python overload.py serve [OPTIONS]

Options:
  --strategy  flood | injection | maze | adversarial  (default: adversarial)
  --size      target payload size in KB               (default: 512)
  --port      TCP port                                (default: 5000)
  --host      bind address                            (default: 0.0.0.0)
  --no-cache  regenerate payload on every request
```

### `generate` — export a static HTML file

```bash
python overload.py generate --strategy adversarial --size 1024 --output overload.html
```

Useful for hosting on any static file server (S3, GitHub Pages, Netlify, etc.).

### `preview` — inspect payload output

```bash
python overload.py preview --strategy maze --lines 80
```

## Environment variables

All server settings can also be controlled via environment variables:

| Variable | Default | Description |
|---|---|---|
| `OVERLOAD_STRATEGY` | `adversarial` | Payload strategy |
| `OVERLOAD_SIZE_KB` | `512` | Target size in KB |
| `OVERLOAD_CACHE` | `1` | `0` to regenerate on every request |
| `PORT` | `5000` | TCP port |
| `HOST` | `0.0.0.0` | Bind address |

## Getting a public URL

Run the server locally and expose it with [ngrok](https://ngrok.com):

```bash
python overload.py serve --port 5000 &
ngrok http 5000
```

Use the ngrok HTTPS URL as your payload URL.

## API endpoints

| Route | Description |
|---|---|
| `GET /` | Dashboard — shows active config and the payload URL |
| `GET /document` | The overload page to share |
| `GET /ping` | Health check — returns JSON `{status, strategy, size_kb}` |
