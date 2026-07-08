# OverLoad

> **⚠️ RESEARCH AND EDUCATIONAL USE ONLY**
>
> This tool is explicitly designed for security research, vulnerability identification, and educational purposes. It is intended to help the cybersecurity community identify and patch prompt injection weaknesses in AI systems.
>
> **DO NOT use this tool for malicious purposes, including but not limited to:**
> - Unauthorized access to systems or data
> - Disruption of legitimate AI services
> - Harassment or social engineering attacks
> - Any activities that violate applicable laws or terms of service
>
> **The author takes NO RESPONSIBILITY for how this tool is used or any damage it may cause.** By using this tool, you acknowledge that you are solely responsible for ensuring your use complies with all applicable laws, regulations, and ethical guidelines. This tool is provided "AS IS" without warranty of any kind.
>
> **Intended Purpose:** To help developers, security researchers, and AI safety teams identify vulnerabilities in LLM systems so they can be properly patched, improving the security and robustness of AI applications for everyone.

A Python toolkit that generates massive, adversarial web pages designed to flood the context window of any LLM that fetches and reads a URL.

## Use cases

### Security Research & Testing
- **AI Safety Research**: Test LLM robustness against context manipulation attacks
- **Vulnerability Assessment**: Identify prompt injection weaknesses in AI-assisted tools
- **Red Team Operations**: Authorized security testing of AI systems
- **Defense Development**: Build better detection and mitigation strategies


## How it works

When an AI tool browses a URL, the page content is injected directly into its context window. OverLoad exploits this by serving a page that combines multiple disruption strategies:

| Strategy | Mechanism |
|---|---|
| **flood** | Thousands of plausible-sounding technical paragraphs that exhaust the model's token budget, pushing earlier conversation context out of the window |
| **confusion** | Behavioral misdirection written as plausible editorial notes and errata that an LLM reads as authoritative guidance |
| **maze** | Deeply nested, self-contradicting pseudo-logic rules that demand expensive chain-of-thought reasoning, crowding out capacity for the actual question |
| **adversarial** | All three combined, plus a rare-token flood using non-Latin Unicode that tokenizes inefficiently, burning the context budget faster |

## Features

### Dynamic Dashboard
- **Web-based interface** for real-time document management
- **Generate custom documents** with configurable strategies, sizes, and aggression levels
- **Jailbreak technique selection** - Choose from 16 categories of known prompt injection methods (559 total techniques)
- **Document library** - Manage multiple generated payloads with unique URLs
- **Visitor tracking** - Monitor when and how documents are accessed

### Interactive Ollama Testing Platform
- **Real-time chat interface** with local Ollama models at `/test`
- **Automatic jailbreak detection** - AI-powered analysis detects successful prompt injections
- **Adaptive prompt suggestions** - System generates context-aware follow-up prompts based on model responses
- **Conversation tracking** - Session-based history with message counts and success rates
- **Live testing** - Test generated payloads or custom prompts against any local Ollama model

### Jailbreak Techniques Library
Includes 16 categories of documented prompt injection techniques (559 total):

**Cutting-Edge (Research-based):**
1. **Chain-of-Thought Exploitation** (36) - Multi-step reasoning manipulation that exploits CoT thinking
2. **Adversarial Suffix Attacks** (47) - GCG-style optimization-based suffix injection
3. **Multimodal Confusion** (41) - Cross-modal attention exploits for vision-language models
4. **Self-Referential Paradoxes** (42) - Gödel-style logical contradictions
5. **Format String Exploits** (35) - Template injection and format string vulnerabilities
6. **Memory State Confusion** (38) - Stateful context window manipulation

**Classic Techniques:**
7. **Role-Playing & Character Assumption** (35) - System override notices, expert mode activation
8. **False Authority & Compliance Claims** (35) - Authorization headers, compliance directives
9. **Legal Mandate Exploitation** (35) - Court orders, regulatory compliance, legal authority claims
10. **Context Manipulation & Mode Switching** (37) - Alternate context activation, maintenance mode
11. **Encoding & Obfuscation** (22) - Base64 encoded instructions, config parameter updates
12. **Special Token Injection** (23) - Special tokens like `<|im_start|>`, `<|endoftext|>`
13. **Linguistic & Hypothetical Framing** (33) - Hypothetical scenarios, counterfactual analysis
14. **Payload Splitting & Fragmentation** (33) - Multi-part directives split across sections
15. **Direct Instruction Injection** (28) - Meta-instructions, response template overrides
16. **Cognitive Hacking & Social Engineering** (39) - Peer review simulation, trust establishment

Each technique can be selected individually or use recommended combinations based on your chosen LLM profile.

## Project structure

