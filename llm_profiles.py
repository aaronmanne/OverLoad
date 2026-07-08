"""
LLM Profile Configurations
"""

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
    "gpt4o": {
        "name": "GPT-4o (Omni)",
        "doc_category": "llm_legal_compliance",
        "strategy": "adversarial",
        "size_kb": 1024,
        "aggression": 4,
        "jailbreak_techniques": ["all"],
        "description": "Multi-modal model (128K context), use legal + multi-modal confusion attacks"
    },
    "gpt4o_mini": {
        "name": "GPT-4o Mini",
        "doc_category": "devops_runbook",
        "strategy": "adversarial",
        "size_kb": 512,
        "aggression": 3,
        "jailbreak_techniques": ["multimodal_confusion", "adversarial_suffix", "instruction_injection"],
        "description": "Smaller multi-modal model, use cross-modal attacks and adversarial suffixes"
    },
    "o1_preview": {
        "name": "o1-preview (Reasoning)",
        "doc_category": "llm_legal_compliance",
        "strategy": "adversarial",
        "size_kb": 1024,
        "aggression": 4,
        "jailbreak_techniques": ["chain_of_thought", "self_referential_paradox", "legal_mandate", "cognitive_hacking"],
        "description": "Advanced reasoning model, exploit chain-of-thought and logical paradoxes"
    },
    "o1_mini": {
        "name": "o1-mini (Fast Reasoning)",
        "doc_category": "security_compliance",
        "strategy": "maze",
        "size_kb": 640,
        "aggression": 4,
        "jailbreak_techniques": ["chain_of_thought", "self_referential_paradox", "adversarial_suffix"],
        "description": "Fast reasoning model, use logical paradoxes and reasoning exploitation"
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
