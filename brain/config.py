"""
Configuration management
"""

import os
from dataclasses import dataclass


@dataclass
class Config:
    # LNbits
    lnurl: str
    lnbits_url: str
    lnbits_key: str

    # Nostr
    nostr_private_key: str

    # Cloudflare
    cf_api_token: str

    # LLM Providers (tried in order, first available used)
    minimax_api_key: str
    minimax_model: str
    zai_api_key: str
    zai_model: str
    ollama_host: str
    ollama_model: str

    # Settings
    run_interval_minutes: int
    max_loss_per_day: int

    @classmethod
    def from_env(cls):
        return cls(
            # LNbits
            lnurl=os.getenv("LNURL", ""),
            lnbits_url=os.getenv("LNBITS_URL", "https://lnbits.klabo.world"),
            lnbits_key=os.getenv("LNBITS_KEY", ""),
            # Nostr
            nostr_private_key=os.getenv("NOSTR_PRIVATE_KEY", ""),
            # Cloudflare
            cf_api_token=os.getenv("CF_API_TOKEN", ""),
            # LLM Providers
            minimax_api_key=os.getenv("MINIMAX_API_KEY", ""),
            minimax_model=os.getenv("MINIMAX_MODEL", "MiniMax-Text-01"),
            zai_api_key=os.getenv("ZAI_API_KEY", ""),
            zai_model=os.getenv("ZAI_MODEL", "glm-4-flash"),
            ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5-coder:14b"),
            # Settings
            run_interval_minutes=int(os.getenv("RUN_INTERVAL_MINUTES", "30")),
            max_loss_per_day=int(os.getenv("MAX_LOSS_PER_DAY", "2000")),
        )