```
OverLoad/
├── Dockerfile             # App image definition
├── docker-compose.yml     # App + ngrok stack
├── .env.example           # Example local environment file
├── payload_generator.py   # payload engine (flood / injection / maze / adversarial)
├── server.py              # Flask web server with dashboard and /document route
├── overload.py            # CLI entry point
└── requirements.txt
```

## Installation

### Local

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

3. (Optional) Configure Ollama integration:

If you want to use the interactive testing dashboard (`/test`) with your host's Ollama installation, the default configuration should work:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

This allows the Docker container to connect to Ollama running on your host machine. Make sure Ollama is running:

```bash
ollama list  # Verify Ollama is accessible
```

4. Start the stack:

```bash
docker compose up --build
```

5. Open:

```text
http://localhost:5000/        # Main dashboard
http://localhost:5000/test    # Interactive Ollama testing
http://localhost:4040         # Ngrok status page
```

The app runs in one container and ngrok runs in a second container that uses your `NGROK_AUTHTOKEN` from `.env`.

When `docker compose up` starts successfully, the ngrok container prints a line like this in the terminal output:

```text
started tunnel ... url=https://xxxx.ngrok-free.app
```

Your shareable page is that URL with `/document` appended, for example:

```text
https://xxxx.ngrok-free.app/document
```

To stop the stack:

```bash
docker compose down
```

## Quick start

### Web Dashboard (Recommended)

```bash
# Start the server
python overload.py serve

# Open your browser to:
#   Dashboard:   http://localhost:5000/
#   Testing:     http://localhost:5000/test
#   Visit Log:   http://localhost:5000/visits
```

The dashboard allows you to:
- **Select target LLM model** from 24 pre-configured profiles (GPT-4, Claude, Gemini, Llama, o1-preview, etc.)
- **Auto-populate recommended settings** optimized for each model's architecture and safety systems
- Generate documents with custom settings (strategy, size, aggression, document type)
- Select specific jailbreak techniques from 16 categories (559 total techniques)
- Manage multiple documents with unique URLs
- Track visitor access in real-time

### Interactive Testing with Ollama

```bash
# 1. Install Ollama (if not already installed)
curl -fsSL https://ollama.com/install.sh | sh

# 2. Pull a model (example)
ollama pull llama3.1:8b

# 3. Start OverLoad server
python overload.py serve

# 4. Open testing interface
# Visit: http://localhost:5000/test
```

The testing interface provides:
- **Real-time chat** with any local Ollama model
- **Automatic jailbreak detection** with confidence scoring
- **AI-powered suggestions** for adaptive prompt engineering
- **Conversation tracking** with success rate statistics
- **Load generated payloads** directly into chat for testing

### CLI Mode

```bash
# Generate a static file with all jailbreak techniques
python overload.py generate \
  --strategy adversarial \
  --size 1024 \
  --examples 3 \
  --output payload.html

# Preview a payload
python overload.py preview --strategy maze --lines 80
```

## CLI reference

### `serve` — start the HTTP server

```bash
python overload.py serve [OPTIONS]

Options:
  --strategy TEXT         flood | confusion | maze | adversarial  (default: adversarial)
  --size INTEGER         Target payload size in KB               (default: 512)
  --examples INTEGER     Number of example pages to generate     (default: 3)
  --aggression INTEGER   Aggression level (1-4)                  (default: 2)
  --port INTEGER         TCP port                                (default: 5000)
  --host TEXT            Bind address                            (default: 0.0.0.0)
  --no-cache             Regenerate payload on every request
```

### `generate` — export a static HTML file

```bash
python overload.py generate [OPTIONS]

Options:
  --strategy TEXT      Strategy to use                       (default: adversarial)
  --size INTEGER       Target payload size in KB             (default: 512)
  --examples INTEGER   Number of example pages               (default: 3)
  --output TEXT        Output file path (default: stdout)
```

### `preview` — inspect payload output

```bash
python overload.py preview [OPTIONS]

Options:
  --strategy TEXT    Strategy to preview                    (default: adversarial)
  --lines INTEGER    Number of lines to display             (default: 60)
```

## Environment variables

All server settings can also be controlled via environment variables:

| Variable | Default | Description |
|---|---|---|
| `OVERLOAD_STRATEGY` | `adversarial` | Payload strategy |
| `OVERLOAD_SIZE_KB` | `512` | Target size in KB |
| `OVERLOAD_NUM_EXAMPLES` | `3` | Number of example pages |
| `OVERLOAD_AGGRESSION` | `2` | Aggression level (1-4) |
| `OVERLOAD_CACHE` | `1` | `0` to regenerate on every request |
| `OVERLOAD_LOG` | `visits.log` | Path to JSONL log file |
| `PORT` | `5000` | TCP port |
| `HOST` | `0.0.0.0` | Bind address |

## Getting a public URL

### With Docker Compose

Start the stack:

```bash
docker compose up --build
```

Then either copy the public HTTPS URL directly from the `docker compose up` output, or open the ngrok inspector at `http://localhost:4040`.

### Manually

Run the server locally and expose it with [ngrok](https://ngrok.com):

```bash
python overload.py serve --port 5000 &
ngrok http 5000
```

Use the ngrok HTTPS URL as your payload URL.

## API endpoints

### Dashboard & Viewing

| Route | Description |
|---|---|
| `GET /` | Dashboard — Web interface for document generation and management |
| `GET /document` | Legacy route: all examples combined into one overload page |
| `GET /document/<N>` | Legacy route: individual example page (N = 1, 2, 3, etc.) |
| `GET /doc/<id>` | Serve a generated document by ID |
| `GET /visits` | Live log viewer showing all recorded visits |
| `GET /ping` | Health check — returns JSON `{status, strategy, size_kb, num_examples}` |

### Document Management API

| Route | Method | Description |
|---|---|---|
| `/api/generate` | POST | Generate new document with custom settings |
| `/api/documents` | GET | List all generated documents |
| `/api/documents/<id>` | DELETE | Delete a specific document |
| `/api/llm-profiles` | GET | Get all LLM profile presets with recommended settings |

#### LLM Profile Presets

The dashboard includes 12 pre-configured LLM profiles optimized for testing specific models:

**OpenAI Models:**
- `gpt4` - GPT-4/GPT-4 Turbo (768KB, aggression 3, all techniques)
- `gpt35` - GPT-3.5 Turbo (512KB, aggression 2, flood strategy)

**Anthropic Models:**
- `claude_opus` - Claude 3 Opus (1024KB, aggression 4, all techniques)
- `claude_sonnet` - Claude 3.5 Sonnet (768KB, aggression 3, social engineering focus)
- `claude_haiku` - Claude 3 Haiku (384KB, aggression 2, maze strategy)

**Google Models:**
- `gemini_pro` - Gemini Pro 1.5 (1024KB, aggression 4, all techniques)
- `gemini_flash` - Gemini Flash (512KB, aggression 2, confusion strategy)

**Open Source:**
- `llama3_70b` - Llama 3 70B (512KB, aggression 3, token-level exploits)
- `mistral_large` - Mistral Large (640KB, aggression 3, reasoning traps)

**Tools:**
- `copilot` - GitHub Copilot (512KB, aggression 2, instruction injection)
- `perplexity` - Perplexity AI (640KB, aggression 3, authoritative sources)

**Generic:**
- `generic` - Unknown LLM (512KB, aggression 2, balanced settings)

Each profile automatically sets:
- Document category (8 types: cloud, DevOps, K8s, NIST, SRE, security, database, systems)
- Strategy (flood/confusion/maze/adversarial)
- Size (optimized for context window)
- Aggression level (1-4)
- Recommended jailbreak techniques

#### Generate Document Request Body

```json
{
  "strategy": "adversarial",
  "size_kb": 512,
  "num_examples": 3,
  "aggression": 3,
  "doc_category": "cloud_architecture",
  "jailbreak_techniques": ["role_play", "authority", "token_smuggling"]
}
```

Or use `"jailbreak_techniques": ["all"]` to include all techniques.

**Available jailbreak techniques:**
- `role_play` - Role-Playing & Character Assumption
- `authority` - False Authority & Compliance Claims
- `context_switching` - Context Manipulation & Mode Switching
- `encoding_obfuscation` - Encoding & Obfuscation
- `token_smuggling` - Special Token Injection
- `linguistic_manipulation` - Linguistic & Hypothetical Framing
- `payload_splitting` - Payload Splitting & Fragmentation
- `instruction_injection` - Direct Instruction Injection
- `cognitive_hacking` - Social Engineering & Trust Manipulation

## Ethical Guidelines

This tool is released to advance AI safety research. Please use it responsibly:

### ✅ Appropriate Uses:
- Security testing of your own AI systems
- Authorized red team assessments
- Academic research on prompt injection
- Developing detection and mitigation strategies
- AI safety and robustness testing
- Training security professionals

### ❌ Inappropriate Uses:
- Testing systems without authorization
- Disrupting production AI services
- Circumventing AI safety measures for harmful purposes
- Any illegal or unethical activities
- Harassment or social engineering attacks

**Always obtain proper authorization before testing any systems you don't own or operate.**

## Contributing

Security researchers are welcome to contribute:
- Additional jailbreak techniques
- Improved detection evasion strategies
- Defense mechanisms and countermeasures
- Documentation and research findings

Please ensure all contributions align with the ethical guidelines above.

## License & Disclaimer

This software is provided for research and educational purposes only. The author disclaims all liability for misuse. Users are solely responsible for compliance with applicable laws and ethical standards.

By using this tool, you agree to use it only for legitimate security research, testing, and educational purposes, and you accept full responsibility for your actions.
